# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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

from datetime import datetime
from unittest import mock

from oslo_utils import uuidutils

from tacker import context
from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.controller import vnflcm_v2
from tacker.sol_refactored.nfvo import nfvo_client
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects.v2 import fields
from tacker.tests.unit.db import base as db_base


class TestVnflcmV2(db_base.SqlTestCase):

    def setUp(self):
        super(TestVnflcmV2, self).setUp()
        objects.register_all()
        self.controller = vnflcm_v2.VnfLcmControllerV2()
        self.context = context.get_admin_context()
        self.context.api_version = api_version.APIVersion("2.0.0")
        self.request = mock.Mock()
        self.request.context = self.context

    def _create_inst_and_lcmocc(self, inst_state, op_state):
        inst = objects.VnfInstanceV2(
            # required fields
            id=uuidutils.generate_uuid(),
            vnfdId=uuidutils.generate_uuid(),
            vnfProvider='provider',
            vnfProductName='product name',
            vnfSoftwareVersion='software version',
            vnfdVersion='vnfd version',
            instantiationState=inst_state
        )

        req = {"flavourId": "simple"}  # instantate request
        lcmocc = objects.VnfLcmOpOccV2(
            # required fields
            id=uuidutils.generate_uuid(),
            operationState=op_state,
            stateEnteredTime=datetime.utcnow(),
            startTime=datetime.utcnow(),
            vnfInstanceId=inst.id,
            operation=fields.LcmOperationType.INSTANTIATE,
            isAutomaticInvocation=False,
            isCancelPending=False,
            operationParams=req)

        inst.create(self.context)
        lcmocc.create(self.context)

        return inst.id, lcmocc.id

    @mock.patch.object(nfvo_client.NfvoClient, 'get_vnf_package_info_vnfd')
    def test_create_pkg_disabled(self, mocked_get_vnf_package_info_vnfd):
        vnfd_id = uuidutils.generate_uuid()
        pkg_info = objects.VnfPkgInfoV2(
            id=uuidutils.generate_uuid(),
            vnfdId=vnfd_id,
            vnfProvider="provider",
            vnfProductName="product",
            vnfSoftwareVersion="software version",
            vnfdVersion="vnfd version",
            operationalState="DISABLED"
        )
        mocked_get_vnf_package_info_vnfd.return_value = pkg_info
        body = {
            "vnfdId": vnfd_id,
            "vnfInstanceName": "test",
            "vnfInstanceDescription": "test"
        }
        self.assertRaises(sol_ex.VnfdIdNotEnabled,
            self.controller.create, request=self.request, body=body)

    def test_delete_instantiated(self):
        inst_id, _ = self._create_inst_and_lcmocc('INSTANTIATED',
            fields.LcmOperationStateType.COMPLETED)

        self.assertRaises(sol_ex.VnfInstanceIsInstantiated,
            self.controller.delete, request=self.request, id=inst_id)

    def test_delete_lcmocc_in_progress(self):
        inst_id, _ = self._create_inst_and_lcmocc('NOT_INSTANTIATED',
            fields.LcmOperationStateType.FAILED_TEMP)

        self.assertRaises(sol_ex.OtherOperationInProgress,
            self.controller.delete, request=self.request, id=inst_id)

    def test_instantiate_instantiated(self):
        inst_id, _ = self._create_inst_and_lcmocc('INSTANTIATED',
            fields.LcmOperationStateType.COMPLETED)
        body = {"flavourId": "small"}

        self.assertRaises(sol_ex.VnfInstanceIsInstantiated,
            self.controller.instantiate, request=self.request, id=inst_id,
            body=body)

    def test_instantiate_lcmocc_in_progress(self):
        inst_id, _ = self._create_inst_and_lcmocc('NOT_INSTANTIATED',
            fields.LcmOperationStateType.FAILED_TEMP)
        body = {"flavourId": "small"}

        self.assertRaises(sol_ex.OtherOperationInProgress,
            self.controller.instantiate, request=self.request, id=inst_id,
            body=body)

    def test_terminate_not_instantiated(self):
        inst_id, _ = self._create_inst_and_lcmocc('NOT_INSTANTIATED',
            fields.LcmOperationStateType.COMPLETED)
        body = {"terminationType": "FORCEFUL"}

        self.assertRaises(sol_ex.VnfInstanceIsNotInstantiated,
            self.controller.terminate, request=self.request, id=inst_id,
            body=body)

    def test_terminate_lcmocc_in_progress(self):
        inst_id, _ = self._create_inst_and_lcmocc('INSTANTIATED',
            fields.LcmOperationStateType.FAILED_TEMP)
        body = {"terminationType": "FORCEFUL"}

        self.assertRaises(sol_ex.OtherOperationInProgress,
            self.controller.terminate, request=self.request, id=inst_id,
            body=body)

    def test_invalid_subscripion(self):
        body = {
            "callbackUri": "http://127.0.0.1:6789/notification",
            "authentication": {
                "authType": ["BASIC"]
            }
        }
        ex = self.assertRaises(sol_ex.InvalidSubscription,
            self.controller.subscription_create, request=self.request,
            body=body)
        self.assertEqual("ParmasBasic must be specified.", ex.detail)

        body = {
            "callbackUri": "http://127.0.0.1:6789/notification",
            "authentication": {
                "authType": ["OAUTH2_CLIENT_CREDENTIALS"]
            }
        }
        ex = self.assertRaises(sol_ex.InvalidSubscription,
            self.controller.subscription_create, request=self.request,
            body=body)
        self.assertEqual("paramsOauth2ClientCredentials must be specified.",
                         ex.detail)

        body = {
            "callbackUri": "http://127.0.0.1:6789/notification",
            "authentication": {
                "authType": ["TLS_CERT"]
            }
        }
        ex = self.assertRaises(sol_ex.InvalidSubscription,
            self.controller.subscription_create, request=self.request,
            body=body)
        self.assertEqual("'TLS_CERT' is not supported at the moment.",
                         ex.detail)

    def test_retry_not_failed_temp(self):
        _, lcmocc_id = self._create_inst_and_lcmocc('INSTANTIATED',
            fields.LcmOperationStateType.COMPLETED)

        self.assertRaises(sol_ex.LcmOpOccNotFailedTemp,
            self.controller.lcm_op_occ_retry, request=self.request,
            id=lcmocc_id)
