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

import ddt
import os

from tacker.objects import fields
from tacker.tests.functional.sol_v2_common import paramgen
from tacker.tests.functional.sol_v2_common import test_vnflcm_basic_common
from tacker.tests import utils


@ddt.ddt
class VnfLcmUpdateTest(test_vnflcm_basic_common.CommonVnfLcmTest):

    @classmethod
    def setUpClass(cls):
        super(VnfLcmUpdateTest, cls).setUpClass()
        image_path = utils.test_etc_sample("etsi/nfv/common/Files/images",
            "cirros-0.5.2-x86_64-disk.img")

        # for basic lcms tests max pattern
        basic_lcms_max_path = utils.test_sample("functional/sol_v2_common",
                                                "basic_lcms_max")
        cls.max_pkg, cls.max_vnfd_id = cls.create_vnf_package(
            basic_lcms_max_path, image_path=image_path)

        # for update vnf test
        update_vnf_path = utils.test_sample("functional/sol_v2_common",
                                            "update_vnf")
        # no image contained
        cls.upd_pkg, cls.upd_vnfd_id = cls.create_vnf_package(update_vnf_path)

    @classmethod
    def tearDownClass(cls):
        super(VnfLcmUpdateTest, cls).tearDownClass()
        cls.delete_vnf_package(cls.max_pkg)
        cls.delete_vnf_package(cls.upd_pkg)

    def setUp(self):
        super().setUp()

    def test_update_scale_lcm(self):
        """Test the sequence of update VNF and scale out

        * About attributes:
          All of the following cardinality attributes are set.
          In addition, 0..N or 1..N attributes are set to 2 or more.
          0..1 is set to 1.
          - 0..1 (1)
          - 0..N (2 or more)
          - 1..N (2 or more)

        * About LCM operations:
          This test includes the following operations.
          - 0. Pre-setting
          - 1. Create subscription
          - 2. Create VNF instance
          - 3. Instantiate VNF
          - 4. Show VNF instance
          - 5. Update VNF
          - 6. Show VNF instance
          - 7. Scale out operation
          - 8. Terminate VNF
          - 9. Delete VNF instance
          - 10. Delete subscription
        """
        # 0. Pre-setting
        # Create a new network and subnet to check the IP allocation of
        # IPv4 and IPv6
        ft_net0_name = 'ft-net0'
        ft_net0_subs = {
            'ft-ipv4-subnet0': {
                'range': '100.100.100.0/24',
                'ip_version': 4
            },
            'ft-ipv6-subnet0': {
                'range': '1111:2222:3333::/64',
                'ip_version': 6
            }
        }
        ft_net0_id = self.create_network(ft_net0_name)
        self.addCleanup(self.delete_network, ft_net0_id)
        for sub_name, val in ft_net0_subs.items():
            # subnet is automatically deleted with network deletion
            self.create_subnet(
                ft_net0_id, sub_name, val['range'], val['ip_version'])

        net_ids = self.get_network_ids(
            ['net0', 'net1', 'net_mgmt', 'ft-net0'])
        subnet_ids = self.get_subnet_ids(
            ['subnet0', 'subnet1', 'ft-ipv4-subnet0', 'ft-ipv6-subnet0'])

        port_names = ['VDU2_CP1-1', 'VDU2_CP1-2']
        port_ids = {}
        for port_name in port_names:
            port_id = self.create_port(net_ids['net0'], port_name)
            port_ids[port_name] = port_id
            self.addCleanup(self.delete_port, port_id)

        # 1. Create subscription
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')

        sub_req = paramgen.sub_create_max(callback_uri)
        resp, body = self.create_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']

        # 2. Create VNF instance
        # ETSI NFV SOL003 v3.3.1 5.5.2.2 VnfInstance
        # NOTE: extensions and vnfConfigurableProperties are omitted
        # because they are commented out in etsi_nfv_sol001.
        expected_inst_attrs = [
            'id',
            'vnfInstanceName',
            'vnfInstanceDescription',
            'vnfdId',
            'vnfProvider',
            'vnfProductName',
            'vnfSoftwareVersion',
            'vnfdVersion',
            # 'vnfConfigurableProperties', # omitted
            # 'vimConnectionInfo', # omitted
            'instantiationState',
            # 'instantiatedVnfInfo', # omitted
            'metadata',
            # 'extensions', # omitted
            '_links'
        ]
        create_req = paramgen.create_vnf_max(self.max_vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 3. Instantiate VNF instance
        instantiate_req = paramgen.instantiate_vnf_max(
            net_ids, subnet_ids, port_ids, self.auth_url)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 4. Show VNF instance
        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check instantiationState of VNF
        self.assertEqual(fields.VnfInstanceState.INSTANTIATED,
                         body['instantiationState'])

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # 5. Update VNF
        # check attribute value before update VNF
        # check usageState of max pattern VNF Package
        self.check_package_usage(self.max_pkg, 'IN_USE')

        # check usageState of update VNF Package
        self.check_package_usage(self.upd_pkg, 'NOT_IN_USE')

        # check vnfd id
        self.assertEqual(self.max_vnfd_id, body['vnfdId'])

        # check vnfc info
        vnfc_info = body['instantiatedVnfInfo']['vnfcInfo']
        self.assertGreater(len(vnfc_info), 1)
        vnfc_ids = [vnfc['id'] for vnfc in vnfc_info]
        for vnfc in vnfc_info:
            self.assertIn('id', vnfc)
            self.assertIn('vduId', vnfc)
            self.assertIsNotNone(vnfc.get('vnfcState'))
            self.assertIsNone(vnfc.get('vnfcConfigurableProperties'))

        update_req = paramgen.update_vnf_max(self.upd_vnfd_id, vnfc_ids)
        resp, body = self.update_vnf_instance(inst_id, update_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 6. Show VNF instance
        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # check usageState of max pattern VNF Package
        self.check_package_usage(self.max_pkg, 'NOT_IN_USE')

        # check usageState of update pattern VNF Package
        self.check_package_usage(self.upd_pkg, 'IN_USE')

        # check the specified attribute after update VNF
        self.assertEqual(self.upd_vnfd_id, body['vnfdId'])
        self.assertEqual('new name', body['vnfInstanceName'])
        self.assertEqual('new description', body['vnfInstanceDescription'])
        dummy_key_value = {'dummy-key': 'dummy-value'}
        self.assertEqual(dummy_key_value, body['metadata'])
        self.assertEqual(dummy_key_value, body['extensions'])
        self.assertEqual(dummy_key_value, body['vnfConfigurableProperties'])
        vim_connection_info = {
            "vim2": {
                "vimId": "ac2d2ece-5e49-4b15-b92d-b681e9c096d8",
                "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
                "interfaceInfo": {
                    "endpoint": "http://127.0.0.1/identity/v3"
                },
                "accessInfo": {
                    "username": "dummy_user",
                    "region": "RegionOne",
                    "project": "dummy_project",
                    "projectDomain": "Default",
                    "userDomain": "Default"
                },
                "extra": {
                    "dummy-key": "dummy-val"
                }
            }
        }
        self.assertEqual(vim_connection_info['vim2'],
            body['vimConnectionInfo']['vim2'])

        # check vnfc info
        vnfc_info = body['instantiatedVnfInfo']['vnfcInfo']
        self.assertEqual(vnfc_ids[0], vnfc_info[0]['id'])
        self.assertEqual(vnfc_ids[1], vnfc_info[1]['id'])
        self.assertEqual(dummy_key_value,
            vnfc_info[0]['vnfcConfigurableProperties'])
        self.assertEqual(dummy_key_value,
            vnfc_info[1]['vnfcConfigurableProperties'])

        # 7. Scale out operation
        scaleout_req = paramgen.scaleout_vnf_max()
        resp, body = self.scale_vnf_instance(inst_id, scaleout_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 8. Terminate a VNF instance
        terminate_req = paramgen.terminate_vnf_max()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 9. Delete a VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 10. Delete subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

    def test_update_heal_lcm(self):
        """Test the sequence of update VNF and heal VNF

        * About attributes:
          All of the following cardinality attributes are set.
          In addition, 0..N or 1..N attributes are set to 2 or more.
          0..1 is set to 1.
          - 0..1 (1)
          - 0..N (2 or more)
          - 1..N (2 or more)

        * About LCM operations:
          This test includes the following operations.
          - 0. Pre-setting
          - 1. Create subscription
          - 2. Create VNF instance
          - 3. Instantiate VNF
          - 4. Show VNF instance
          - 5. Update VNF
          - 6. Show VNF instance
          - 7. Heal VNF(all with omit all parameter)
          - 8. Heal VNF(all with all=False parameter)
          - 9. Heal VNF(all with all=True parameter)
          - 10. Terminate VNF
          - 11. Delete VNF instance
          - 12. Delete subscription
        """
        # 0. Pre-setting
        # Create a new network and subnet to check the IP allocation of
        # IPv4 and IPv6
        ft_net0_name = 'ft-net0'
        ft_net0_subs = {
            'ft-ipv4-subnet0': {
                'range': '100.100.100.0/24',
                'ip_version': 4
            },
            'ft-ipv6-subnet0': {
                'range': '1111:2222:3333::/64',
                'ip_version': 6
            }
        }
        ft_net0_id = self.create_network(ft_net0_name)
        self.addCleanup(self.delete_network, ft_net0_id)
        for sub_name, val in ft_net0_subs.items():
            # subnet is automatically deleted with network deletion
            self.create_subnet(
                ft_net0_id, sub_name, val['range'], val['ip_version'])

        net_ids = self.get_network_ids(
            ['net0', 'net1', 'net_mgmt', 'ft-net0'])
        subnet_ids = self.get_subnet_ids(
            ['subnet0', 'subnet1', 'ft-ipv4-subnet0', 'ft-ipv6-subnet0'])

        port_names = ['VDU2_CP1-1', 'VDU2_CP1-2']
        port_ids = {}
        for port_name in port_names:
            port_id = self.create_port(net_ids['net0'], port_name)
            port_ids[port_name] = port_id
            self.addCleanup(self.delete_port, port_id)

        # 1. Create subscription
        callback_url = os.path.join(self.get_notify_callback_url(),
                                    self._testMethodName)
        callback_uri = ('http://localhost:'
                        f'{self.get_server_port()}'
                        f'{callback_url}')

        sub_req = paramgen.sub_create_max(callback_uri)
        resp, body = self.create_subscription(sub_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        sub_id = body['id']

        # 2. Create VNF instance
        # ETSI NFV SOL003 v3.3.1 5.5.2.2 VnfInstance
        # NOTE: extensions and vnfConfigurableProperties are omitted
        # because they are commented out in etsi_nfv_sol001.
        expected_inst_attrs = [
            'id',
            'vnfInstanceName',
            'vnfInstanceDescription',
            'vnfdId',
            'vnfProvider',
            'vnfProductName',
            'vnfSoftwareVersion',
            'vnfdVersion',
            # 'vnfConfigurableProperties', # omitted
            # 'vimConnectionInfo', # omitted
            'instantiationState',
            # 'instantiatedVnfInfo', # omitted
            'metadata',
            # 'extensions', # omitted
            '_links'
        ]
        create_req = paramgen.create_vnf_max(self.max_vnfd_id)
        resp, body = self.create_vnf_instance(create_req)
        self.assertEqual(201, resp.status_code)
        self.check_resp_headers_in_create(resp)
        self.check_resp_body(body, expected_inst_attrs)
        inst_id = body['id']

        # check usageState of VNF Package
        self.check_package_usage(self.max_pkg, 'IN_USE')

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 3. Instantiate VNF instance
        instantiate_req = paramgen.instantiate_vnf_max(
            net_ids, subnet_ids, port_ids, self.auth_url)
        resp, body = self.instantiate_vnf_instance(inst_id, instantiate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 4. Show VNF instance
        # check creation of Heat-stack
        stack_name = f'vnf-{inst_id}'
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("CREATE_COMPLETE", stack_status)

        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check instantiationState of VNF
        self.assertEqual(fields.VnfInstanceState.INSTANTIATED,
                         body['instantiationState'])

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # 5. Update VNF
        # check attribute value before update VNF
        # check usageState of max pattern VNF Package
        self.check_package_usage(self.max_pkg, 'IN_USE')

        # check usageState of update VNF Package
        self.check_package_usage(self.upd_pkg, 'NOT_IN_USE')

        # check vnfd id
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(self.max_vnfd_id, body['vnfdId'])

        # check vnfc info
        vnfc_info = body['instantiatedVnfInfo']['vnfcInfo']
        self.assertGreater(len(vnfc_info), 1)
        vnfc_ids = [vnfc['id'] for vnfc in vnfc_info]
        for vnfc in vnfc_info:
            self.assertIn('id', vnfc)
            self.assertIn('vduId', vnfc)
            self.assertIsNotNone(vnfc.get('vnfcState'))
            self.assertIsNone(vnfc.get('vnfcConfigurableProperties'))

        update_req = paramgen.update_vnf_max(self.upd_vnfd_id, vnfc_ids)
        resp, body = self.update_vnf_instance(inst_id, update_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # 6. Show VNF instance
        additional_inst_attrs = [
            'vimConnectionInfo',
            'instantiatedVnfInfo'
        ]
        expected_inst_attrs.extend(additional_inst_attrs)
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.check_resp_headers_in_get(resp)
        self.check_resp_body(body, expected_inst_attrs)

        # check vnfState of VNF
        self.assertEqual(fields.VnfOperationalStateType.STARTED,
                         body['instantiatedVnfInfo']['vnfState'])

        # check usageState of max pattern VNF Package
        self.check_package_usage(self.max_pkg, 'NOT_IN_USE')

        # check usageState of update VNF Package
        self.check_package_usage(self.upd_pkg, 'IN_USE')

        # check the specified attribute after update VNF
        self.assertEqual(self.upd_vnfd_id, body['vnfdId'])
        self.assertEqual('new name', body['vnfInstanceName'])
        self.assertEqual('new description', body['vnfInstanceDescription'])
        dummy_key_value = {'dummy-key': 'dummy-value'}
        self.assertEqual(dummy_key_value, body['metadata'])
        self.assertEqual(dummy_key_value, body['extensions'])
        self.assertEqual(dummy_key_value, body['vnfConfigurableProperties'])
        vim_connection_info = {
            "vim2": {
                "vimId": "ac2d2ece-5e49-4b15-b92d-b681e9c096d8",
                "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
                "interfaceInfo": {
                    "endpoint": "http://127.0.0.1/identity/v3"
                },
                "accessInfo": {
                    "username": "dummy_user",
                    "region": "RegionOne",
                    "project": "dummy_project",
                    "projectDomain": "Default",
                    "userDomain": "Default"
                },
                "extra": {
                    "dummy-key": "dummy-val"
                }
            }
        }
        self.assertEqual(vim_connection_info['vim2'],
            body['vimConnectionInfo']['vim2'])

        # check vnfc info
        vnfc_info = body['instantiatedVnfInfo']['vnfcInfo']
        self.assertEqual(vnfc_ids[0], vnfc_info[0]['id'])
        self.assertEqual(vnfc_ids[1], vnfc_info[1]['id'])
        self.assertEqual(dummy_key_value,
            vnfc_info[0]['vnfcConfigurableProperties'])
        self.assertEqual(dummy_key_value,
            vnfc_info[1]['vnfcConfigurableProperties'])

        # 7. Heal VNF(all with omit all parameter)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2'])]
        vdu1_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]
        heal_req = paramgen.heal_vnf_all_max_with_parameter()
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check stack info
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("UPDATE_COMPLETE", stack_status)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2'])]
        vdu1_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]

        self.assertEqual("CREATE_COMPLETE",
            vdu1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            vdu2_stack_after_heal['resource_status'])

        self.assertNotEqual(vdu1_stack_before_heal['physical_resource_id'],
            vdu1_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(vdu2_stack_before_heal['physical_resource_id'],
            vdu2_stack_after_heal['physical_resource_id'])

        # 8. Heal VNF(all with all=False parameter)
        vdu1_stack_before_heal = vdu1_stack_after_heal
        vdu2_stack_before_heal = vdu2_stack_after_heal
        heal_req = paramgen.heal_vnf_all_max_with_parameter(False)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check stack info
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("UPDATE_COMPLETE", stack_status)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2'])]
        vdu1_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]

        self.assertEqual("CREATE_COMPLETE",
            vdu1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            vdu2_stack_after_heal['resource_status'])

        self.assertNotEqual(vdu1_stack_before_heal['physical_resource_id'],
            vdu1_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(vdu2_stack_before_heal['physical_resource_id'],
            vdu2_stack_after_heal['physical_resource_id'])

        # 9. Heal VNF(all with all=True parameter)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2', 'VDU1-VirtualStorage',
            'VDU2-VirtualStorage', 'internalVL3'])]
        vdu1_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]
        storage1_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1-VirtualStorage')][0]
        storage2_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2-VirtualStorage')][0]
        network_stack_before_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'internalVL3')][0]

        stack_id_before_heal = self.heat_client.get_stack_id(stack_name)
        heal_req = paramgen.heal_vnf_all_max_with_parameter(True)
        resp, body = self.heal_vnf_instance(inst_id, heal_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)
        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check stack info
        stack_id_after_heal = self.heat_client.get_stack_id(stack_name)
        self.assertNotEqual(stack_id_before_heal, stack_id_after_heal)
        stack_status, _ = self.heat_client.get_status(stack_name)
        self.assertEqual("CREATE_COMPLETE", stack_status)
        nested_stacks = self.heat_client.get_resources(stack_name)
        temp_stacks = [stack for stack in nested_stacks if
            (stack['resource_name'] in ['VDU1', 'VDU2', 'VDU1-VirtualStorage',
            'VDU2-VirtualStorage', 'internalVL3'])]
        vdu1_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1')][0]
        vdu2_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2')][0]
        storage1_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU1-VirtualStorage')][0]
        storage2_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'VDU2-VirtualStorage')][0]
        network_stack_after_heal = [stack for stack in temp_stacks if
            (stack['resource_name'] == 'internalVL3')][0]

        self.assertEqual("CREATE_COMPLETE",
            vdu1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            vdu2_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            storage1_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            storage2_stack_after_heal['resource_status'])
        self.assertEqual("CREATE_COMPLETE",
            network_stack_after_heal['resource_status'])

        self.assertNotEqual(vdu1_stack_before_heal['physical_resource_id'],
            vdu1_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(vdu2_stack_before_heal['physical_resource_id'],
            vdu2_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(storage1_stack_before_heal['physical_resource_id'],
            storage1_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(storage2_stack_before_heal['physical_resource_id'],
            storage2_stack_after_heal['physical_resource_id'])
        self.assertNotEqual(network_stack_before_heal['physical_resource_id'],
            network_stack_after_heal['physical_resource_id'])

        # 10. Terminate VNF
        terminate_req = paramgen.terminate_vnf_max()
        resp, body = self.terminate_vnf_instance(inst_id, terminate_req)
        self.assertEqual(202, resp.status_code)
        self.check_resp_headers_in_operation_task(resp)

        lcmocc_id = os.path.basename(resp.headers['Location'])
        self.wait_lcmocc_complete(lcmocc_id)

        # check instantiationState of VNF
        resp, body = self.show_vnf_instance(inst_id)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(fields.VnfInstanceState.NOT_INSTANTIATED,
                         body['instantiationState'])

        # 11. Delete VNF instance
        resp, body = self.exec_lcm_operation(self.delete_vnf_instance, inst_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)

        # 12. Delete subscription
        resp, body = self.delete_subscription(sub_id)
        self.assertEqual(204, resp.status_code)
        self.check_resp_headers_in_delete(resp)
