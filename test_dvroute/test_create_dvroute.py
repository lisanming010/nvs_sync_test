import pytest, json
from datetime import datetime
from utils.logger_config import running_logger
from utils.ssh_host import sshToEnv
from utils.tools import nvs_map_comparison, list_id_2_map_id
from copy import deepcopy
from apis.network.dvrouter import DvRouter

# CREATE_DATA ={
#     "routerId":"",
#     "routerName":"test",
#     "upLinkDeviceIds":[
#         "nicoutlet-00b2799d13"
#     ],
#     "description":""
# }

@pytest.fixture(scope='class')
def setup_class_fixture(request, login):
    test_class = request.cls
    test_class.logger = running_logger
    test_class.ssh = sshToEnv('10.16.221.154', 'pass@hci1')

    test_class.req_session, test_class.username, test_class.passwd = login
    test_class.dvrouter = DvRouter(test_class.req_session)

class TestCreateDvRoute:

    def assert_dvroute_info(self, route_name:str, req_session)-> str:
        """
        分布式路由器断言方法

        :param route_name: 分布式路由器名称
        :return: 分布式路由器ID
        :rtype: str
        """

        # 断言1：分布式路由器创建成功
        dvroute_list = self.dvrouter.get_dvroute_list()
        dvroute_list = json.loads(dvroute_list).get('data', '')

        dvroute_id = ''
        dvroute_in_list = False
        for dvroute in dvroute_list:
            if route_name in dvroute.values():
                dvroute_in_list = True
                dvroute_id = dvroute.get('routerId', '')
                break
        assert dvroute_in_list, f'分布式路由器{route_name}创建失败'

        # 断言2：个节点router map行数是否一致校验
        assert nvs_map_comparison(self.ssh, 'router'), '节点间nvs_map不一致'

        # 断言3：分布式路由器底层map是否下发成功
        dvroute_id = dvroute_id.removeprefix('dvr-00')
        dvroute_id_map = list_id_2_map_id(dvroute_id)
        dvroute_map, _ = self.ssh.exec_cmd(f'/bhci/nvs/nvs-tool map dump router')
        assert dvroute_id_map in dvroute_map, f'分布式路由器底层map下发失败，请检查'

        self.logger.debug(f'新建分布式路由器用例通过！')

        return dvroute_id

    @pytest.mark.parametrize('uplink_device_id', ['nicoutlet-00b2799d13'])
    def test_create_dvroute(self, setup_class_fixture, uplink_device_id:str):


        payload = DvRouter.get_create_payload_tmpl()
        time_now = datetime.now().strftime('%d%H%M%S%f')[:-3]
        route_name = 'test_route_' + time_now

        payload['routerName'] = route_name
        payload['upLinkDeviceIds'] = [uplink_device_id]

        self.dvrouter.create_dvrouter(payload)
        
        dvroute_id = self.assert_dvroute_info(route_name, self.req_session)
        dvroute_id = 'dvr-00' + dvroute_id

        self.dvrouter.delete_dvroute(dvroute_id, self.passwd)

# class TestCreateDvRoute:
#     def setup_method(self):
#         self.api_path = '/bcs/api/network/dvRouter/create'
#         self.logger = running_logger
#         self.ssh = sshToEnv('10.16.221.154', 'pass@hci1')

#     def get_dvroute_list(self, req_session) -> list:
#         """
#         分布式路由器列表查询方法，获取所有分布式路由器记录
#         """
#         api_path = '/bcs/api/network/dvRouter/list'
#         payload = {
#             "page":1,
#             "pageSize":10,
#             "total":True,
#             "orderBy":"createAt desc",
#             "params":{},
#             "rawfilters":{},
#             "visibleColumn":["routerId","routerName","description","upLinkDeviceNames","createBy","createAt","operation"]
#         }

#         res = req_session.post(api_path, json.dumps(payload), '', headers={'Content-Type': 'application/json'})
#         self.logger.debug(f'路由器列表查询结果：{res}')
#         return res
    
#     def delete_dvroute(self, dv_route_id:str, passwd:str, req_session, is_force:bool=False) -> bool:
#         """
#         分布式路由器删除方法

#         :param dv_route_id: 分布式路由器ID
#         :param passwd: 当前登录用户的密码
#         :param req_session: 请求会话
#         :param is_force: 是否强制删除，默认为False

#         """
#         api_path = '/bcs/api/network/dvRouter/delete'

#         payload = {
#             "isForce":is_force,
#             "routerIds":[dv_route_id],
#             "userLoginPwd":passwd
#         }
#         res = req_session.post(api_path, json.dumps(payload), '', headers={'Content-Type': 'application/json'})

#     def assert_dvroute_info(self, route_name:str, req_session)-> str:
#         """
#         分布式路由器断言方法

#         :param route_name: 分布式路由器名称
#         :return: 分布式路由器ID
#         :rtype: str
#         """

#         # 断言1：分布式路由器创建成功
#         dvroute_list = self.get_dvroute_list(req_session)
#         dvroute_list = json.loads(dvroute_list).get('data', '')

#         dvroute_id = ''
#         dvroute_in_list = False
#         for dvroute in dvroute_list:
#             if route_name in dvroute.values():
#                 dvroute_in_list = True
#                 dvroute_id = dvroute.get('routerId', '')
#                 break
#         assert dvroute_in_list, f'分布式路由器{route_name}创建失败'

#         # 断言2：个节点router map行数是否一致校验
#         assert nvs_map_comparison(self.ssh, 'router'), '节点间nvs_map不一致'

#         # 断言3：分布式路由器底层map是否下发成功
#         dvroute_id = dvroute_id.removeprefix('dvr-00')
#         dvroute_id_map = list_id_2_map_id(dvroute_id)
#         dvroute_map, _ = self.ssh.exec_cmd(f'/bhci/nvs/nvs-tool map dump router')
#         assert dvroute_id_map in dvroute_map, f'分布式路由器底层map下发失败，请检查'

#         self.logger.debug(f'新建分布式路由器用例通过！')

#         return dvroute_id

#     @pytest.mark.parametrize('uplink_device_id', ['nicoutlet-00b2799d13'])
#     def test_create_dvroute(self, login, uplink_device_id:str):
#         payload = deepcopy(CREATE_DATA)
#         time_now = datetime.now().strftime('%d%H%M%S%f')[:-3]
#         route_name = 'test_route_' + time_now

#         payload['routerName'] = route_name
#         payload['upLinkDeviceIds'] = [uplink_device_id]

#         req_session, _, user_passwd = login
#         res = req_session.post(self.api_path, json.dumps(payload), '', headers={'Content-Type': 'application/json'})

#         dvroute_id = self.assert_dvroute_info(route_name, req_session)
#         dvroute_id = 'dvr-00' + dvroute_id

#         self.delete_dvroute(dvroute_id, user_passwd, req_session)

