import pytest
import json
import random
import time
from utils.logger_config import running_logger
from utils.ssh_host import sshToEnv
from datetime import datetime
from utils.tools import watch_task
from apis.computer.instance import Instance

# CREATE_DATA = {
#     "architecture":"x86_64",
#     "deadline":None,
#     "description":"",
#     "disableTermination":False,
#     "guestOSId":"",
#     "vclusterId":"vcr-aarch64",
#     "icon":"",
#     "instanceName":"test",
#     "bootFromKernel":False,
#     "kernelId":"",
#     "isHA":True,
#     "isImportant":False,
#     "password":"",
#     "platform":"linux",
#     "groupId":"instance-default",
#     "scheduleGroup":"",
#     "scheduleType":"ROUND_ROBIN",
#     "expectedHost":"",
#     "rebootIfFailed":False,
#     "priority":5,
#     "publicKey":"",
#     "tag":"",
#     "bootType":"bios",
#     "poolId":"sp-00e9cff7d0",
#     "hostId":"",
#     "vmConfig":{
#         "architecture":"aarch64",
#         "isUefi":False,
#         "enableKvmClock":True,
#         "enableDiskEncryption":False,
#         "enableEscapeDetection":False,
#         "poolId":"sp-00e9cff7d0",
#         "poolType":"",
#         "cpu":{
#             "cpuCurrent":2,
#             "cpuSocket":1,
#             "corePerSocket":2,
#             "enableHostCpu":False,
#             "enableCpuHotPlug":False,
#             "enableMonopolyCpu":False,
#             "monopolyConfig":None,
#             "cpuFrequency":0,
#             "quota":0,
#             "isAutoDedicatedPCpu":False
#         },
#         "memory":{
#             "memorySize":2048,
#             "enableHugePage":False,
#             "memHugePage":None,
#             "enableMemHotPlug":False,
#             "hardLimit":0
#         },
#         "hardDisk":[
#             {
#                 "volumeSize":20,
#                 "volumeName":"",
#                 "volumeId":"",
#                 "hasOperatingSystem":True,
#                 "srcFileId":"",
#                 "srcSnapshotId":"",
#                 "iopsLimit":0,
#                 "bpsLimit":0,
#                 "slot":0,
#                 "srcIncBackupVolId":"",
#                 "kmsId":"",
#                 "encryptedKey":"",
#                 "isEncrypted":False,
#                 "poolId":"sp-00e9cff7d0",
#                 "ioReadRate":0,
#                 "ioWriteRate":0,
#                 "ioReadPs":0,
#                 "ioWritePs":0
#             }
#         ],
#         "cdrom":[
#             {
#                 "isoId":""
#             },
#             {
#                 "isoId":""
#             }
#         ],
#         "networkInterfaces":[
#             {
#                 "uplinkDeviceId":"dvs-008fe93a76",
#                 "connectedToName":"内部策略交换机",
#                 "firewallId":"",
#                 "ipv4Enable":True,
#                 "gatewayIp":"",
#                 "ipAddress":"",
#                 "netMask":"",
#                 "isUplink":True,
#                 "hwAddr":"",
#                 "ipCheck":True,
#                 "inBandwidth":0,
#                 "outBandwidth":0,
#                 "txChecksumDisabled":False,
#                 "inBrustBandwidth":0,
#                 "outBrustBandwidth":0,
#                 "ipv6Enable":False,
#                 "ipv6Address":"",
#                 "ipv6Gateway":"",
#                 "ipv6NetMask":"",
#                 "queues":0,
#                 "ipv4SecondaryIpCount":0,
#                 "ipv4SecondaryIps":[],
#                 "ipv4SecondaryIpsStr":"",
#                 "ipv6SecondaryIpCount":0,
#                 "ipv6SecondaryIps":[],
#                 "ipv6SecondaryIpsStr":""
#             }
#         ],
#         "usb":[],
#         "pci":[],
#         "extendDomain":"",
#         "extendDevices":"",
#         "aliveEdit":None
#     },
#     "cloneMode":"fastFullClone",
#     "count":1,
#     "srcInstanceId":"i-009df1cf60",
#     "srcTemplateId":"vmt-00e8c69c7e",
#     "startAfterCreated":True,
#     "sufBegin":1,
#     "tags":None,
#     "createType":"CREATE_TYPE_TEMPLATE"
# }

@pytest.fixture(scope='class') 
def setup_class_fixture(request, login): 
    test_class = request.cls
    test_class.logger = running_logger
    test_class.ssh = sshToEnv('10.16.221.154', 'pass@hci1')

    test_class.req_session, test_class.username, test_class.login_passwd = login
    test_class.instance = Instance(test_class.req_session)

