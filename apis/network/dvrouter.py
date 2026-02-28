import json
from copy import deepcopy
from utils.logger_config import running_logger

CREATE_DVROUTER_DATA ={
    "routerId":"",
    "routerName":"test",
    "upLinkDeviceIds":[
        "nicoutlet-00b2799d13"
    ],
    "description":""
}

CREATE_TRANSFORM_SNAT_DATA = {
    "addressTransformId":"",
    "routerId":"dvr-004258bfb9",
    "isAll":False,
    "addressTransformType":"AddressTransformSNAT",
    "transformDevices":[
        {
            "deviceId":"vnic-003b042b39",
            "ip":"192.168.98.2",
            "deviceType":"Nic",
            "disabled":True,
            "uplinkDeviceId":"dvs-0007171e0a",
            "deviceName":"防火墙-1"
        }
    ],
    "DNatDstPort":0,
    "upLinkDeviceId":"nicoutlet-00b2799d13",
    "ipPoolAllocatedIP":"",
    "DNatSrcPort":0,
    "description":"",
    "createBy":"",
    "modifiedBy":"",
    "createAt":"",
    "updateAt":""
}

CREATE_TRANSFORM_DNAT_DATA = {
    "addressTransformId":"",
    "routerId":"dvr-004258bfb9",
    "isAll":False,
    "DNatSessionAffinity":True,
    "protocol":"tcp",
    "addressTransformType":"AddressTransformDNAT",
    "transformDevices":[
        {
            "deviceId":"vnic-0017d0ed5b",
            "ip":"192.168.98.3",
            "deviceType":"Nic",
            "disabled":False,
            "uplinkDeviceId":"dvs-0007171e0a",
            "deviceName":"防火墙-2"
        }
    ],
    "sessionAffinityTimeout":300,
    "DNatDstPort":1,
    "upLinkDeviceId":"nicoutlet-00b2799d13",
    "ipPoolAllocatedIP":"192.16.2.200",
    "DNatSrcPort":1,
    "description":"",
    "createBy":"",
    "modifiedBy":"",
    "createAt":"",
    "updateAt":""
}

class DvRouter:
    def __init__(self, req_session):
        self.req_session = req_session
        self.logger = running_logger

        self.create_api_path = '/bcs/api/network/dvRouter/create'
        self.list_api_path = '/bcs/api/network/dvRouter/list'
        self.delete_api_path = '/bcs/api/network/dvRouter/delete'

    @staticmethod
    def get_create_payload_tmpl():
        return deepcopy(CREATE_DVROUTER_DATA)
    
    def get_dvroute_list(self) -> str:
        """
        分布式路由器列表查询方法，获取所有分布式路由器记录
        """
        payload = {
            "page":1,
            "pageSize":10,
            "total":True,
            "orderBy":"createAt desc",
            "params":{},
            "rawfilters":{},
            "visibleColumn":["routerId","routerName","description","upLinkDeviceNames","createBy","createAt","operation"]
        }

        res = self.req_session.post(self.list_api_path, json.dumps(payload), '', headers={'Content-Type': 'application/json'})
        self.logger.debug(f'路由器列表查询结果：{res}')
        return res
    
    def delete_dvroute(self, dv_route_id:str, passwd:str, is_force:bool=False) -> bool:
        """
        分布式路由器删除方法

        :param dv_route_id: 分布式路由器ID
        :param passwd: 当前登录用户的密码
        :param req_session: 请求会话
        :param is_force: 是否强制删除，默认为False

        """
        payload = {
            "isForce":is_force,
            "routerIds":[dv_route_id],
            "userLoginPwd":passwd
        }
        res = self.req_session.post(self.delete_api_path, json.dumps(payload), '', headers={'Content-Type': 'application/json'})

    def create_dvrouter(self, payload:dict):
        print('create_dvrouter')
        res = self.req_session.post(self.create_api_path, json.dumps(payload), '', headers={'Content-Type': 'application/json'})

