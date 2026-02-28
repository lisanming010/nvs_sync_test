import pytest
import json
import random
from utils.logger_config import running_logger
from copy import deepcopy
from datetime import datetime
from utils.ssh_host import sshToEnv
from utils.tools import nvs_map_comparison, list_id_2_map_id
from apis.network.dvswitch import DvSwitch

# CREATE_DATA = {
#     "switchName":"testswitch",
#     "description":"",
#     "dhcpEnable":False,
#     "upLinkDeviceId":"",
#     "haveConnectDevice":False,
#     "switchType":"SwitchTypeStack",
#     "mcastSuppressThreshold":0,
#     "upLinkType":"Outlet",
#     "subnet":{
#         "cidr":"",
#         "gatewayIP":"",
#         "networkFrom":"",
#         "networkTo":"",
#         "dhcpOption":{
#             "dnsServerIPs":[],
#             "ntpServerIPs":[],
#             "netBiosServerIPs":[],
#             "netBiosType":0,
#             "nextServerIp":"",
#             "archBootFileMap":{}
#         }
#     },
#     "vlanId":0,
#     "ipv6Enable":False,
#     "ipv6Subnet":{
#         "subnetId":"",
#         "cidr":"",
#         "gatewayIP":"",
#         "managerIP":"",
#         "networkFrom":"",
#         "networkTo":"",
#         "dnsServerIPs":[]
#     },
#     "microSegEnable":False
# }

# CREATE_DATA_MACLEARN = {
#     "switchName":"test1244",
#     "description":"",
#     "upLinkDeviceId":"nicoutlet-00b2799d13",
#     "switchType":"SwitchTypeMacLearn"
#     }


@pytest.fixture(scope='class')
def setup_class_fixture(request, login):
    test_class = request.cls
    test_class.logger = running_logger
    test_class.ssh = sshToEnv('10.16.221.154', 'pass@hci1')
    
    test_class.req_session, *_ = login
    test_class.dvswitch = DvSwitch(test_class.req_session)
    test_class.logger.debug(f'DvSwitch类初始化完成')

