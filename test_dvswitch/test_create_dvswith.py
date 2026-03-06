import pytest
import json
import random
import time
import asyncio
from utils.logger_config import running_logger
from copy import deepcopy
from datetime import datetime
from utils.ssh_host import sshToEnv
from utils.vm_gust_exec import GustExec
from utils.tools import nvs_map_comparison, list_id_2_map_id, parse_nvs_map, ipv4_prefix_2_netmask, make_random_ip
from apis.network.dvswitch import DvSwitch
from apis.computer.instance import Instance

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
    
    test_class.req_session, test_class.username, test_class.passwd = login
    test_class.dvswitch = DvSwitch(test_class.req_session)
    test_class.logger.debug(f'DvSwitch类初始化完成')

class TestCreateDvSwitch:
    def assert_dvswitch_info(self, payload:dict, ipv4_dict:dict, ipv6_dict:dict)-> str:
        """
        dvswitch信息断言公用方法

        :param payload: 分布式交换机创建时传递的payload
        """
        dvswitch_list = self.dvswitch.get_dvswitch_list()
        dvswitch_list = json.loads(dvswitch_list).get('data', '')

        dv_switch_name = payload.get('switchName', '')
        
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

        # 断言4：dhcp map中是否有对应交换机记录
        if payload.get('dhcpEnable', ''):
            is_pass = False
            stdout, _ = self.ssh.exec_cmd('cd /bhci/nvs;./nvs-tool map dump dhcp')
            dhcp_nvs_map = parse_nvs_map(stdout)
            for dhcp_map_line in dhcp_nvs_map:
                if switch_map_id in dhcp_map_line.values():
                    _, prefix = payload['subnet']['cidr'].split('/')
                    gateway = payload['subnet']['gatewayIP']
                    netmask = ipv4_prefix_2_netmask(prefix)
                    dns = payload['subnet']['dhcpOption']['dnsServerIPs']
                    if gateway not in dhcp_map_line.get('gatewayAddr', ''):
                        self.logger.error(f"{switch_map_id} dhcp 网关与nvs map中的不一致, nvs_map:{dhcp_map_line.get('gatewayAddr', '')},payload:{gateway}")
                        assert False, 'dhcp map中网关不一致'

                    if netmask not in dhcp_map_line.get('subnetMask', ''):
                        self.logger.error(f'{switch_map_id} dhcp 掩码与nvs map中的不一致, nvs_map:{dhcp_map_line.get("subnetMask", "")},payload:{netmask}')
                        assert False, 'dhcp map中掩码不一致'

                    if str(dns) not in dhcp_map_line.get('DNS', ''):
                        self.logger.error(f'{switch_map_id} dhcp dns与nvs map中的不一致, nvs_map:{dhcp_map_line.get("DNS", "")},payload:{dns}')
                        assert False, 'dhcp map中dns不一致'
                    
                    self.logger.debug(f'dhcp map中{switch_map_id}对应交换机记录一致')
                    is_pass = True
                    break
            assert is_pass, 'dhcp map中无对应交换机记录'
        
        # 断言5：dhcpv6 map中是否有对应交换机记录
        if payload.get('ipv6Enable', ''):
            is_pass = False
            stdout, _ = self.ssh.exec_cmd('cd /bhci/nvs;./nvs-tool map dump dhcp6')
            dhcp6_nvs_map = parse_nvs_map(stdout)
            for dhcp6_map_line in dhcp6_nvs_map:
                if switch_map_id in dhcp6_map_line.values():
                    _, prefix = payload['ipv6Subnet']['cidr'].split('/')
                    gateway = payload['ipv6Subnet']['gatewayIP']
                    dns = '::' if payload['ipv6Subnet']['dnsServerIPs'] == [] else payload['ipv6Subnet']['dnsServerIPs'][0]
                    if gateway not in dhcp6_map_line.get('gatewayAddr', ''):
                        self.logger.error(f'{switch_map_id} dhcpv6 网关与nvs map中的不一致, nvs_map:{dhcp6_map_line.get("gatewayAddr", "")},payload:{gateway}')
                        assert False, 'dhcpv6 map中网关不一致'

                    if prefix not in dhcp6_map_line.get('prefix', ''):
                        self.logger.error(f'{switch_map_id} dhcpv6 掩码与nvs map中的不一致, nvs_map:{dhcp6_map_line.get("prefix", "")},payload:{prefix}')
                        assert False, 'dhcpv6 map中掩码不一致'

                    if str(dns) not in dhcp6_map_line.get('DNS', ''):
                        self.logger.error(f'{switch_map_id} dhcpv6 dns与nvs map中的不一致, nvs_map:{dhcp6_map_line.get("DNS", "")},payload:{dns}')
                        assert False, 'dhcpv6 map中dns不一致'

                    is_pass = True
                    break
            assert is_pass, 'dhcpv6 map中无对应交换机记录'

        # 断言6：交换机下虚拟机联通性
        vm_list = asyncio.run(self.async_create_downstrem_vm(dvswitch_id, dv_switch_name, ipv4_dict, ipv6_dict))
        for vm in vm_list:
            dst_vm_list = vm_list[:]
            dst_vm_list.remove(vm)

            src_ip = vm['ipv4_address']
            src_ipv6 = vm['ipv6_address']
            src_host_ip = vm['host_ip']
            src_vm_id = vm['vm_id']

            ge = GustExec(src_vm_id, self.ssh, src_host_ip)

            for dst_vm in dst_vm_list:
                dst_ip = dst_vm['ipv4_address']
                dst_ipv6 = dst_vm['ipv6_address']
                
                is_ipv4_reachable = False
                is_ipv6_reachable = False
                for i in range(10):
                    if is_ipv4_reachable and is_ipv6_reachable:
                        break

                    if not is_ipv4_reachable:
                        exec_result, exit_code = ge.gust_exec(f'ping -c 1 {dst_ip}')
                        if exit_code != 0:
                            self.logger.error(f'{src_vm_id} ping {dst_ip} 失败, {exec_result}')
                        else:
                            is_ipv4_reachable = True

                    if not is_ipv6_reachable:
                        exec_result, exit_code = ge.gust_exec(f'ping -6 -c 1 {dst_ipv6}')
                        if exit_code != 0:
                            self.logger.error(f'{src_vm_id} ipv6 ping {dst_ipv6} 失败, {exec_result}')
                        else:
                            is_ipv6_reachable = True
                    time.sleep(3)
                assert is_ipv4_reachable and is_ipv6_reachable, f'虚拟机无法ping通,is_ipv4_reachable：{is_ipv4_reachable},is_ipv6_reachable:{is_ipv6_reachable}'

        ins = Instance(self.req_session)
        for vm in vm_list:
            ins.delete_vm(vm['vm_id'], self.passwd, watch_delete=True)

        return dvswitch_id
    
    def create_downstream_vm(self, dvswitch_id:str, dvswitch_name:str,
                             ipv4_info:dict={}, ipv6_info:dict={})->list:
        """
        分布式交换机下行vm创建方法

        :params req_session: 请求会话
        :params dvswitch_id: 分布式交换机ID
        :params dvswitch_name: 分布式交换机名称
        :params is_dhcp: 连接到的分布式交换机是否使用dhcp
        :params is_dhcpv6: 连接到的分布式交换机是否使用dhcpv6
        :params ipv4_info: ipv4信息，包含ip、netmask、gateway
        :params ipv6_info: ipv6信息，包含ip、netmask、gateway
        :return: vm_id, 虚拟机所在物理节点, ipv4地址, ipvv6地址
        """
        inst = Instance(self.req_session)

        payload = inst.get_create_payload_tmpl()
        vm_name = 'test_dvswitch_downstream_vm'
        payload['instanceName'] = vm_name

        nic_conf = payload['vmConfig']['networkInterfaces'][0]
        nic_conf['isUplink'] = True
        nic_conf['uplinkDeviceId'] = dvswitch_id
        nic_conf['connectedToName'] = dvswitch_name
        nic_conf['ipv4Enable'] = True
        nic_conf['ipv6Enable'] = True

        ip_addr = ipv4_info.get('ip', '')
        nic_conf['ipAddress'] = ip_addr
        nic_conf['netMask'] = ipv4_info.get('netMask', '')
        nic_conf['gateway'] = ipv4_info.get('gateway', '')

        # 因为固定前缀所以只做简单处理
        ipv6_addr = ipv6_info.get('ip', '')
        nic_conf['ipv6Address'] = ipv6_addr
        nic_conf['ipv6NetMask'] = ipv6_info.get('netMask', '')
        nic_conf['ipv6Gateway'] = ipv6_info.get('gateway', '')

        vm_id, vm_info = inst.create_vm(payload, watch_is_start=True)
        host_ip = json.loads(vm_info)['data']['hostIp']

        return vm_id, host_ip, ip_addr, ipv6_addr

    async def async_create_downstrem_vm(self, dvswitch_id:str, dvswitch_name:str,
                             ipv4_info:dict={}, ipv6_info:dict={}, create_vm_nums:int=2)->str:
        
        loop = asyncio.get_event_loop()
        tasks = []

        for i in range(create_vm_nums):
            ipv4_info_copy = ipv4_info.copy()
            ipv6_info_copy = ipv6_info.copy()

            ip_addr = ipv4_info_copy.get('ip', '').split('.')
            ip_addr[-1] = int(ip_addr[-1]) + i
            ip_addr = '.'.join(map(str, ip_addr))
            ipv4_info_copy['ip'] = ip_addr

            ipv6_addr = ipv6_info_copy.get('ip', '').split('::')
            ipv6_addr[-1] = hex(int(ipv6_addr[-1], 16) + i)[2:]
            ipv6_addr = '::'.join(map(str, ipv6_addr))
            ipv6_info_copy['ip'] = ipv6_addr

            args = (dvswitch_id, dvswitch_name, ipv4_info_copy, ipv6_info_copy)

            task = loop.run_in_executor(None, self.create_downstream_vm, *args)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)

        vm_list = []

        for vm_id, host_ip, ipv4_address, ipv6_address in results:
            vm_info_dict = {}
            vm_info_dict['vm_id'] = vm_id
            vm_info_dict['host_ip'] = host_ip
            vm_info_dict['ipv4_address'] = ipv4_address
            vm_info_dict['ipv6_address'] = ipv6_address
            vm_list.append(vm_info_dict)
    
        return vm_list


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

        ip_addr_part, ipv4_dict = make_random_ip('ipv4')
        base_ipv6, ipv6_dict = make_random_ip('ipv6')

        if dhcp_enable:
            payload['dhcpEnable'] = True
            ip_cidr = ip_addr_part + '.0/24'
            ipv4_subnet = payload['subnet']
            ipv4_subnet['cidr'] = ip_cidr
            ipv4_subnet['gatewayIP'] = ip_addr_part + '.1'
            ipv4_subnet['networkFrom'] = ip_addr_part + '.2'
            ipv4_subnet['networkTo'] = ip_addr_part + '.255'

        if dhcpv6_enable:
            payload['ipv6Enable'] = True
            ipv6_cidr = base_ipv6 + '::0/64'
            ipv6_subnet = payload['ipv6Subnet']
            ipv6_subnet['cidr'] = ipv6_cidr
            ipv6_subnet['gatewayIP'] = base_ipv6 + '::1'
            ipv6_subnet['managerIP'] = base_ipv6 + '::2'
            ipv6_subnet['networkFrom'] = base_ipv6 + '::1'
            ipv6_subnet['networkTo'] = base_ipv6 + '::ffff:ffff:ffff:ffff'
            
        res = self.dvswitch.create_dvswitch(payload)
        dv_switch_id = self.assert_dvswitch_info(payload, ipv4_dict, ipv6_dict)
        self.dvswitch.delete_dvswitch(dv_switch_id)

    def test_create_dvswitch_maclearn(self, setup_class_fixture):
        """
        基础交换机创建用例
        """

        payload = DvSwitch.get_create_payload_tmpl(is_maclearn=True)
        time_now = datetime.now().strftime('%d%H%M%S%f')[:-3]
        switch_name = 'test_maclearn_' + time_now
        payload['switchName'] = switch_name

        _, ipv4_dict = make_random_ip('ipv4')
        _, ipv6_dict = make_random_ip('ipv6')

        res = self.dvswitch.create_dvswitch(payload)
        dv_switch_id = self.assert_dvswitch_info(payload, ipv4_dict, ipv6_dict)
        self.dvswitch.delete_dvswitch(dv_switch_id)
