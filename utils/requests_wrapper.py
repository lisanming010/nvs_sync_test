import requests
import json
import functools
from requests.packages import urllib3
from utils.logger_config import requests_logger


class RequestWrap:
    """requests封装类"""
    def __init__(self):
        urllib3.disable_warnings()

        self.logger = requests_logger
        self.req_session = requests.session()
        self.verify = False
        self.url = 'https://10.16.221.154:8443'

    def close_session(self):
        """关闭session"""
        self.req_session.close()

    def _res_handing(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            res_raw = func(*args, **kwargs)
            res_code = res_raw.status_code
            args[0].logger.debug(f'cookies：{res_raw.cookies.get_dict()}')
            args[0].logger.debug(f'请求头：{res_raw.request.headers}')
            args[0].logger.debug(f'请求体：{res_raw.request.body}')
            # 请求响应码判断
            if res_code >= 400:
                args[0].logger.error(f'请求失败！请求返回响应码：{res_code}，请求路径：{args[1]}')
                args[0].logger.error(f'cookies：{res_raw.cookies.get_dict()}')
                args[0].logger.error(f'响应体：{res_raw.text}')
                raise RuntimeError('请求失败')
            #响应体处理
            if res_raw.request.method == 'POST':
                try:
                    res_json = res_raw.json()
                except requests.exceptions.JSONDecodeError:
                    args[0].logger.error(f'response转换json失败，\nresponse:\n{res_raw}')
                    # raise RuntimeError('response转换失败')
                    return res_raw
                else:
                    task_code = res_json.get('code', '')
                    if task_code != 'ok':
                        args[0].logger.error(f'任务下发失败，任务响应：{task_code}，响应体：\n{res_json}')
                        raise RuntimeError('任务下发失败')
                    try:
                        task_data_code = res_json['data'].get('msgCode', '')
                    except AttributeError:
                        task_data_code = ''
                    if task_data_code != '' and task_data_code != 'ok':
                        args[0].logger.error(f'任务下发失败，任务响应码：{task_data_code}，响应体：\n{res_json}')
                        raise RuntimeError('任务下发失败')
                    return json.dumps(res_json, ensure_ascii=False)
            if res_raw.request.method == 'GET':
                try:
                    res = json.dumps(res_raw.json(), ensure_ascii=False)
                except requests.exceptions.JSONDecodeError:
                    args[0].logger.error(f'response转换json失败，\nresponse:\n{res_raw}')
                    res = res_raw
                return res
        return wrapper
    @_res_handing
    def post(self, api_path:str, payload:any, params:str, headers={}, allow_redirects=True)-> requests.Response:
        """
        post包装函数，期望响应值为200的json序列化对象，若响应体无法执行.json()反序列化则抛出error，
        响应码非200、响应体中task_code非‘OK’均会抛出错误
        
        :param api_path: 请求API路径
        :type api_path: str
        :param payload: post请求体
        :type payload: any
        :param headers: 请求头，默认值为空，使用session配置
        :type headers: dict
        :allow_redirects: 允许重定向，默认值为True
        :type allow_redirects: bool
        :return: json序列化后的响应体
        :rtype: Response
        """
        url = self.url + api_path
        self.logger.debug(f'发起请求：POST {url}')
        res_raw = self.req_session.post(url, data=payload, params=params, headers=headers, verify=self.verify, allow_redirects=allow_redirects)
        return res_raw

    @_res_handing
    def get(self, api_path:str, params:str='', headers={})-> requests.Response:
        url = self.url + api_path
        self.logger.debug(f'发起请求：GET {url}')
        res_raw = self.req_session.get(url, params=params, headers=headers, verify=self.verify)
        return res_raw
    
    def get_session_cookies(self)-> dict:
        """
        返回当前会话的cookies

        :return: cookies
        :rtype: dict
        """
        return self.req_session.cookies.get_dict()

    def session_header_update(self, header:dict)-> None:
        """
        更新当前会话的全局header

        :param header: header
        :type header: dict
        :return: None
        """
        self.req_session.headers.update(header)

        
        
    
    