class TestCreateVM1:
    def assert_vm_info(self, vm_name:str, vm_id:str, task_id:str, req_session)-> str:
        # 创建任务执行断言
        assert watch_task(task_id, req_session), f'虚拟机创建失败，虚拟机名称：{vm_name}'
        self.logger.info(f'虚拟机创建成功，虚拟机名称：{vm_name}')

        # vnic底层nvs map下发断言
        # TODO：平台中交换机下联设备关联断言、nvs map中网卡关联信息断言
        loop_count = 0
        max_loop_count = 120
        while True:
            if loop_count > max_loop_count:
                self.logger.error(f'等待虚拟机开机超时，虚拟机名称：{vm_name}')
                break
            vm_info = self.instance.get_vm_info(vm_id)
            vm_info = json.loads(vm_info)
            if vm_info['data']['instanceStatus'] == 'running':
                break
            else:
                time.sleep(1)
            loop_count += 1
        
        hostId = vm_info['data']['hostId']
        time.sleep(1)
        vnic_map, _ = self.ssh.exec_cmd(f'ssh {hostId} "/bhci/nvs/nvs-tool map dump nic"')
        self.logger.debug(f'vnic nvs map：\n{vnic_map}\n')
        vnic_confs = vm_info['data']['vmConfig']['networkInterfaces']
        for vnic_conf in vnic_confs:
            vnic_mac = vnic_conf['hwAddr']
            self.logger.debug(f'vnic mac：{vnic_mac}')
            if vnic_mac not in vnic_map:
                self.logger.error(f'虚拟机{vm_name}的vnic nvs map下发失败，虚拟机名称：{vm_name},map：{vnic_map}')
                assert False, f'虚拟机{vm_name}的vnic nvs map下发失败，虚拟机名称：{vm_name}'

        self.logger.debug(f'虚拟机{vm_name}的vnic nvs map下发成功，虚拟机名称：{vm_name}')

    @pytest.mark.parametrize('dv_switch_id, dv_switch_name, enable_dhcpv4, enable_dhcpv6',
                             [('dvs-008fe93a76', '内部策略交换机', True, False),
                              ('dvs-0029221ec6', '无DHCP', False, False),
                              ('dvs-00a85bde9a', '单栈IPv6-外部模拟', False, True),
                              ('dvs-0040d908c2', 'NAT测试2-双栈', True, True)]
                            )
    @pytest.mark.parametrize('enable_ipv4', [True, False])
    @pytest.mark.parametrize('enable_ipv6', [True, False])
    @pytest.mark.parametrize('specify_ipv4', [False, True])
    @pytest.mark.parametrize('specify_ipv6', [False, True])  
    def test_create_vm_vnic(
            self,
            setup_class_fixture, 
            dv_switch_id:str, 
            dv_switch_name:str,
            enable_dhcpv4:bool,
            enable_dhcpv6:bool,
            enable_ipv4:bool,
            enable_ipv6:bool,
            specify_ipv4:bool,
            specify_ipv6:bool
        ):
        """
        虚拟机网卡验证用例

        :param login: 登录会话
        :param dv_switch_id: 虚拟交换机ID
        :param dv_switch_name: 虚拟交换机名称
        :param enable_dhcpv4: 交换机是否开启DHCPv4
        :param enable_dhcpv6: 交换机是否开启DHCPv6
        :param enable_ipv4: 虚拟机网卡是否启用IPv4
        :param enable_ipv6: 虚拟机网卡是否启用IPv6
        :param specify_ipv4: 虚拟机网卡是否指定IPv4
        :param specify_ipv6: 虚拟机网卡是否指定IPv6
        """
        payload = self.instance.get_create_payload_tmpl()
        time_now = datetime.now().strftime('%d%H%M%S%f')[:-3]
        vm_name = 'test_vm_' + time_now
        payload['instanceName'] = vm_name
        vnic_conf = payload['vmConfig']['networkInterfaces'][0]

        vnic_conf['uplinkDeviceId'] = dv_switch_id
        vnic_conf['connectedToName'] = dv_switch_name

        vnic_conf['ipv4Enable'] = enable_ipv4
        if enable_dhcpv4 == False and enable_ipv4 == True and specify_ipv4:
            ip_parts_base = [random.randint(1, 255) for _ in range(3)]
            ip_addr = '.'.join(map(str, ip_parts_base))
            
            vnic_conf['ipAddress'] = ip_addr + '.' + str(random.randint(1, 255))
            vnic_conf['netMask'] = '255.255.255.0'
            vnic_conf['gatewayIp'] = ip_addr + '.1'

        vnic_conf['ipv6Enable'] = enable_ipv6
        if enable_dhcpv6 == False and enable_ipv6 == True and specify_ipv6:
            ipv6_parts = [random.randint(0, 0xFFFF) for _ in range(2)]
            base_ipv6 = ":".join(f"{part:x}" for part in ipv6_parts)
 
            vnic_conf['ipv6Address'] = f'{base_ipv6}::{random.randint(1, 0xFFFF):x}'
            vnic_conf['ipv6NetMask'] = 'ffff:ffff:ffff:ffff::'
            vnic_conf['ipv6Gateway'] = f'{base_ipv6}::1'

        res = self.instance.create_vm(payload)
        res_json = json.loads(res)
        task_id = res_json['data']['taskIds'][0]
        vm_id, = res_json['data']['instanceTaskMap'].keys()

        self.assert_vm_info(vm_name, vm_id, task_id, self.req_session)
        self.instance.delete_vm(vm_id, self.login_passwd)

    def test_create_vm(self, setup_class_fixture):
        payload = self.instance.get_create_payload_tmpl()
        res = self.instance.create_vm(payload)
        res_json = json.loads(res)
        task_id = res_json['data']['taskIds'][0]
        vm_id, = res_json['data']['instanceTaskMap'].keys()

        self.assert_vm_info('test', vm_id, task_id, self.req_session)
        self.instance.delete_vm(vm_id, self.login_passwd)


    # def create_vm_disk_test(self,):
    #     pass
    # ....




