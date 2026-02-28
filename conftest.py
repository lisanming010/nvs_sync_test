import pytest
import json
from utils.requests_wrapper import RequestWrap
from utils.logger_config import running_logger
from urllib.parse import quote

@pytest.fixture(scope='session')
def login(request):
    if hasattr(request, 'param') and request.param != None:
        username, passwd = request.param
    else:
        username = 'admin'
        passwd = 'FBurr8dTjJ2XUg+l36BC0xsihbTIdSWdNdmFFyIv0cTDIyYbm3EF+w+BvphM72vyIbBQ06BrL8+uOXvljZFCYqSCxjhA8B5viv3dRdmiysGFYlYcmiPUy1AWkAyGpZpf79/avKHgECnInEk/GK9CvRT++y47BGx5a9T+kBby9og='
    requests_session = RequestWrap()
    prams = 'client_id=hci&response_type=code&redirect_uri=https%3A%2F%2F10.16.221.154%3A8443%2Fbcs%2Fconsole%2F%23%2Fssoclient%3F_d%3D1770972495295%26returnUrl%3D%252F&scope=openid+profile+email+offline_access+groups&app_logout_url=https%3A%2F%2F10.16.221.154%3A8443%2Fbcs%2Fconsole%2F%23%2Fbcc-ssoclient%3FssoLO%3D1%26_inframe%3Dtrue%26return_url%3D%2F'
    res = requests_session.get('/dex/auth/local', params=prams)

    # prelogin，获取sign
    prelogin_params = 'client_id=hci&response_type=code&redirect_uri=https%3A%2F%2F10.16.221.154%3A8443%2Fbcs%2Fconsole%2F%23%2Fssoclient%3F_d%3D1770972495295%26returnUrl%3D%252F&scope=openid+profile+email+offline_access+groups&app_logout_url=https%3A%2F%2F10.16.221.154%3A8443%2Fbcs%2Fconsole%2F%23%2Fbcc-ssoclient%3FssoLO%3D1%26_inframe%3Dtrue%26return_url%3D%2F'
    prelogin_data = {"login":username,"password":passwd,"pwdType":1,"code":""}
    res = requests_session.post('/dex/auth/local/prelogin', json.dumps(prelogin_data), prelogin_params)
    res_json = json.loads(res)
    sign = res_json['data']['sign']

    # login，获取code
    url_encode = quote(passwd)
    login_params = 'client_id=hci&response_type=code&redirect_uri=https%3A%2F%2F10.16.221.154%3A8443%2Fbcs%2Fconsole%2F%23%2Fssoclient%3F_d%3D1771989316020%26returnUrl%3D%252F&scope=openid+profile+email+offline_access+groups&app_logout_url=https%3A%2F%2F10.16.221.154%3A8443%2Fbcs%2Fconsole%2F%23%2Fbcc-ssoclient%3FssoLO%3D1%26_inframe%3Dtrue%26return_url%3D%2F'
    login_data = f'login={username}&password={url_encode}&sign={sign}&pwdType=1'
    res = requests_session.post('/dex/auth/local/login', login_data, login_params, headers={'Content-Type': 'application/x-www-form-urlencoded'}, allow_redirects=False)
    location = res.headers.get('Location')
    code = location.split('=')[2].split('&')[0]

    # SSOlogin，获取token
    sso_login_payload = {"code":code,"state":"","redirectUrl":""}
    res = requests_session.post('/bcs/api/auth/ssoLogin', json.dumps(sso_login_payload), params='', headers={'Content-Type': 'application/json'})
    print(res)
    token = json.loads(res)['data']['accessToken']

    # 更新session headers
    requests_session.session_header_update({'Authorization': 'Bearer ' + token})

    running_logger.debug(f'{username}登录成功！')
    yield requests_session, username, passwd
    requests_session.close_session()
    running_logger.debug(f'连接关闭')
    
@pytest.mark.parametrize('login', [('admin','FBurr8dTjJ2XUg+l36BC0xsihbTIdSWdNdmFFyIv0cTDIyYbm3EF+w+BvphM72vyIbBQ06BrL8+uOXvljZFCYqSCxjhA8B5viv3dRdmiysGFYlYcmiPUy1AWkAyGpZpf79/avKHgECnInEk/GK9CvRT++y47BGx5a9T+kBby9og=')], indirect=True)
@pytest.fixture(scope='class')
def preare_dvswitch(request):
    pass


    # requests_session.close_session()

# if __name__ == '__main__':
#     login('admin',
#           'FBurr8dTjJ2XUg+l36BC0xsihbTIdSWdNdmFFyIv0cTDIyYbm3EF+w+BvphM72vyIbBQ06BrL8+uOXvljZFCYqSCxjhA8B5viv3dRdmiysGFYlYcmiPUy1AWkAyGpZpf79/avKHgECnInEk/GK9CvRT++y47BGx5a9T+kBby9og=')