import paramiko
import re, os, hashlib, sys
from pathlib import Path
from functools import wraps
from utils.logger_config import running_logger

class sshToEnv:
    def __init__(self, hostname:str, passwd:str, username='root', port=22):
        '''
        ssh连接操作类
        
        :param hostname: 远程连接名
        :param logger: 日志对象
        :param username: 登录名，默认为root
        :param passwd: 登录密码
        :param port: 登录端口，默认为22
        '''
        self.hostname = hostname
        self.username =username
        self.passwd = passwd
        self.port = port
        self.logger = running_logger

        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def _close_ssh(func):
        '''
        ssh连接回收装饰器
        '''
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                args[0].logger.error(e)
                args[0].ssh.close()
                raise
            else:
                if kwargs.get('close_ssh', True):
                    args[0].ssh.close()
                    args[0].logger.info(f'{func.__qualname__}方法调用ssh链接关闭,func params:{args}')
                return result
        return wrapper

    def ssh_client(self) -> paramiko.SSHClient:
        '''
        ssh连接方法
        '''
        self.ssh.connect(self.hostname, self.port, self.username, self.passwd)

    @_close_ssh
    def exec_cmd(self, cmd:str, ssh_client:paramiko=None, get_pty=False, close_ssh=True) -> tuple:
        '''
        ssh自定义命令执行方法

        :param cmd: 自定义命令
        :param ssh_clinet: paramiko实例对象，决定是否复用外部connect
        :param get_pty: 是否需要pty，一般执行sudo命令时需要，默认为false
        :param close_ssh: 是否自动关闭ssh连接，默认为Ture，自动关闭 
        :return: (stdout, stderr)
        '''
        if ssh_client is None:
            self.ssh_client()
        self.logger.debug(f'exec cmd: {cmd}')
        _, stdout, stderr = self.ssh.exec_command(cmd, get_pty=get_pty)
        return stdout.read().decode(), stderr.read().decode()
    
    @staticmethod
    def local_md5sum(file_full_path:str, bufsize=8192, is_local=True) -> dict:
        '''
        计算MD5，若传递值为文件则直接计算文件md5,若为文件夹则递归计算文件夹下所有文件md5

        :param file_full_path: 路径
        :param bufsize: 缓冲区大小，默认为8192
        :param is_local: 是否为本地文件，默认为True
        :return: {file_full_path: md5}
        '''
        if is_local:
            root = Path(file_full_path)
            if not root.exists():
                raise FileNotFoundError(root)

            def _walk(current: Path, base: Path):
                try:
                    for p in sorted(current.iterdir()):
                        rel = str(p)
                        if p.is_file():
                            h = hashlib.md5()
                            with p.open('rb') as f:
                                for chunk in iter(lambda: f.read(bufsize), b''):
                                    h.update(chunk)
                            yield rel, h.hexdigest()
                        elif p.is_dir():
                            yield from _walk(p, base)
                except NotADirectoryError as e: #捕获到目录名称无效，但已有文件存在校验所以进入次逻辑可能是因为传递的是文件名而非一个路径
                    h = hashlib.md5()
                    with current.open('rb') as f:
                        for chunk in iter(lambda: f.read(bufsize), b''):
                            h.update(chunk)
                    yield str(current), h.hexdigest()
            return dict(_walk(root, root))

    @_close_ssh
    def _md5_check(self, local_file_full_path:str, remote_file_path:str, ssh_client:paramiko.SSHClient='', close_ssh=True) -> tuple:
        """
        远程文件md5与本地文件md5校验，远程文件默认远程操作系统为linux，使用ssh连接执行md5sum

        :param local_file_full_path: 本地文件路径
        :param remote_file_path: 远程文件路径
        :param close_ssh: 调用结束后是否需要自动关闭ssh连接
        :return: (run_code, 本地文件md5, 远程文件md5)
        """
        run_code = True
        local_file_md5 = self.local_md5sum(local_file_full_path)
        remote_file_md5, stderr = self.exec_cmd(f'md5sum {remote_file_path}', ssh_client=ssh_client, close_ssh=close_ssh)

        if stderr != '':
            self.logger.error(stderr)
            run_code = False
            remote_file_md5 = ''
        elif local_file_md5[local_file_full_path] not in remote_file_md5:
            run_code = False
            
        return run_code, local_file_md5, remote_file_md5

    def close_ssh(self):
        """
        手动关闭连接
        """
        self.ssh.close()

    @_close_ssh
    def sftp_file(self, local_file_path:str, remote_file_path:str, 
                  local_file_name:str, remote_file_name:str, ssh_client:paramiko.SSHClient='',
                  flow_direction='upload', close_ssh=True):
        '''
        sftp文件上传/下载方法

        :param local_file_path: 本地文件路径
        :param remote_file_path: 远程文件路径
        :param local_file_name: 本地文件名称
        :param remote_file_name: 远程文件名称
        :param ssh_client: paramiko实例对象，决定是否复用外部connect
        :param flow_direction: 上传/下载方向，默认为上传
        :param close_ssh: 是否自动关闭ssh连接，默认为Ture，自动关闭 
        '''
        self.logger.debug(f'{local_file_name} {flow_direction} start!')
        if ssh_client == '':
            self.ssh_client()

        local_file_full_path = Path(local_file_path).joinpath(local_file_name)
        remote_file_full_path = remote_file_path + '/' + remote_file_name
        
        if flow_direction == 'upload':
            if not local_file_full_path.exists():
                raise FileExistsError(f'{local_file_full_path}不存在')
        elif flow_direction == 'download':
            if not Path(local_file_path).exists():
                raise FileExistsError(f'{local_file_full_path}不存在')

        with self.ssh.open_sftp() as sftp:
            if flow_direction == 'upload':
                sftp.put(local_file_full_path, remote_file_full_path)
            elif flow_direction == 'download':
                sftp.get(remote_file_full_path, local_file_full_path)
            
            md5_check_result, local_file_md5, remote_file_md5 = self._md5_check(str(local_file_full_path), remote_file_full_path, 
                                                                                self.ssh, close_ssh=False)
            if md5_check_result:
                self.logger.debug(f'{remote_file_full_path} {flow_direction}成功！\n本地文件MD5:{local_file_md5}\n远程文件MD5:{remote_file_md5}')
            else:
                self.logger.debug(f'{remote_file_full_path} {flow_direction}失败！\n本地文件MD5:{local_file_md5}\n远程文件MD5:{remote_file_md5}')
                raise RuntimeError(f'{remote_file_full_path} {flow_direction}失败！\n本地文件MD5:{local_file_md5}\n远程文件MD5:{remote_file_md5}')