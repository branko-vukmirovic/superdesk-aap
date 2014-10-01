import logging
from flask import current_app as app
import superdesk
from superdesk.utc import utcnow
from superdesk.utils import get_hash, is_hashed


logger = logging.getLogger(__name__)


class CreateUserCommand(superdesk.Command):
    """Create a user with given username, password and email.
    If user with given username exists, reset password.
    """

    option_list = (
        superdesk.Option('--username', '-u', dest='username', required=True),
        superdesk.Option('--password', '-p', dest='password', required=True),
        superdesk.Option('--email', '-e', dest='email', required=True),
        superdesk.Option('--admin', '-a', dest='admin', required=False),
    )

    def run(self, username, password, email, admin = 'false'):

        # force type conversion to boolean
        if admin.lower() == 'true':
            is_admin = True
        else:
            is_admin = False

        userdata = {
            'username': username,
            'password': password,
            'email': email,
            'is_admin' : is_admin,
            app.config['LAST_UPDATED']: utcnow(),
        }

        with app.test_request_context('/users', method='POST'):
            if userdata.get('password', None) and not is_hashed(userdata.get('password')):
                userdata['password'] = get_hash(userdata.get('password'),
                                                app.config.get('BCRYPT_GENSALT_WORK_FACTOR', 12))

            user = superdesk.get_resource_service('users').find_one(username=userdata.get('username'), req=None)

            if user:
                logger.info('updating user %s' % (userdata))
                superdesk.get_resource_service('users').patch(user.get('_id'), userdata)
                return userdata
            else:
                logger.info('creating user %s' % (userdata))
                userdata[app.config['DATE_CREATED']] = userdata[app.config['LAST_UPDATED']]
                superdesk.get_resource_service('users').post([userdata])

            logger.info('user saved %s' % (userdata))
            return userdata


class HashUserPasswordsCommand(superdesk.Command):
    def run(self):
        users = superdesk.get_resource_service('auth_users').get(req=None, lookup={})
        for user in users:
            pwd = user.get('password')
            if not is_hashed(pwd):
                updates = {}
                hashed = get_hash(user['password'], app.config.get('BCRYPT_GENSALT_WORK_FACTOR', 12))
                user_id = user.get('_id')
                updates['password'] = hashed
                superdesk.get_resource_service('users').patch(user_id, updates=updates)


superdesk.command('users:create', CreateUserCommand())
superdesk.command('users:hash_passwords', HashUserPasswordsCommand())