class TestCreateDvSwitch1:
    def assert_dvswitch_info(self, dv_switch_name:str, req_session)-> str:
        """
        dvswitch信息断言公用方法

        :param dv_switch_name: dvswitch名称
        :param req_session: 请求会话
        """
        dvswitch_list = self.dvswitch.get_dvswitch_list()
        dvswitch_list = json.loads(dvswitch_list).get('data', '')
        
        # TODO: 网段、VLAN号、交换机类型等其余字段校验
        # 断言1：节点间map比较
        assert nvs_map_comparison(self.ssh, 'bridge'), f'nvs-map not equal'

        # 断言2：列表中是否能查询到创建的DVSwitch校验
        dvswitch_id = ''
        dvswitch_in_list = False
        for dvswitch in dvswitch_list:
            if dv_switch_name in dvswitch.values():
                dvswitch_in_list = True
                dvswitch_id = dvswitch.get('switchId', '')
                break
        assert dvswitch_in_list == True, f'{dv_switch_name} not in dvswitch list'

        # 断言3：nvs-tool map dump bridge 命令中，是否能查询到创建的DVSwitch
        stdout, _ = self.ssh.exec_cmd('cd /bhci/nvs;./nvs-tool map dump bridge')
        dvswitch_id_hex = dvswitch_id.removeprefix('dvs-00')
        switch_map_id = list_id_2_map_id(dvswitch_id_hex)
        assert switch_map_id in stdout, f'{dv_switch_name} not in nvs-tool map dump bridge'
        self.logger.debug(f'dvswitch 创建成功，交换机名称：{dv_switch_name}')
        
        return dvswitch_id
    
    # 创建策略交换机用例
    @pytest.mark.parametrize('up_link', ['', 'nicoutlet-00b2799d13'])
    @pytest.mark.parametrize('dhcp_enable', [True, False])
    @pytest.mark.parametrize('dhcpv6_enable', [True, False])
    def test_create_dvswitch(self, setup_class_fixture, dhcp_enable:str, dhcpv6_enable:str, up_link:str):
        # payload构建
        payload = DvSwitch.get_create_payload_tmpl()
        time_now = datetime.now().strftime('%d%H%M%S%f')[:-3]
        switch_name = 'NoDhcp_' + time_now
        payload['switchName'] = switch_name
        payload['upLinkDeviceId'] = up_link

        if dhcp_enable:
            payload['dhcpEnable'] = True
            ip_parts = [random.randint(0, 255) for _ in range(3)]
            ip_addr_part = '.'.join(map(str, ip_parts))
            ip_cidr = ip_addr_part + '.0/24'
            ipv4_subnet = payload['subnet']
            ipv4_subnet['cidr'] = ip_cidr
            ipv4_subnet['gatewayIP'] = ip_addr_part + '.1'
            ipv4_subnet['networkFrom'] = ip_addr_part + '.2'
            ipv4_subnet['networkTo'] = ip_addr_part + '.255'

        if dhcpv6_enable:
            payload['ipv6Enable'] = True
            ipv6_parts = [random.randint(0, 0xFFFF) for _ in range(2)]
            base_ipv6 = ":".join(f"{part:x}" for part in ipv6_parts)
            ipv6_cidr = base_ipv6 + '::0/64'
            ipv6_subnet = payload['ipv6Subnet']
            ipv6_subnet['cidr'] = ipv6_cidr
            ipv6_subnet['gatewayIP'] = base_ipv6 + '::1'
            ipv6_subnet['managerIP'] = base_ipv6 + '::2'
            ipv6_subnet['networkFrom'] = base_ipv6 + '::1'
            ipv6_subnet['networkTo'] = base_ipv6 + '::ffff:ffff:ffff:ffff'
            
        res = self.dvswitch.create_dvswitch(payload)
        
        dv_switch_id = self.assert_dvswitch_info(switch_name, self.req_session)

        self.dvswitch.delete_dvswitch(dv_switch_id)

    def test_create_dvswitch_maclearn(self, setup_class_fixture):
        """
        基础交换机创建用例
        """

        payload = DvSwitch.get_create_payload_tmpl(is_maclearn=True)
        time_now = datetime.now().strftime('%d%H%M%S%f')[:-3]
        switch_name = 'test_maclearn_' + time_now
        payload['switchName'] = switch_name

        self.dvswitch.create_dvswitch(payload)

        dv_switch_id = self.assert_dvswitch_info(switch_name, self.req_session)

        self.dvswitch.delete_dvswitch(dv_switch_id)


# class TestCreateDvSwitch:
#     def setup_method(self):
#         self.api_path = '/bcs/api/network/DVSwitch/create'
#         self.logger = running_logger
#         self.ssh = sshToEnv('10.16.221.154', 'pass@hci1')
#         self.test_dvswitch_id_list = []

#     def get_dvswitch_list(self, req_session):
#         payload = {"page":1,
#                    "pageSize":10,
#                    "total":True,
#                    "orderBy":"createAt desc",
#                    "params":{"bareMetalEnable":False},
#                    "rawfilters":{},
#                    "visibleColumn":
#                         ["switchId","switchName","switchType","networkType","vlanId","subnet.cidr","ipAddressCount","ipv6Subnet.cidr","ipv6AddressUse","upLinkDeviceName","createAt","operation"]
#                 }
#         api_path = '/bcs/api/network/DVSwitch/list'
#         res = req_session.post(api_path, json.dumps(payload), '', headers={'Content-Type': 'application/json'})
#         self.logger.debug(f'dvswitch list:{res}')
#         return res
    
#     # def bridge_id_2_dvid(self, bridge_id:int)->str:
#     #     return str(hex(bridge_id)).removeprefix('0x')

#     # def dvid_2_bridge_id(self, dvid:str)->str:
#     #     return str(int(dvid, 16))
    
#     def delete_dvswitch(self, dv_switch_id:str, req_session):
#         api_path = '/bcs/api/network/DVSwitch/delete'
#         params = f'id={dv_switch_id}'
#         req_session.get(api_path, params)
#         self.logger.debug(f'删除DVSwitch：{dv_switch_id}')
#     def assert_dvswitch_info(self, dv_switch_name:str, req_session)-> str:
#         """
#         dvswitch信息断言公用方法

#         :param dv_switch_name: dvswitch名称
#         :param req_session: 请求会话
#         """
#         dvswitch_list = self.get_dvswitch_list(req_session)
#         dvswitch_list = json.loads(dvswitch_list).get('data', '')
        
