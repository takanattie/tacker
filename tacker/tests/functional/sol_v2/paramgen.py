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

from oslo_utils import uuidutils


def sub1_create():
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)
    vnf_provider_1 = {
        "vnfProvider": "dummy-vnfProvider-1",
        "vnfProducts": [
            {
                "vnfProductName": "dummy-vnfProductName-1-1",
                "versions": [
                    {
                        "vnfSoftwareVersion": 1.0,
                        "vnfdVersions": [1.0, 2.0]
                    },
                    {
                        "vnfSoftwareVersion": 1.1,
                        "vnfdVersions": [1.1, 2.1]
                    },
                ]
            },
            {
                "vnfProductName": "dummy-vnfProductName-1-2",
                "versions": [
                    {
                        "vnfSoftwareVersion": 1.0,
                        "vnfdVersions": [1.0, 2.0]
                    },
                    {
                        "vnfSoftwareVersion": 1.1,
                        "vnfdVersions": [1.1, 2.1]
                    },
                ]
            }
        ]
    }
    vnf_provider_2 = {
        "vnfProvider": "dummy-vnfProvider-2",
        "vnfProducts": [
            {
                "vnfProductName": "dummy-vnfProductName-2-1",
                "versions": [
                    {
                        "vnfSoftwareVersion": 1.0,
                        "vnfdVersions": [1.0, 2.0]
                    },
                    {
                        "vnfSoftwareVersion": 1.1,
                        "vnfdVersions": [1.1, 2.1]
                    },
                ]
            },
            {
                "vnfProductName": "dummy-vnfProductName-2-2",
                "versions": [
                    {
                        "vnfSoftwareVersion": 1.0,
                        "vnfdVersions": [1.0, 2.0]
                    },
                    {
                        "vnfSoftwareVersion": 1.1,
                        "vnfdVersions": [1.1, 2.1]
                    },
                ]
            }
        ]
    }

    # NOTE: The following is omitted because authType is BASIC in this case
    #  - "paramsOauth2ClientCredentials"
    return {
        "filter": {
            "vnfInstanceSubscriptionFilter": {
                "vnfdIds": [
                    "dummy-vnfdId-1",
                    "dummy-vnfdId-2"
                ],
                "vnfProductsFromProviders": [
                    vnf_provider_1,
                    vnf_provider_2
                ],
                "vnfInstanceIds": [
                    "dummy-vnfInstanceId-1",
                    "dummy-vnfInstanceId-2"
                ],
                "vnfInstanceNames": [
                    "dummy-vnfInstanceName-1",
                    "dummy-vnfInstanceName-2"
                ]
            },
            "notificationTypes": [
                "VnfIdentifierCreationNotification",
                "VnfLcmOperationOccurrenceNotification"
            ],
            "operationTypes": [
                "INSTANTIATE",
                "TERMINATE"
            ],
            "operationStates": [
                "COMPLETED",
                "FAILED"
            ]
        },
        "callbackUri": "http://127.0.0.1/",
        "authentication": {
            "authType": [
                "BASIC"
            ],
            "paramsBasic": {
                "password": "test_pass",
                "userName": "test_user"
            },
            # "paramsOauth2ClientCredentials": omitted,
        },
        "verbosity": "SHORT"
    }


def sub2_create():
    # Omit except for required attributes
    # NOTE: Only the following cardinality attributes are set.
    #  - 1
    #  - 1..N (1)
    return {
        "callbackUri": "http://127.0.0.1/"
    }


def sample1_create(vnfd_id):
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)
    return {
        "vnfdId": vnfd_id,
        "vnfInstanceName": "sample1",
        "vnfInstanceDescription": "test sample1",
        "metadata": {"dummy-key": "dummy-val"}
    }


def sample1_terminate():
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)
    return {
        "terminationType": "GRACEFUL",
        "gracefulTerminationTimeout": 5,
        "additionalParams": {"dummy-key": "dummy-val"}
    }