# class TestCreateVM:

#     def get_vm_info(self, vm_id:str, req_session)-> str:
#         """
#         查询指定ID的虚拟机信息

#         :param vm_id: 虚拟机ID
#         :param req_session: 请求会话
#         :return: 虚拟机信息
#         :rtype: str
#         """
#         api_path = '/bcs/api/compute/instance/get'

#         payload = f'instanceId={vm_id}&needMonitorData=true&wrapVmConfig=true'
#         res = req_session.get(api_path, payload)
#         return res

#     def shutdown_vm(self, vm_id:str, req_session, is_force:bool=False):
#         """
#         虚拟机关机,关机失败或任务监控超时则抛出runtimeerror

#         :param vm_id: 虚拟机ID
#         :param req_session: 请求会话
#         :param is_force: 是否强制关机
#         """
#         api_path = '/bcs/api/compute/instance/stop'

#         payload = {"force":is_force,"instanceIds":[vm_id],"reason":"pytest shutdown"}
#         res = req_session.post(api_path, json.dumps(payload), '', headers={'Content-Type':'application/json'})  
#         res = json.loads(res) 
#         task_id = res['data']['taskIds'][0]
#         if not watch_task(task_id, req_session):
#             raise RuntimeError(f'虚拟机关机失败，虚拟机名称：{vm_id}')

#     def rm_vm(self, vm_id:str, login_user_passwd:str, req_session,
#               deleteDirectly:bool=True, skip_if_shutdown_fail:bool=True):
#         """
#         关闭虚拟机并删除

#         :param vm_id: 虚拟机ID
#         :param login_user_passwd: 当前登录用户的密码，混淆后
#         :param req_session: 请求会话
#         :param deleteDirectly: 是否直接删除虚拟机，False时则移至回收站
#         :param skip_if_shutdown_fail: 虚拟机关机失败时是否忽略该虚拟机，false时关机失败则抛出异常
#         """
#         try:
#             self.shutdown_vm(vm_id, req_session)
#         except RuntimeError as e:
#             self.logger.warning(f'虚拟机关机失败，虚拟机名称：{vm_id}')
#             if not skip_if_shutdown_fail:
#                 raise e
#             self.logger.debug(f'删除操作跳过虚拟机：{vm_id}')
#         else:
#             api_path = '/bcs/api/compute/instance/delete'
#             payload = {
#                 "instanceIds":[vm_id],
#                 "deleteDirectly":True,
#                 "loginPassword":login_user_passwd
#                 }

#             res = req_session.post(api_path, json.dumps(payload), '', headers={'Content-Type':'application/json'})
                    
#     def assert_vm_info(self, vm_name:str, vm_id:str, task_id:str, req_session)-> str:
#         # 创建任务执行断言
#         assert watch_task(task_id, req_session), f'虚拟机创建失败，虚拟机名称：{vm_name}'
#         self.logger.info(f'虚拟机创建成功，虚拟机名称：{vm_name}')

#         # vnic底层nvs map下发断言
#         # TODO：平台中交换机下联设备关联断言、nvs map中网卡关联信息断言
#         loop_count = 0
#         max_loop_count = 120
#         while True:
#             if loop_count > max_loop_count:
#                 self.logger.error(f'等待虚拟机开机超时，虚拟机名称：{vm_name}')
#                 break
#             vm_info = self.get_vm_info(vm_id, req_session)
#             vm_info = json.loads(vm_info)
#             if vm_info['data']['instanceStatus'] == 'running':
#                 break
#             else:
#                 time.sleep(1)
#             loop_count += 1
        
