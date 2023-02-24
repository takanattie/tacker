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


import threading

from oslo_log import log as logging
from oslo_utils import timeutils
from oslo_utils import uuidutils

from tacker.sol_refactored.api import api_version
from tacker.sol_refactored.common import config
from tacker.sol_refactored.common import exceptions as sol_ex
from tacker.sol_refactored.common import http_client
from tacker.sol_refactored.common import vnf_instance_utils as inst_utils
from tacker.sol_refactored import objects


LOG = logging.getLogger(__name__)

CONF = config.CONF

TEST_NOTIFICATION_TIMEOUT = 20  # seconds


def get_subsc(context, subsc_id):
    subsc = objects.LccnSubscriptionV2.get_by_id(context, subsc_id)
    if subsc is None:
        raise sol_ex.LccnSubscriptionNotFound(subsc_id=subsc_id)
    return subsc


def get_subsc_all(context, marker=None):
    return objects.LccnSubscriptionV2.get_all(context, marker)


def subsc_href(subsc_id, endpoint):
    return "{}/vnflcm/v2/subscriptions/{}".format(endpoint, subsc_id)


def _get_notification_auth_handle(subsc):
    auth_req = subsc.get('authentication', None)
    if auth_req:
        auth = objects.SubscriptionAuthentication(
            authType=auth_req['authType']
        )
        if 'OAUTH2_CLIENT_CERT' in auth.authType:
            param = subsc.authentication.paramsOauth2ClientCert
            verify_cert = CONF.v2_vnfm.notification_mtls_ca_cert_file
            client_cert = CONF.v2_vnfm.notification_mtls_client_cert_file
            return http_client.OAuth2MtlsAuthHandle(None,
                param.tokenEndpoint, param.clientId, verify_cert, client_cert)
        elif 'OAUTH2_CLIENT_CREDENTIALS' in auth.authType:
            param = subsc.authentication.paramsOauth2ClientCredentials
            return http_client.OAuth2AuthHandle(None,
                param.tokenEndpoint, param.clientId, param.clientPassword)
        elif 'BASIC' in auth.authType:
            param = subsc.authentication.paramsBasic
            return http_client.BasicAuthHandle(param.userName, param.password)
        else:
            raise sol_ex.AuthTypeNotFound(auth.authType)
    else:
        return http_client.NoAuthHandle()

    # not reach here


def async_call(func):
    def inner(*args, **kwargs):
        th = threading.Thread(target=func, args=args,
                kwargs=kwargs, daemon=True)
        th.start()
    return inner


@async_call
def send_notification(subsc, notif_data):
    auth_handle = _get_notification_auth_handle(subsc)
    connect_retries = (CONF.v2_vnfm.notify_connect_retries
        if CONF.v2_vnfm.notify_connect_retries else None)
    client = http_client.HttpClient(auth_handle,
        version=api_version.CURRENT_VERSION,
        connect_retries=connect_retries)

    url = subsc.callbackUri
    try:
        resp, body = client.do_request(
            url, "POST", expected_status=[204], body=notif_data)
    except sol_ex.SolException:
        # it may occur if test_notification was not executed.
        LOG.exception("send_notification failed")

    if resp.status_code != 204:
        LOG.error("send_notification failed: %d" % resp.status_code)


def test_notification(subsc):
    auth_handle = _get_notification_auth_handle(subsc)
    client = http_client.HttpClient(auth_handle,
        version=api_version.CURRENT_VERSION,
        timeout=TEST_NOTIFICATION_TIMEOUT)

    url = subsc.callbackUri
    try:
        resp, _ = client.do_request(url, "GET", expected_status=[204])
    except sol_ex.SolException as e:
        # any sort of error is considered. avoid 500 error.
        raise sol_ex.TestNotificationFailed() from e

    if resp.status_code != 204:
        raise sol_ex.TestNotificationFailed()


def match_version(version, inst):
    # - vnfSoftwareVersion 1
    # - vnfdVersions 0..N
    if version.vnfSoftwareVersion != inst.vnfSoftwareVersion:
        return False

    if not version.obj_attr_is_set('vnfdVersions'):
        # OK, no more check necessary.
        return True

    return inst.vnfdVersion in version.vnfdVersions


def match_products_per_provider(products, inst):
    # - vnfProvider 1
    # - vnfProducts 0..N
    #   - vnfProductName 1
    #   - versions 0..N
    #     - vnfSoftwareVersion 1
    #     - vnfdVersions 0..N
    if products.vnfProvider != inst.vnfProvider:
        return False

    if not products.obj_attr_is_set('vnfProducts'):
        # OK, no more check necessary.
        return True

    for product in products.vnfProducts:
        if product.vnfProductName == inst.vnfProductName:
            if not product.obj_attr_is_set('versions'):
                # OK, no more check necessary.
                return True
            for ver in product.versions:
                if match_version(ver, inst):
                    # OK, match.
                    return True
    # no match
    return False


def match_inst_subsc_filter(inst_filter, inst):
    # inst_filter: VnfInstanceSubscriptionFilter
    # - vnfdIds 0..N
    # - VnfProductsFromProviders 0..N
    # - vnfInstanceIds 0..N
    # - vnfInstanceNames 0..N
    if inst_filter.obj_attr_is_set('vnfdIds'):
        if inst.vnfdId not in inst_filter.vnfdIds:
            return False

    if inst_filter.obj_attr_is_set('vnfProductsFromProviders'):
        products_providers = inst_filter.vnfProductsFromProviders
        match = False
        for products in products_providers:
            if match_products_per_provider(products, inst):
                match = True
                break
        if not match:
            # no match found
            return False

    if inst_filter.obj_attr_is_set('vnfInstanceIds'):
        if inst.id not in inst_filter.vnfInstanceIds:
            return False

    if inst_filter.obj_attr_is_set('vnfInstanceNames'):
        if inst.vnfInstanceName not in inst_filter.vnfInstanceNames:
            return False

    return True