class AddressTransform:
    def __init__(self, req_session):
        self.req_session = req_session
        self.logger = running_logger

        self.list_existing_transform_api = '/bcs/api/network/dvRouter/addressTransfer/list'
        self.ip_pool_list_api = '/bcs/api/network/dvRouter/addressTransfer/ipPoolList'
        self.list_connected_sw_api = '/bcs/api/network/dvRouter/addressTransfer/listSwc'
        self.list_swc_connected_vnic = '/bcs/api/network/dvRouter/addressTransfer/swcConnectedInstance'
        self.crearte_transform_api = '/bcs/api/network/dvRouter/addressTransfer/create'
        self.delete_transform_api = '/bcs/api/network/dvRouter/addressTransfer/delete'

    @staticmethod
    def get_create_transform_tmpl(kind_of_transform:str):
        payload = {}
        if kind_of_transform == 'AddressTransformSNAT':
            payload = deepcopy(CREATE_TRANSFORM_SNAT_DATA)
        if kind_of_transform == 'AddressTransformDNAT':
            payload = deepcopy(CREATE_TRANSFORM_DNAT_DATA)
        return payload

    def get_existing_transform_list(self, route_id:str, kind_of_transform:str) -> str:

        """
        获取已存在的地址转换列表

        :param route_id: 分布式路由器ID
        :param kind_of_transform: 地址转换类型,SNAT/DNAT
        :return: 查询结果，可被json序列化的str
        """
        payload = {
            "page":1,
            "pageSize":10,
            "total":True,
            "orderBy":"",
            "params":{
                "routerId":route_id,
                "addressTransformType":kind_of_transform
            },
            "rawfilters":{},
            "visibleColumn":["upLinkDeviceName","sIps","dIps","operation"]
        }

        res = self.req_session.post(self.list_existing_transform_api, json.dumps(payload), '', headers={'Content-Type': 'application/json'})
        return res
    
    def get_ip_pool_list(self, route_id:str, ip_pool_id:str, kind_of_transform:str) -> str:
        """
        获取地址转换的出口IP池列表

        :param route_id: 分布式路由器ID
        :param ip_pool_id: 业务出口ID
        :param kind_of_transform: 地址转换类型,SNAT/DNAT
        """
        payload = {
            "ipPoolId":ip_pool_id,
            "routerId":route_id,
            "addressTransformType":kind_of_transform
        }

        res = self.req_session.post(self.ip_pool_list_api, json.dumps(payload), '', headers={'Content-Type': 'application/json'})
        return res
    
    def get_connected_sw(self, route_id:str, kind_of_transform:str) -> str:
        """
        获取当前路由器下已连接的交换机列表

        :param route_id: 分布式路由器ID
        :param kind_of_transform: 地址转换类型,SNAT/DNAT
        """
        payload = {
            "page":1,
            "pageSize":999,
            "total":True,
            "params":{
                "addressTransformType":kind_of_transform,
                "routerId":route_id
            }
        }

        res = self.req_session.post(self.list_connected_sw_api, json.dumps(payload), '', headers={'Content-Type': 'application/json'})
        return res

    def get_swc_connected_vnic(self, route_id:str, sw_id:str, kind_of_transform:str) -> str:
        """
        获取交换机下已连接的虚拟网卡列表

        :param route_id: 分布式路由器ID
        :param sw_id: 交换机ID
        :param kind_of_transform: 地址转换类型,SNAT/DNAT
        """
        payload = {
            "page":1,
            "pageSize":999,
            "total":False,
            "params":{
                "dVSwitchId":sw_id,
                "addressTransformType":kind_of_transform,
                "routerId":route_id
                }
            }
        
        res = self.req_session.post(self.list_swc_connected_vnic, json.dumps(payload), '', headers={'Content-Type': 'application/json'})
        return res

    def create_transform(self, payload:dict) -> str:
        res = self.req_session.post(self.crearte_transform_api, json.dumps(payload), '', headers={'Content-Type': 'application/json'})

    def delete_transform(self, transform_id:str):
        payload = {"addressTransferId":transform_id}

        res = self.req_session.post(self.delete_transform_api, json.dumps(payload), '', headers={'Content-Type': 'application/json'})
        
    
