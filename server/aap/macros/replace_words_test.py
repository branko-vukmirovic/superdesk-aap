# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.tests import TestCase


class ReplaceWordsTest(TestCase):

    def setUp(self):
        try:
            from .replace_words import find_and_replace
        except:
            self.fail('Cannot import find_and_replace, do_find_replace functions.')
        else:
            self.under_test_find_and_replace = find_and_replace
            vocab = {
                "_id": "replace_words",
                "display_name": "Replace Words",
                "type": "manageable",
                "items": [
                    {"is_active": True, "existing": "a.m.", "replacement": "am"},
                    {"is_active": True, "existing": "center", "replacement": "centre"},
                    {"is_active": True, "existing": "color", "replacement": "colour"},
                    {"is_active": True, "existing": "tire", "replacement": "tyre"},
                    {"is_active": True, "existing": "George W. Bush", "replacement": "George W Bush"},
                    {"is_active": True, "existing": "ax", "replacement": "axe"}
                ]}

            self.app.data.insert('vocabularies', [vocab])

    def test_find_replace_words_multiple_words(self):
        item = {
            'slugline': 'this is color',
            'headline': 'ColOr is bad.',
            'body_html': 'this is color. tire is great. maximum'
        }

        result, diff = self.under_test_find_and_replace(item)
        self.assertEqual(result['slugline'], 'this is color')
        self.assertEqual(result['headline'], 'ColOr is bad.')
        self.assertEqual(result['body_html'], 'this is color. tire is great. maximum')
        self.assertDictEqual(diff, {'ColOr': 'Colour', 'color': 'colour',
                                    'tire': 'tyre', 'ax': 'axe'})

    def test_find_replace_words_same_words(self):
        item = {
            'body_html': 'Center is great. Center is far'
        }

        result, diff = self.under_test_find_and_replace(item)
        self.assertEqual(result['body_html'], 'Center is great. Center is far')
        self.assertDictEqual(diff, {'Center': 'Centre'})

    def test_find_replace_words(self):
        item = {
            'body_html': 'I am coloring this center.',
            'slugline': 'George W. Bush'
        }

        result, diff = self.under_test_find_and_replace(item)
        self.assertEqual(result['body_html'], 'I am coloring this center.')
        self.assertEqual(result['slugline'], 'George W. Bush')
        self.assertDictEqual(diff, {'center': 'centre', 'George W. Bush': 'George W Bush', 'color': 'colour'})

    def test_find_replace_words_ending_with_dots(self):
        item = {
            'body_html': 'George W. Bush center opens at 5 a.m.',
            'slugline': 'George W. Bush'
        }

        result, diff = self.under_test_find_and_replace(item)
        self.assertEqual(result['body_html'], 'George W. Bush center opens at 5 a.m.')
        self.assertEqual(result['slugline'], 'George W. Bush')
        self.assertDictEqual(diff, {'a.m.': 'am', 'George W. Bush': 'George W Bush', 'center': 'centre'})

    def test_repetition_of_words_with_different_case(self):
        item = {'body_html': 'Color color COLOR cOlOr'}
        result, diff = self.under_test_find_and_replace(item)
        self.assertEqual(result['body_html'], 'Color color COLOR cOlOr')

    def test_partial_word(self):
        item = {'body_html': 'Something coloring it red'}
        result, diff = self.under_test_find_and_replace(item)
        self.assertEqual(result['body_html'], 'Something coloring it red')
