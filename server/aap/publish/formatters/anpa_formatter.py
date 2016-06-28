# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.publish.formatters import Formatter
from .aap_formatter_common import map_priority
from apps.archive.common import get_utc_schedule
import superdesk
from superdesk.errors import FormatterError
from bs4 import BeautifulSoup, NavigableString
import datetime
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, BYLINE, EMBARGO, FORMAT, FORMATS
from .field_mappers.locator_mapper import LocatorMapper
from io import StringIO


class AAPAnpaFormatter(Formatter):
    def format(self, article, subscriber, codes=None):
        try:
            docs = []
            for category in article.get('anpa_category'):
                pub_seq_num = superdesk.get_resource_service('subscribers').generate_sequence_number(subscriber)
                anpa = []

                # selector codes are only injected for those subscribers that are defined
                # in the mapper
                # Ta 20/04/16: Keeping selector code mapper section here for the time being
                # selectors = dict()
                # SelectorcodeMapper().map(article, category.get('qcode').upper(),
                #                          subscriber=subscriber,
                #                          formatted_item=selectors)

                if codes:
                    anpa.append(b'\x05')
                    anpa.append(' '.join(codes).encode('ascii'))
                    anpa.append(b'\x0D\x0A')

                # start of message header (syn syn soh)
                anpa.append(b'\x16\x16\x01')
                anpa.append(article.get('service_level', 'a').lower().encode('ascii'))

                # story number
                anpa.append(str(pub_seq_num).zfill(4).encode('ascii'))

                # field seperator
                anpa.append(b'\x0A')  # -LF
                anpa.append(map_priority(article.get('priority')).encode('ascii'))
                anpa.append(b'\x20')

                anpa.append(category['qcode'].encode('ascii'))

                anpa.append(b'\x13')
                # format identifier
                if article.get(FORMAT, FORMATS.HTML) == FORMATS.PRESERVED:
                    anpa.append(b'\x12')
                else:
                    anpa.append(b'\x11')
                anpa.append(b'\x20')

                # keyword
                keyword = 'bc-{}'.format(self.append_legal(article=article, truncate=True)).replace(' ', '-')
                keyword = keyword[:24] if len(keyword) > 24 else keyword
                anpa.append(keyword.encode('ascii'))
                anpa.append(b'\x20')

                # version field
                anpa.append(b'\x20')

                # reference field
                anpa.append(b'\x20')

                # filing date
                anpa.append('{}-{}'.format(article['_updated'].strftime('%m'),
                                           article['_updated'].strftime('%d')).encode('ascii'))
                anpa.append(b'\x20')

                # add the word count
                anpa.append(str(article.get('word_count', '0000')).zfill(4).encode('ascii'))
                anpa.append(b'\x0D\x0A')

                anpa.append(b'\x02')  # STX

                self._process_headline(anpa, article, category['qcode'].encode('ascii'))

                keyword = self.append_legal(article=article, truncate=True).encode('ascii', 'ignore')
                anpa.append(keyword)
                take_key = article.get('anpa_take_key', '').encode('ascii', 'ignore')
                anpa.append((b'\x20' + take_key) if len(take_key) > 0 else b'')
                anpa.append(b'\x0D\x0A')

                if article.get(EMBARGO):
                    embargo = '{}{}\r\n'.format('Embargo Content. Timestamp: ',
                                                get_utc_schedule(article, EMBARGO).isoformat())
                    anpa.append(embargo.encode('ascii', 'replace'))

                if article.get('ednote', '') != '':
                    ednote = '{}\r\n'.format(article.get('ednote'))
                    anpa.append(ednote.encode('ascii', 'replace'))

                if BYLINE in article:
                    anpa.append(article.get(BYLINE).encode('ascii', 'ignore'))
                    anpa.append(b'\x0D\x0A')

                if article.get(FORMAT) == FORMATS.PRESERVED:
                    soup = BeautifulSoup(self.append_body_footer(article), "html.parser")
                    anpa.append(soup.get_text().encode('ascii', 'replace'))
                else:
                    if article.get('dateline', {}).get('text'):
                        soup = BeautifulSoup(article.get('body_html', ''), "html.parser")
                        ptag = soup.find('p')
                        if ptag is not None:
                            ptag.insert(0, NavigableString(
                                '{} '.format(article.get('dateline').get('text')).encode('ascii', 'ignore')))
                            article['body_html'] = str(soup)
                    anpa.append(self.to_ascii(article.get('body_html', '')))
                    if article.get('body_footer'):
                        anpa.append(self.to_ascii(article.get('body_footer', '')))

                anpa.append(b'\x0D\x0A')
                if article.get('more_coming', False):
                    anpa.append('MORE'.encode('ascii'))
                else:
                    anpa.append(article.get('source', '').encode('ascii'))
                sign_off = article.get('sign_off', '').encode('ascii')
                anpa.append((b'\x20' + sign_off) if len(sign_off) > 0 else b'')
                anpa.append(b'\x0D\x0A')

                anpa.append(b'\x03')  # ETX

                # time and date
                anpa.append(datetime.datetime.now().strftime('%d-%m-%y %H-%M-%S').encode('ascii'))

                anpa.append(b'\x04')  # EOT
                anpa.append(b'\x0D\x0A\x0D\x0A\x0D\x0A\x0D\x0A\x0D\x0A\x0D\x0A\x0D\x0A\x0D\x0A')

                docs.append((pub_seq_num, b''.join(anpa)))

            return docs
        except Exception as ex:
            raise FormatterError.AnpaFormatterError(ex, subscriber)

    def to_ascii(self, html):
        """
        Given a html string returns ascii bytes
        :param html:
        :return:
        """
        soup = BeautifulSoup(html, "html.parser")
        text = StringIO()
        for p in soup.findAll('p'):
            text.write('\r\n   ')
            ptext = p.get_text('\n')
            for l in ptext.split('\n'):
                text.write(l + '\r\n')
        return text.getvalue().replace('\xA0', ' ').encode('ascii', 'replace')

    def _process_headline(self, anpa, article, category):
        # prepend the locator to the headline if required
        headline_prefix = LocatorMapper().map(article, category.upper())
        if headline_prefix:
            headline = '{}:{}'.format(headline_prefix, article['headline'])
        else:
            headline = article.get('headline', '')

        # Set the maximum size to 64 including the sequence number if any
        if len(headline) > 64:
            if article.get('sequence'):
                digits = len(str(article['sequence'])) + 1
                shortened_headline = '{}={}'.format(headline[:-digits][:(64 - digits)], article['sequence'])
                anpa.append(shortened_headline.encode('ascii', 'replace'))
            else:
                anpa.append(headline[:64].encode('ascii', 'replace'))
        else:
            anpa.append(headline.encode('ascii', 'replace'))
        anpa.append(b'\x0D\x0A')

    def can_format(self, format_type, article):
        return format_type == 'AAP ANPA' and article[ITEM_TYPE] in [CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED]