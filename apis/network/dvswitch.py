import json
from copy import deepcopy
from utils.logger_config import running_logger

CREATE_DATA = {
    "switchName":"testswitch",
    "description":"",
    "dhcpEnable":False,
    "upLinkDeviceId":"",
    "haveConnectDevice":False,
    "switchType":"SwitchTypeStack",
    "mcastSuppressThreshold":0,
    "upLinkType":"Outlet",
    "subnet":{
        "cidr":"",
        "gatewayIP":"",
        "networkFrom":"",
        "networkTo":"",
        "dhcpOption":{
            "dnsServerIPs":[],
            "ntpServerIPs":[],
            "netBiosServerIPs":[],
            "netBiosType":0,
            "nextServerIp":"",
            "archBootFileMap":{}
        }
    },
    "vlanId":0,
    "ipv6Enable":False,
    "ipv6Subnet":{
        "subnetId":"",
        "cidr":"",
        "gatewayIP":"",
        "managerIP":"",
        "networkFrom":"",
        "networkTo":"",
        "dnsServerIPs":[]
    },
    "microSegEnable":False
}

CREATE_DATA_MACLEARN = {
    "switchName":"test1244",
    "description":"",
    "upLinkDeviceId":"nicoutlet-00b2799d13",
    "switchType":"SwitchTypeMacLearn"
}


class DvSwitch:
    def __init__(self, req_session):
        self.req_session = req_session
        self.logger = running_logger

        self.create_api_path = '/bcs/api/network/DVSwitch/create'
        self.list_api_path = '/bcs/api/network/DVSwitch/list'
        self.delete_api_path = '/bcs/api/network/DVSwitch/delete'

    @staticmethod
    def get_create_payload_tmpl(is_maclearn:bool=False):
        payload_tmpl = deepcopy(CREATE_DATA)
        if is_maclearn:
            payload_tmpl = deepcopy(CREATE_DATA_MACLEARN)
        return payload_tmpl

    def get_dvswitch_list(self):
        payload = {"page":1,
                   "pageSize":10,
                   "total":True,
                   "orderBy":"createAt desc",
                   "params":{"bareMetalEnable":False},
                   "rawfilters":{},
                   "visibleColumn":
                        ["switchId","switchName","switchType","networkType","vlanId","subnet.cidr","ipAddressCount","ipv6Subnet.cidr","ipv6AddressUse","upLinkDeviceName","createAt","operation"]
                }

        res = self.req_session.post(self.list_api_path, json.dumps(payload), '', headers={'Content-Type': 'application/json'})
        self.logger.debug(f'dvswitch list:{res}')
        return res
    
    def delete_dvswitch(self, dv_switch_id:str):
        params = f'id={dv_switch_id}'
        self.req_session.get(self.delete_api_path, params)
        self.logger.debug(f'删除DVSwitch：{dv_switch_id}')

    def create_dvswitch(self, payload:dict) -> str:
        res = self.req_session.post(self.create_api_path, json.dumps(payload), '', headers={'Content-Type': 'application/json'})