def sample1_instantiate(net_ids, subnets, ports, auth_url):
    # All attributes are set.
    # NOTE: All of the following cardinality attributes are set.
    # In addition, 0..N or 1..N attributes are set to 2 or more.
    #  - 0..1 (1)
    #  - 0..N (2 or more)
    #  - 1
    #  - 1..N (2 or more)

    vim_id_1 = uuidutils.generate_uuid()
    vim_id_2 = uuidutils.generate_uuid()
    link_port_id_1 = uuidutils.generate_uuid()
    link_port_id_2 = uuidutils.generate_uuid()

    # NOTE: The following is not supported so it is omitted
    #  - "segmentationId"
    #  - "addressRange"
    #  - Multiple "cpProtocolData"
    #  - Multiple "fixedAddresses"
    ext_vl_1 = {
        "id": uuidutils.generate_uuid(),
        "vimConnectionId": vim_id_1,
        "resourceProviderId": "Company",
        "resourceId": net_ids['net0'],
        "extCps": [
            {
                "cpdId": "VDU1_CP1",
                "cpConfig": {
                    "VDU1_CP1": {
                        "parentCpConfigId": uuidutils.generate_uuid(),
                        # "linkPortId": omitted,
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                # "macAddress": omitted,
                                # "segmentationId": omitted,
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    # "fixedAddresses": omitted,
                                    "numDynamicAddresses": 1,
                                    # "addressRange": omitted,
                                    "subnetId": subnets['subnet0']}]}}]
                    },
                    # { "VDU1_CP1_2": omitted }
                }
            },
            {
                "cpdId": "VDU2_CP1-1",
                "cpConfig": {
                    "VDU2_CP1-1": {
                        "parentCpConfigId": uuidutils.generate_uuid(),
                        "linkPortId": link_port_id_1,
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                # "macAddress": omitted,
                                # "segmentationId": omitted,
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    # "fixedAddresses": omitted,
                                    "numDynamicAddresses": 1,
                                    # "addressRange": omitted,
                                    "subnetId": subnets['subnet0']
                                }]
                            }
                        }]
                    },
                    # { "VDU2_CP1_2": omitted }
                }
            },
            {
                "cpdId": "VDU2_CP1-2",
                "cpConfig": {
                    "VDU2_CP1-2": {
                        "parentCpConfigId": uuidutils.generate_uuid(),
                        "linkPortId": link_port_id_2,
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                # "macAddress": omitted,
                                # "segmentationId": omitted,
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    # "fixedAddresses": omitted,
                                    "numDynamicAddresses": 1,
                                    # "addressRange": omitted,
                                    "subnetId": subnets['subnet0']
                                }]
                            }
                        }]
                    },
                    # { "VDU2_CP1_2": omitted }
                }
            }
        ],
        "extLinkPorts": [
            {
                "id": link_port_id_1,
                "resourceHandle": {
                    "resourceId": ports['VDU2_CP1-1']
                }
            },
            # NOTE: Set dummy value because it is set by "additionalParams"
            {
                "id": link_port_id_2,
                "resourceHandle": {
                    "resourceId": "dummy-id"
                }
            }
        ]
    }

    # NOTE: The following is not supported so it is omitted
    #  - "segmentationId"
    #  - "addressRange"
    #  - Multiple "cpProtocolData"
    #  - Multiple "fixedAddresses"
    ext_vl_2 = {
        "id": uuidutils.generate_uuid(),
        "vimConnectionId": vim_id_1,
        "resourceProviderId": "Company",
        "resourceId": net_ids['ft-net0'],
        "extCps": [
            {
                "cpdId": "VDU1_CP2",
                "cpConfig": {
                    "VDU1_CP2": {
                        "parentCpConfigId": uuidutils.generate_uuid(),
                        # "linkPortId": omitted,
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                # "macAddress": omitted,
                                # "segmentationId": omitted,
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    # "fixedAddresses": omitted,
                                    "numDynamicAddresses": 1,
                                    # "addressRange": omitted,
                                    "subnetId": subnets['ft-ipv4-subnet0']}
                                ]}
                        }]
                    },
                    # { "VDU1_CP2_2": omitted }
                }
            },
            {
                "cpdId": "VDU2_CP2",
                "cpConfig": {
                    "VDU2_CP2": {
                        "parentCpConfigId": uuidutils.generate_uuid(),
                        # "linkPortId": omitted,
                        "cpProtocolData": [{
                            "layerProtocol": "IP_OVER_ETHERNET",
                            "ipOverEthernet": {
                                "macAddress": "fa:16:3e:fa:22:75",
                                # "segmentationId": omitted,
                                "ipAddresses": [{
                                    "type": "IPV4",
                                    "fixedAddresses": [
                                        "100.100.100.11",
                                        # omitted
                                    ],
                                    # "numDynamicAddresses": omitted,
                                    # "addressRange": omitted,
                                    "subnetId": subnets['ft-ipv4-subnet0']
                                }, {
                                    "type": "IPV6",
                                    # "fixedAddresses": omitted,
                                    # "numDynamicAddresses": omitted,
                                    "numDynamicAddresses": 1,
                                    # "addressRange": omitted,
                                    "subnetId": subnets['ft-ipv6-subnet0']
                                }]
                            }
                        }]
                    },
                    # { "VDU2_CP2_2": omitted }
                }
            }
        ]
        # "extLinkPorts": omitted
    }
    # NOTE: "vnfLinkPort" is omitted because it is not supported
    ext_mngd_vl_1 = {
        "id": uuidutils.generate_uuid(),
        "vnfVirtualLinkDescId": "internalVL1",
        "vimConnectionId": vim_id_1,
        "resourceProviderId": "Company",
        "resourceId": net_ids['net_mgmt'],
        # "vnfLinkPort": omitted,
        "extManagedMultisiteVirtualLinkId": uuidutils.generate_uuid()
    }
    # NOTE: "vnfLinkPort" is omitted because it is not supported
    ext_mngd_vl_2 = {
        "id": uuidutils.generate_uuid(),
        "vnfVirtualLinkDescId": "internalVL2",
        "vimConnectionId": vim_id_1,
        "resourceProviderId": "Company",
        "resourceId": net_ids['net1'],
        # "vnfLinkPort": omitted,
        "extManagedMultisiteVirtualLinkId": uuidutils.generate_uuid()
    }
    vim_1 = {
        "vimId": vim_id_1,
        "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
        "interfaceInfo": {"endpoint": auth_url},
        "accessInfo": {
            "username": "nfv_user",
            "region": "RegionOne",
            "password": "devstack",
            "project": "nfv",
            "projectDomain": "Default",
            "userDomain": "Default"
        },
        "extra": {"dummy-key": "dummy-val"}
    }
    vim_2 = {
        "vimId": vim_id_2,
        "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
        "interfaceInfo": {"endpoint": auth_url},
        "accessInfo": {
            "username": "dummy_user",
            "region": "RegionOne",
            "password": "dummy_password",
            "project": "dummy_project",
            "projectDomain": "Default",
            "userDomain": "Default"
        },
        "extra": {"dummy-key": "dummy-val"}
    }
    addParams = {
        "lcm-operation-user-data": "./UserData/userdata.py",
        "lcm-operation-user-data-class": "UserData",
        "nfv": {"CP": {"VDU2_CP1-2": {"port": ports['VDU2_CP1-2']}}}
    }

    return {
        "flavourId": "simple",
        "instantiationLevelId": "instantiation_level_1",
        "extVirtualLinks": [
            ext_vl_1,
            ext_vl_2
        ],
        "extManagedVirtualLinks": [
            ext_mngd_vl_1,
            ext_mngd_vl_2
        ],
        "vimConnectionInfo": {
            "vim1": vim_1,
            "vim2": vim_2
        },
        "localizationLanguage": "ja",
        "additionalParams": addParams,
        "extensions": {"dummy-key": "dummy-val"}
    }


def sample2_create(vnfd_id):
    # Omit except for required attributes
    # NOTE: Only the following cardinality attributes are set.
    #  - 1
    #  - 1..N (1)
    return {
        "vnfdId": vnfd_id,
    }


def sample2_terminate():
    # Omit except for required attributes
    # NOTE: Only the following cardinality attributes are set.
    #  - 1
    #  - 1..N (1)
    return {
        "terminationType": "FORCEFUL"
    }


def sample2_instantiate():
    # Omit except for required attributes
    # NOTE: Only the following cardinality attributes are set.
    #  - 1
    #  - 1..N (1)
    return {
        "flavourId": "simple"
    }
