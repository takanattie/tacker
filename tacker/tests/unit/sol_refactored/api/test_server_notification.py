# Copyright (C) 2022 Fujitsu
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from tacker import context
from tacker.sol_refactored.api import server_notification_wsgi as sn_wsgi
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored import objects
from tacker.tests.unit import base
from unittest import mock


class TestServerNotification(base.TestCase):
    def setUp(self):
        super(TestServerNotification, self).setUp()
        objects.register_all()
        self.context = context.get_admin_context()
        self.request = mock.Mock()
        self.request.context = self.context

    @mock.patch.object(sn_wsgi.ServerNotificationErrorResponse, 'serialize')
    def test_response(self, mock_serialize_pp):
        class _Test():
            def __init__(self, ctx, title):
                self.status = 200
                self.detail = 'detail'
                self.title = title
                self.method = 'GET'
                self.url = 'url'
                self.environ = None
                self.body = {}
                self.context = ctx
                self.status_int = 200

            def best_match_content_type(self):
                return 'application/json'

            def serialize(self, _):
                if self.title == 'error':
                    raise sol_ex.SolValidationError(
                        detail='test error')
                return self

        def test(*args, **kwargs):
            return (None, None, None)

        def test2(*args, **kwargs):
            return _Test(None, None)

        def test3(*args, **kwargs):
            return _Test(None, 'error')

        # make responses
        sn_wsgi.ServerNotificationResponse(
            200, {}, content_type='content_type')
        sn_wsgi.ServerNotificationErrorResponse(
            _Test(self.context, None), None)
        sn_wsgi.ServerNotificationErrorResponse(
            _Test(self.context, 'title'), None)

        # no error
        p = sn_wsgi.ServerNotificationResource(
            None, 'tacker_server_notification_api:server_notification:notify')
        p(_Test(self.context, None))

        # raise unknown error
        p = sn_wsgi.ServerNotificationResource(
            None, 'tacker_server_notification_api:server_notification:notify')
        p._deserialize_request = test
        p._check_policy = test
        p._dispatch = test2
        p(_Test(self.context, None))

        mock_serialize_pp.side_effect = _Test(self.context, 'error')
        p._dispatch = test3
        p(_Test(self.context, 'error'))
