from builtins import object
from cardinal.bot import user_info
from plugins.admin.plugin import AdminPlugin


class TestAdminPlugin(object):
    def test_admins_translation(self):
        plugin = AdminPlugin(None, {
            'admins': [
                {'nick': 'nick', 'user': 'user', 'vhost': 'vhost'},
                {'nick': 'nick', 'user': 'user'},
                {'nick': 'nick', 'vhost': 'vhost'},
                {'user': 'user', 'vhost': 'vhost'},
                {'nick': 'nick'},
                {'user': 'user'},
                {'vhost': 'vhost'},
            ]
        })

        assert plugin.admins == [
            user_info('nick', 'user', 'vhost'),
            user_info('nick', 'user', None),
            user_info('nick', None, 'vhost'),
            user_info(None, 'user', 'vhost'),
            user_info('nick', None, None),
            user_info(None, 'user', None),
            user_info(None, None, 'vhost'),
        ]

    def test_no_config(self):
        plugin = AdminPlugin(None, None)
        assert plugin.admins == []

    def test_is_admin(self):
        plugin = AdminPlugin(None, {'admins': [{'nick': 'nick'}]})
        assert plugin.is_admin(user_info('nick', 'user', 'vhost')) is True
        assert plugin.is_admin(user_info('bad_nick', 'user', 'vhost')) is False

        plugin = AdminPlugin(None, {'admins': [{'user': 'user'}]})
        assert plugin.is_admin(user_info('nick', 'user', 'vhost')) is True
        assert plugin.is_admin(user_info('nick', 'bad_user', 'vhost')) is False

        plugin = AdminPlugin(None, {'admins': [{'vhost': 'vhost'}]})
        assert plugin.is_admin(user_info('nick', 'user', 'vhost')) is True
        assert plugin.is_admin(user_info('nick', 'user', 'bad_vhost')) is False

        plugin = AdminPlugin(None,
                             {'admins': [{'nick': 'nick', 'vhost': 'vhost'}]})
        assert plugin.is_admin(user_info('nick', 'user', 'vhost')) is True
        assert plugin.is_admin(user_info('bad_nick', 'user', 'vhost')) is False
        assert plugin.is_admin(user_info('nick', 'user', 'bad_vhost')) is False

        plugin = AdminPlugin(None,
                             {'admins': [{'user': 'user', 'vhost': 'vhost'}]})
        assert plugin.is_admin(user_info('nick', 'user', 'vhost')) is True
        assert plugin.is_admin(user_info('nick', 'bad_user', 'vhost')) is False
        assert plugin.is_admin(user_info('nick', 'user', 'bad_vhost')) is False

        plugin = AdminPlugin(None,
                             {'admins': [{'nick': 'nick', 'user': 'user'}]})
        assert plugin.is_admin(user_info('nick', 'user', 'vhost')) is True
        assert plugin.is_admin(user_info('bad_nick', 'user', 'vhost')) is False
        assert plugin.is_admin(user_info('nick', 'bad_user', 'vhost')) is False

        plugin = AdminPlugin(None,
                             {'admins': [{'nick': 'nick',
                                          'user': 'user',
                                          'vhost': 'vhost'}]})
        assert plugin.is_admin(user_info('nick', 'user', 'vhost')) is True
        assert plugin.is_admin(user_info('bad_nick', 'user', 'vhost')) is False
        assert plugin.is_admin(user_info('nick', 'bad_user', 'vhost')) is False
        assert plugin.is_admin(user_info('nick', 'user', 'bad_vhost')) is False