#         hostId = vm_info['data']['hostId']
#         vnic_map, _ = self.ssh.exec_cmd(f'ssh {hostId} "/bhci/nvs/nvs-tool map dump nic"')
#         self.logger.debug(f'vnic nvs map：\n{vnic_map}\n')
#         vnic_confs = vm_info['data']['vmConfig']['networkInterfaces']
#         for vnic_conf in vnic_confs:
#             vnic_mac = vnic_conf['hwAddr']
#             self.logger.debug(f'vnic mac：{vnic_mac}')
#             assert vnic_mac in vnic_map, f'虚拟机{vm_name}的vnic nvs map下发失败，虚拟机名称：{vm_name}'
#         self.logger.debug(f'虚拟机{vm_name}的vnic nvs map下发成功，虚拟机名称：{vm_name}')

#     @pytest.mark.parametrize('dv_switch_id, dv_switch_name, enable_dhcpv4, enable_dhcpv6',
#                              [('dvs-008fe93a76', '内部策略交换机', True, False),
#                               ('dvs-0029221ec6', '无DHCP', False, False),
#                               ('dvs-00a85bde9a', '单栈IPv6-外部模拟', False, True),
#                               ('dvs-0040d908c2', 'NAT测试2-双栈', True, True)]
#                             )
#     @pytest.mark.parametrize('enable_ipv4', [True, False])
#     @pytest.mark.parametrize('enable_ipv6', [True, False])
#     @pytest.mark.parametrize('specify_ipv4', [False, True])
#     @pytest.mark.parametrize('specify_ipv6', [False, True])  
#     def test_create_vm_vnic(
#             self,
#             login, 
#             dv_switch_id:str, 
#             dv_switch_name:str,
#             enable_dhcpv4:bool,
#             enable_dhcpv6:bool,
#             enable_ipv4:bool,
#             enable_ipv6:bool,
#             specify_ipv4:bool,
#             specify_ipv6:bool
#         ):
#         """
#         虚拟机网卡验证用例

#         :param login: 登录会话
#         :param dv_switch_id: 虚拟交换机ID
#         :param dv_switch_name: 虚拟交换机名称
#         :param enable_dhcpv4: 交换机是否开启DHCPv4
#         :param enable_dhcpv6: 交换机是否开启DHCPv6
#         :param enable_ipv4: 虚拟机网卡是否启用IPv4
#         :param enable_ipv6: 虚拟机网卡是否启用IPv6
#         :param specify_ipv4: 虚拟机网卡是否指定IPv4
#         :param specify_ipv6: 虚拟机网卡是否指定IPv6
#         """
#         payload = deepcopy(CREATE_DATA)
#         time_now = datetime.now().strftime('%d%H%M%S%f')[:-3]
#         vm_name = 'test_vm_' + time_now
#         payload['instanceName'] = vm_name
#         vnic_conf = payload['vmConfig']['networkInterfaces'][0]

#         vnic_conf['uplinkDeviceId'] = dv_switch_id
#         vnic_conf['connectedToName'] = dv_switch_name

#         vnic_conf['ipv4Enable'] = enable_ipv4
#         if enable_dhcpv4 == False and enable_ipv4 == True and specify_ipv4:
#             ip_parts_base = [random.randint(0, 255) for _ in range(3)]
#             ip_addr = '.'.join(map(str, ip_parts_base))
            
#             vnic_conf['ipAddress'] = ip_addr + '.' + str(random.randint(0, 255))
#             vnic_conf['netMask'] = '255.255.255.0'
#             vnic_conf['gatewayIp'] = ip_addr + '.1'

#         vnic_conf['ipv6Enable'] = enable_ipv6
#         if enable_dhcpv6 == False and enable_ipv6 == True and specify_ipv6:
#             ipv6_parts = [random.randint(0, 0xFFFF) for _ in range(2)]
#             base_ipv6 = ":".join(f"{part:x}" for part in ipv6_parts)
 
#             vnic_conf['ipv6Address'] = f'{base_ipv6}::{random.randint(0, 0xFFFF):x}'
#             vnic_conf['ipv6NetMask'] = 'ffff:ffff:ffff:ffff::'
#             vnic_conf['ipv6Gateway'] = f'{base_ipv6}::1'

#         req_session, _, login_passwd = login
#         res = req_session.post(self.create_by_templ_api, json.dumps(payload), '', headers={'Content-Type': 'application/json'})
#         res_json = json.loads(res)
#         task_id = res_json['data']['taskIds'][0]
#         vm_id, = res_json['data']['instanceTaskMap'].keys()

#         self.assert_vm_info(vm_name, vm_id, task_id, req_session)
#         self.rm_vm(vm_id, login_passwd, req_session)


#     # def create_vm_disk_test(self,):
#     #     pass
#     # ....