#         # TODO: 网段、VLAN号、交换机类型等其余字段校验
#         # 断言1：节点间map比较
#         assert nvs_map_comparison(self.ssh, 'bridge'), f'nvs-map not equal'

#         # 断言2：列表中是否能查询到创建的DVSwitch校验
#         dvswitch_id = ''
#         dvswitch_in_list = False
#         for dvswitch in dvswitch_list:
#             if dv_switch_name in dvswitch.values():
#                 dvswitch_in_list = True
#                 dvswitch_id = dvswitch.get('switchId', '')
#                 break
#         assert dvswitch_in_list == True, f'{dv_switch_name} not in dvswitch list'

#         # 断言3：nvs-tool map dump bridge 命令中，是否能查询到创建的DVSwitch
#         stdout, _ = self.ssh.exec_cmd('cd /bhci/nvs;./nvs-tool map dump bridge')
#         dvswitch_id_hex = dvswitch_id.removeprefix('dvs-00')
#         switch_map_id = list_id_2_map_id(dvswitch_id_hex)
#         assert switch_map_id in stdout, f'{dv_switch_name} not in nvs-tool map dump bridge'
#         self.logger.debug(f'dvswitch 创建成功，交换机名称：{dv_switch_name}')
        
#         return dvswitch_id
    
#     # 创建策略交换机用例
#     @pytest.mark.parametrize('up_link', ['', 'nicoutlet-00b2799d13'])
#     @pytest.mark.parametrize('dhcp_enable', [True, False])
#     @pytest.mark.parametrize('dhcpv6_enable', [True, False])
#     def test_create_dvswitch(self, login, dhcp_enable:str, dhcpv6_enable:str, up_link:str):
#         # payload构建
#         payload = deepcopy(CREATE_DATA)
#         time_now = datetime.now().strftime('%d%H%M%S%f')[:-3]
#         switch_name = 'NoDhcp_' + time_now
#         payload['switchName'] = switch_name
#         payload['upLinkDeviceId'] = up_link

#         if dhcp_enable:
#             payload['dhcpEnable'] = True
#             ip_parts = [random.randint(0, 255) for _ in range(3)]
#             ip_addr_part = '.'.join(map(str, ip_parts))
#             ip_cidr = ip_addr_part + '.0/24'
#             ipv4_subnet = payload['subnet']
#             ipv4_subnet['cidr'] = ip_cidr
#             ipv4_subnet['gatewayIP'] = ip_addr_part + '.1'
#             ipv4_subnet['networkFrom'] = ip_addr_part + '.2'
#             ipv4_subnet['networkTo'] = ip_addr_part + '.255'

#         if dhcpv6_enable:
#             payload['ipv6Enable'] = True
#             ipv6_parts = [random.randint(0, 0xFFFF) for _ in range(2)]
#             base_ipv6 = ":".join(f"{part:x}" for part in ipv6_parts)
#             ipv6_cidr = base_ipv6 + '::0/64'
#             ipv6_subnet = payload['ipv6Subnet']
#             ipv6_subnet['cidr'] = ipv6_cidr
#             ipv6_subnet['gatewayIP'] = base_ipv6 + '::1'
#             ipv6_subnet['managerIP'] = base_ipv6 + '::2'
#             ipv6_subnet['networkFrom'] = base_ipv6 + '::1'
#             ipv6_subnet['networkTo'] = base_ipv6 + '::ffff:ffff:ffff:ffff'
            
#         req_session, *_ = login
#         res = req_session.post(self.api_path, json.dumps(payload), '', headers={'Content-Type': 'application/json'})
        
#         dv_switch_id = self.assert_dvswitch_info(switch_name, req_session)

#         self.delete_dvswitch(dv_switch_id, req_session)

#     def test_create_dvswitch_maclearn(self, login):
#         """
#         基础交换机创建用例
#         """

#         payload = deepcopy(CREATE_DATA_MACLEARN)
#         time_now = datetime.now().strftime('%d%H%M%S%f')[:-3]
#         switch_name = 'test_maclearn_' + time_now
#         payload['switchName'] = switch_name

#         req_session, *_ = login
#         res = req_session.post(self.api_path, json.dumps(payload), '',headers={'Content-Type': 'application/json'})

#         dv_switch_id = self.assert_dvswitch_info(switch_name, req_session)

#         self.delete_dvswitch(dv_switch_id, req_session)
