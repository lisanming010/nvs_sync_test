import pytest, json, random, time
from utils.logger_config import running_logger
from utils.ssh_host import sshToEnv
from utils.tools import nvs_map_comparison, list_id_2_map_id, map_id_2_list_id
from datetime import datetime
from apis.network.dvrouter import AddressTransform

@pytest.fixture(scope='class')
def setup_class_fixture(request, login):
    test_class = request.cls
    test_class.logger = running_logger

    test_class.req_session, *_ = login
    test_class.ssh = sshToEnv('10.16.221.154', 'pass@hci1')
    test_class.address_transform = AddressTransform(test_class.req_session)
    test_class.logger.debug(f'TestCreateAddressTransform类初始化完成')

class TestCreateAddressTransform:

    def get_connected_vnic(self, route_id:str, sw_id:str, kind_of_transform:str, vnic_nums:int=1) -> dict:
        """
        获取交换机下未被使用的vnic

        :param route_id: 分布式路由器ID
        :param sw_id: 交换机ID
        :param kind_of_transform: 地址转换类型
        :param vnic_nums: 需要获取的虚拟机数量
        :return: 虚拟机信息字典，{vnic_id: [vnic_ip, vnic_name]}
        """

        res = self.address_transform.get_swc_connected_vnic(route_id, sw_id, kind_of_transform)
        res_json = json.loads(res)

        res_data = res_json['data']
        if res_data == []:
            self.logger.error(f'该交换机下无虚拟机连接，请检查交换机ID：{sw_id}')
            raise RuntimeError(f'{sw_id}下无连接的虚拟机')
        
        # 获取交换机下未被使用vnic id
        vnic_dict = {}
        for vnic in res_data:
            if vnic.get('isUsed', True):
                pass
            else:
                if len(vnic_dict) == vnic_nums:
                    break

                vnic_id = vnic.get('nicId', '')
                if vnic_id == '':
                    continue
                vnic_ip = vnic.get('ip', '')
                vnic_name = vnic.get('instanceName', '')
                vnic_dict[vnic_id] = [vnic_ip, vnic_name]
        
        if vnic_dict == {}:
            self.logger.error(f'该交换机下无未使用的虚拟机，请检查交换机ID：{sw_id}')
            raise RuntimeError(f'{sw_id}下无未使用的虚拟机')
        elif len(vnic_dict) < vnic_nums:
            self.logger.error(f'该交换机下未使用的虚拟机数量无法满足要求，请检查交换机ID：{sw_id}')
            raise RuntimeError(f'{sw_id}下未使用的虚拟机无法满足数量要求')
        
        return vnic_dict

    def get_connected_sw(self, route_id:str, kind_of_transform:str, sw_nums:int=1) -> dict:
        """
        获取连接到分布式路由器下未被SNAT规则关联的交换机

        :param route_id: 分布式路由器ID
        :param kind_of_transform: 地址转换类型
        :param sw_nums: 需要获取的交换机数量
        :return: 交换机信息字典，{swid: [cidr, sw_name]}
        """
        res = self.address_transform.get_connected_sw(route_id, kind_of_transform)
        res_json = json.loads(res)

        res_data = res_json['data']
        if res_data == []:
            self.logger.error(f'该路由器下无交换机连接，请检查路由ID：{route_id}')
            raise RuntimeError(f'{route_id}下无连接的交换机')
        
        # 获取未被使用的交换机id以及cidr
        sw_dict = {}
        for sw in res_data:
            if sw.get('isUsed', True):
                pass
            else:
                if len(sw_dict) == sw_nums:
                    break

                sw_id = sw.get('switchId', '')
                if sw_id == '':
                    continue
                sw_cidr = sw['subnet'].get('cidr', '')
                sw_name = sw.get('switchName', '')
                sw_dict[sw_id] = [sw_cidr, sw_name]
                
        if sw_dict == {}:
            self.logger.error(f'该路由器下无未使用的交换机，请检查路由ID：{route_id}')
            raise RuntimeError(f'{route_id}下无未使用的交换机')
        elif len(sw_dict) < sw_nums:
            self.logger.error(f'该路由器下未被使用交换机数量无法满足要求，请检查路由ID：{route_id}')
            raise RuntimeError(f'{route_id}下未使用的交换机无法满足数量要求')
        
        return sw_dict

    def make_snat_transform_devices_list(self, route_id:str, kind_of_transform:str, devices_type:str, device_num:int=1)->list:
        """
        生成SNAT转换设备列表

        :param route_id: 分布式路由器ID
        :param kind_of_transform: 地址转换类型
        :param devices_type: 设备类型
        :param device_num: 设备数量
        :return: 设备列表,[dict, ...]
        """

        transform_devices = []
        if devices_type == 'switch':
            device_tmpl = {
                "deviceId":"dvs-0007171e0a",
                "ip":"192.168.98.0/24",
                "deviceType":"Switch",
                "disabled":False,
                "deviceName":"防火墙测试交换机"
            }

            # 生成switch类型的 transform_devices
            available_sw_dict = self.get_connected_sw(route_id, kind_of_transform, device_num)
            for available_sw_id, available_sw_info in available_sw_dict.items():
                device_tmpl['deviceId'] = available_sw_id
                sw_cidr, sw_name = available_sw_info
                device_tmpl['ip'] = sw_cidr
                device_tmpl['deviceName'] = sw_name
                transform_devices.append(device_tmpl)

        elif devices_type == 'nic':
            device_tmpl = {
                "deviceId":"vnic-003b042b39",
                "ip":"192.168.98.2",
                "deviceType":"Nic",
                "disabled":True,
                "uplinkDeviceId":"dvs-0007171e0a",
                "deviceName":"防火墙-1"
            }

            # 生成nic类型的 transform_devices
            # 获取所有已连接的交换机id
            all_connetced_sw = self.address_transform.get_connected_sw(route_id, kind_of_transform)
            all_connetced_sw = json.loads(all_connetced_sw)
            connected_swid_list = []
            for sw_data in all_connetced_sw['data']:
                conn_sw_id = sw_data.get('switchId', '')
                connected_swid_list.append(conn_sw_id)

            # TODO：允许拆分虚拟机到不同交换机下
            available_vnic_dict = {}
            for sw_id in connected_swid_list:
                try:
                    available_vnic_dict = self.get_connected_vnic(route_id, sw_id, kind_of_transform, device_num)
                except RuntimeError as e:
                    continue
                else:
                    for vnic_id, vnic_info in available_vnic_dict.items():
                        device_tmpl['deviceId'] = vnic_id
                        vnic_ip, vnic_name = vnic_info
                        device_tmpl['ip'] = vnic_ip
                        device_tmpl['deviceName'] = vnic_name
                        device_tmpl['uplinkDeviceId'] = sw_id
                        transform_devices.append(device_tmpl)
                    break

            if available_vnic_dict == {}:
                self.logger.error(f'路由器下任意单个交换机下联虚拟机数量均不能满足要求，请检查路由ID：{route_id}')
                raise RuntimeError(f'单个交换机下无足够的虚拟机')
        else:
            self.logger.error(f'设备类型错误：{devices_type}')
            raise RuntimeError('设备类型错误')
        
        return transform_devices


    def assert_transform_info(self, route_id:str, kind_of_transform:str, payload:dict)-> str:
        """
        验证地址转换信息
        """
        nat_list = self.address_transform.get_existing_transform_list(route_id, kind_of_transform)
        nat_list = json.loads(nat_list)['data']

        des_ip = payload.get('ipPoolAllocatedIP', '')

        kind_of_transform = 'snat' if kind_of_transform == 'AddressTransformSNAT' else 'dnat'

        # 断言1：各节点间NAT map条数是否一致。
        assert nvs_map_comparison(self.ssh, kind_of_transform)

        if kind_of_transform == 'snat':
            # 断言2：NAT规则是否创建成功
            is_success = False
            for nat_rule in nat_list:
                if nat_rule.get('dIps', '')[0] == des_ip:
                    is_success = True
                    break
            if not is_success:
                self.logger.error(f'{route_id}下未找到对应的SNAT规则')
                assert False, f'{route_id}下未找到对应的SNAT规则'

            # 断言3：SNAT规则是否正常下发
            for _ in range(5):
                snat_map_nums, _ = self.ssh.exec_cmd(f'/bhci/nvs/nvs-tool map dump snat|grep {des_ip}|wc -l')
                snat_map, _ = self.ssh.exec_cmd(f'/bhci/nvs/nvs-tool map dump snat|grep {des_ip}')
                if snat_map_nums != '' and snat_map != '':
                    break
                else:
                    time.sleep(1)
            if not payload['isAll']:
                assert len(payload['transformDevices']) == int(snat_map_nums), 'SNAT规则下发失败'
                for transformdevice in payload['transformDevices']:
                    if transformdevice['ip'] not in snat_map:
                        self.logger.error(f'SNAT下发失败, snat_map: {snat_map}')
                        assert False, 'SNAT规则下发失败'
            else:
                conn_sw = self.address_transform.get_connected_sw(route_id, kind_of_transform)
                conn_sw = json.loads(conn_sw)
                assert conn_sw['total'] == int(snat_map_nums), 'SNAT规则下发失败或nvs_map采集超时'
                for swc in conn_sw['data']:
                    if swc['subnet']['cidr'] not in snat_map:
                        self.logger.error(f'SNAT下发失败')
                        assert False, 'SNAT规则下发失败'

        if kind_of_transform == 'dnat':
            # 断言2：NAT规则是否创建成功
            nvs_map_key = []

            for payload_transform_devices in payload['transformDevices']:
                temp = []
                sw_id = payload_transform_devices['uplinkDeviceId']
                sw_id = list_id_2_map_id(sw_id.removeprefix('dvs-00'))
                ip = payload_transform_devices['ip']
                temp.append(sw_id)
                temp.append(ip)
                nvs_map_key.append(temp)

            is_success = False
            for nat_rule in nat_list:
                if des_ip in nat_rule.get('dIps', '') and payload['protocol'] == nat_rule['protocol'] and payload['DNatDstPort'] == nat_rule['DNatDstPort']:
                    is_success = True
                    break
            if not is_success:
                self.logger.error(f'DNAT创建失败')
                assert False, 'DNAT创建失败'

            # 断言3：DNAT规则是否正常下发
            for nvs_map in nvs_map_key:
                for _ in range(5):
                    dnat_map, _ = self.ssh.exec_cmd(f"/bhci/nvs/nvs-tool map dump dnat|grep {des_ip}|grep {payload['protocol']}|grep {payload['DNatDstPort']}|grep {payload['DNatSrcPort']}|grep {nvs_map[0]}|grep {nvs_map[1]}")
                    if dnat_map != '':
                        break
                    else:
                        time.sleep(1)
                if dnat_map == '':
                    self.logger.error(f'DNAT规则下发失败,节点map查询：{dnat_map}')
                    assert False, 'DNAT规则下发失败'
          
    @pytest.mark.parametrize('dv_route_id', ['dvr-004258bfb9'])
    @pytest.mark.parametrize('upLink_deviceid', ['nicoutlet-00b2799d13'])
    @pytest.mark.parametrize('backend_type', ['switch', 'nic'])
    @pytest.mark.parametrize('backend_nums', [0, 1, 2])
    def test_create_transform_snat(self,
                                   setup_class_fixture,
                                   dv_route_id:str,
                                   upLink_deviceid:str,
                                   backend_type:str,
                                   backend_nums:int,
                                   ) -> str:
        
        payload = self.address_transform.get_create_transform_tmpl('AddressTransformSNAT')
        payload['routerId'] = dv_route_id
        payload['upLinkDeviceId'] = upLink_deviceid
        ip_pool_info = self.address_transform.get_ip_pool_list(dv_route_id, upLink_deviceid, 'AddressTransformSNAT')
        ip_pool_info = json.loads(ip_pool_info)
        for ip_info in ip_pool_info['data']:
            if ip_info['id'] == '':
                payload['ipPoolAllocatedIP'] = ip_info['ip']
        if payload['ipPoolAllocatedIP'] == '':
            self.logger.error(f'该路由器连接IP池中无IP可用，业务出口：{upLink_deviceid}')
            raise RuntimeError(f'该路由器连接IP池中无IP可用')
        
        if backend_nums == 0:
            payload['isAll'] = True
            payload['backendDevices'] = []
        else:
            payload['isAll'] = False
            payload['backendDevices'] = self.make_snat_transform_devices_list(dv_route_id, 'AddressTransformSNAT', backend_type, backend_nums)
        
        res = self.address_transform.create_transform(payload)
        self.assert_transform_info(dv_route_id, 'AddressTransformSNAT', payload)

        list_nat = self.address_transform.get_existing_transform_list(dv_route_id, 'AddressTransformSNAT')
        list_nat = json.loads(list_nat)['data']
        for nat_rule in list_nat:
            nat_id = nat_rule.get('addressTransformId', '')
            self.address_transform.delete_transform(nat_id)
     

    @pytest.mark.parametrize('dv_route_id', ['dvr-004258bfb9'])
    @pytest.mark.parametrize('upLink_deviceid', ['nicoutlet-00b2799d13'])
    @pytest.mark.parametrize('backend_nums', [1, 2])
    @pytest.mark.parametrize('protocol', ['tcp', 'udp'])
    @pytest.mark.parametrize('dnat_dstport', [80, 443])
    @pytest.mark.parametrize('dnat_srcport', [80, 443])
    @pytest.mark.parametrize('session_affinity_timeout', [0, 300])
    def test_create_transform_dnat(self,
                                setup_class_fixture,
                                dv_route_id:str,
                                upLink_deviceid:str,
                                backend_nums:int,
                                protocol:str,
                                dnat_dstport:int,
                                dnat_srcport:int,
                                session_affinity_timeout:int
                                ) -> str:
        payload = self.address_transform.get_create_transform_tmpl('AddressTransformDNAT')
        payload['routerId'] = dv_route_id
        payload['upLinkDeviceId'] = upLink_deviceid
        payload['protocol'] = protocol
        payload['DNatDstPort'] = dnat_dstport
        payload['DNatSrcPort'] = dnat_srcport

        if session_affinity_timeout == 0:
            payload['DNatSessionAffinity'] = False
        else:
            payload['sessionAffinityTimeout'] = session_affinity_timeout

        payload['backendDevices'] = self.make_snat_transform_devices_list(dv_route_id, 'AddressTransformDNAT', 'nic', backend_nums)

        res = self.address_transform.create_transform(payload)
        self.assert_transform_info(dv_route_id, 'AddressTransformDNAT', payload)

        list_nat = self.address_transform.get_existing_transform_list(dv_route_id, 'AddressTransformDNAT')
        list_nat = json.loads(list_nat)['data']
        for nat_rule in list_nat:
            nat_id = nat_rule.get('addressTransformId', '')
            self.address_transform.delete_transform(nat_id)

    @pytest.mark.parametrize('dv_route_id', ['dvr-004258bfb9'])
    @pytest.mark.parametrize('upLink_deviceid', ['nicoutlet-00b2799d13'])
    @pytest.mark.parametrize('backend_nums', [1])
    @pytest.mark.parametrize('protocol', ['tcp'])
    @pytest.mark.parametrize('dnat_dstport', [80])
    @pytest.mark.parametrize('dnat_srcport', [80])
    @pytest.mark.parametrize('session_affinity_timeout', [0])
    def test_create_transform_dnat1(self,
                                setup_class_fixture,
                                dv_route_id:str,
                                upLink_deviceid:str,
                                backend_nums:int,
                                protocol:str,
                                dnat_dstport:int,
                                dnat_srcport:int,
                                session_affinity_timeout:int
                                ) -> str:
        payload = self.address_transform.get_create_transform_tmpl('AddressTransformDNAT')
        payload['routerId'] = dv_route_id
        payload['upLinkDeviceId'] = upLink_deviceid
        payload['protocol'] = protocol
        payload['DNatDstPort'] = dnat_dstport
        payload['DNatSrcPort'] = dnat_srcport

        if session_affinity_timeout == 0:
            payload['DNatSessionAffinity'] = False
        else:
            payload['sessionAffinityTimeout'] = session_affinity_timeout

        payload['backendDevices'] = self.make_snat_transform_devices_list(dv_route_id, 'AddressTransformDNAT', 'nic', backend_nums)

        res = self.address_transform.create_transform(payload)
        self.assert_transform_info(dv_route_id, 'AddressTransformDNAT', payload)

        list_nat = self.address_transform.get_existing_transform_list(dv_route_id, 'AddressTransformDNAT')
        list_nat = json.loads(list_nat)['data']
        for nat_rule in list_nat:
            nat_id = nat_rule.get('addressTransformId', '')
            self.address_transform.delete_transform(nat_id)