def get_inst_create_subscs(context, inst):
    return get_matched_subscs(context, inst,
            'VnfIdentifierCreationNotification', None, None)


def get_inst_delete_subscs(context, inst):
    return get_matched_subscs(context, inst,
            'VnfIdentifierDeletionNotification', None, None)


def get_lcmocc_subscs(context, lcmocc, inst):
    return get_matched_subscs(context, inst,
            'VnfLcmOperationOccurrenceNotification',
            lcmocc.operation, lcmocc.operationState)


def get_matched_subscs(context, inst, notif_type, op_type, op_state):
    subscs = []
    for subsc in get_subsc_all(context):
        # subsc: LccnSubscription

        if not subsc.obj_attr_is_set('filter'):
            # no filter. get it.
            subscs.append(subsc)
            continue

        # subsc.filter: LifecycleChangeNotificationsFilter
        # - vnfInstanceSubscriptionFilter 0..1
        # - notificationTypes 0..N
        # - operationTypes 0..N
        # - operationStates 0..N
        if subsc.filter.obj_attr_is_set('vnfInstanceSubscriptionFilter'):
            inst_filter = subsc.filter.vnfInstanceSubscriptionFilter
            if not match_inst_subsc_filter(inst_filter, inst):
                continue

        if subsc.filter.obj_attr_is_set('notificationTypes'):
            if notif_type not in subsc.filter.notificationTypes:
                continue

        if (op_type is not None and
                subsc.filter.obj_attr_is_set('operationTypes')):
            if op_type not in subsc.filter.operationTypes:
                continue

        if (op_state is not None and
                subsc.filter.obj_attr_is_set('operationStates')):
            if op_state not in subsc.filter.operationStates:
                continue

        # OK, matched
        subscs.append(subsc)

    return subscs


def make_create_inst_notif_data(subsc, inst, endpoint):
    notif_data = objects.VnfIdentifierCreationNotificationV2(
        id=uuidutils.generate_uuid(),
        notificationType="VnfIdentifierCreationNotification",
        subscriptionId=subsc.id,
        timeStamp=timeutils.utcnow(),
        vnfInstanceId=inst.id,
        _links=objects.LccnLinksV2(
            vnfInstance=objects.NotificationLink(
                href=inst_utils.inst_href(inst.id, endpoint)),
            subscription=objects.NotificationLink(
                href=subsc_href(subsc.id, endpoint))
        )
        # vnfLcmOpOcc: is not necessary
    )
    return notif_data


def make_delete_inst_notif_data(subsc, inst, endpoint):
    notif_data = objects.VnfIdentifierDeletionNotificationV2(
        id=uuidutils.generate_uuid(),
        notificationType="VnfIdentifierDeletionNotification",
        subscriptionId=subsc.id,
        timeStamp=timeutils.utcnow(),
        vnfInstanceId=inst.id,
        _links=objects.LccnLinksV2(
            vnfInstance=objects.NotificationLink(
                href=inst_utils.inst_href(inst.id, endpoint)),
            subscription=objects.NotificationLink(
                href=subsc_href(subsc.id, endpoint))
        )
        # vnfLcmOpOcc: is not necessary
    )
    return notif_data


def check_http_client_auth(auth_req):
    auth = objects.SubscriptionAuthentication(
        authType=auth_req['authType']
    )
    if 'OAUTH2_CLIENT_CERT' in auth.authType:
        oauth2_mtls_req = auth_req.get('paramsOauth2ClientCert')
        if oauth2_mtls_req is None:
            msg = "paramsOauth2ClientCert must be specified."
            raise sol_ex.InvalidSubscription(sol_detail=msg)
        auth.paramsOauth2ClientCert = (
            objects.SubscriptionAuthentication_ParamsOauth2ClientCert(
                clientId=oauth2_mtls_req.get('clientId'),
                certificateRef=oauth2_mtls_req.get('certificateRef'),
                tokenEndpoint=oauth2_mtls_req.get('tokenEndpoint')
            )
        )
    elif 'OAUTH2_CLIENT_CREDENTIALS' in auth.authType:
        oauth2_req = auth_req.get('paramsOauth2ClientCredentials')
        if oauth2_req is None:
            msg = "paramsOauth2ClientCredentials must be specified."
            raise sol_ex.InvalidSubscription(sol_detail=msg)
        auth.paramsOauth2ClientCredentials = (
            objects.SubscriptionAuthentication_ParamsOauth2(
                clientId=oauth2_req.get('clientId'),
                clientPassword=oauth2_req.get('clientPassword'),
                tokenEndpoint=oauth2_req.get('tokenEndpoint')
            )
        )
    elif 'BASIC' in auth.authType:
        basic_req = auth_req.get('paramsBasic')
        if basic_req is None:
            msg = "ParamsBasic must be specified."
            raise sol_ex.InvalidSubscription(sol_detail=msg)
        auth.paramsBasic = (
            objects.SubscriptionAuthentication_ParamsBasic(
                userName=basic_req.get('userName'),
                password=basic_req.get('password')
            )
        )
    else:
        raise sol_ex.AuthTypeNotFound(auth.authType)
    return auth
