import json, time
from utils.logger_config import running_logger
from utils.ssh_host import sshToEnv
from utils.tools import base64_decode
from copy import deepcopy

class GustExec:
    """
    虚拟机内部执行命令并获取返回（QGA）

    :param vm_id: 虚拟机id
    :param ssh_client: ssh连接对象
    """
    def __init__(self, vm_id:str, ssh_client:sshToEnv, exec_node:str):
        self.vm_id = vm_id
        self.ssh_client = ssh_client
        self.exec_node = exec_node
        
        self.exec_struct_dict = {
            "execute":"guest-exec",
            "arguments":{
                "path":"/bin/ls",
                "arg":["/tmp"],
                "capture-output":True
                }
            }
        
    def gust_exec(self, cmd:str, capture_output:bool=True)->tuple:
        """
        命令执行方法，返回命令执行结果包含输出和错误信息

        :param cmd: 命令
        :param capture_output: 是否捕获输出
        :return: 命令执行结果包含输出或错误信息，退出码
        :rtype: tuple
        """

        # 检测虚拟机qga是否就绪
        qga_ready = False
        for i in range(20):
            stdout, stderr = self.ssh_client.exec_cmd(f'ssh {self.exec_node} "virsh dumpxml {self.vm_id}|grep org.qemu.guest_agent.0|grep state"')
            if stderr and 'Authorized users only' not in stderr:
                running_logger.debug(f'虚拟机{self.vm_id}执行命令{cmd}失败，原因：{stderr}')
                raise RuntimeError(f'虚拟机{self.vm_id}执行命令{cmd}失败，原因：{stderr}')
            
            if stdout and 'disconnected' in stdout:
                running_logger.debug(f'虚拟机{self.vm_id}未连接guest agent，请检查虚拟机状态')
            elif stdout != '':
                qga_ready = True
                break
            time.sleep(3)
            running_logger.debug(f'等待虚拟机qga ready，retry：{i}')
        if not qga_ready:
            running_logger.error(f'虚拟机{self.vm_id}未连接guest agent等待在线超时')
            raise RuntimeError(f'虚拟机{self.vm_id}未连接guest agent等待在线超时')
        
        # 调用qga执行命令
        cmd = cmd.split()
        exec_dict = deepcopy(self.exec_struct_dict)
        exec_dict['arguments']['path'] = cmd[0]
        exec_dict['arguments']['arg'] = cmd[1:]
        exec_dict['arguments']['capture-output'] = capture_output
        str_exec_dict = json.dumps(exec_dict).replace('"', '\\"')
        pid_out, _ = self.ssh_client.exec_cmd(f'ssh {self.exec_node} "virsh qemu-agent-command {self.vm_id} \'{str_exec_dict}\' --pretty"')
        pid = json.loads(pid_out)['return']['pid']

        # 解析执行结果
        get_exec_pid_struct_dict = {
            "execute":"guest-exec-status",
            "arguments":{
                "pid":pid
                }
            }
        get_exec_pid_str = json.dumps(get_exec_pid_struct_dict).replace('"', '\\"')

        loop_count = 0
        max_loop = 60
        while True:
            if loop_count > max_loop:
                running_logger.error(f'虚拟机{self.vm_id}执行命令{cmd}失败，原因：执行超时')
                raise RuntimeError(f'虚拟机{self.vm_id}执行命令{cmd}失败，原因：执行超时')

            exec_result, _ = self.ssh_client.exec_cmd(f'ssh {self.exec_node} \"virsh qemu-agent-command {self.vm_id} \'{get_exec_pid_str}\' --pretty\"')
            exec_result = json.loads(exec_result)
            if exec_result['return']['exited']:
                exit_code = exec_result['return']['exitcode']
                break
            else:
                loop_count += 1
                time.sleep(2)
        
        if exit_code == 2:
            print(exec_result)
            err_out = exec_result['return']['err-data']
            err_out = base64_decode(err_out)
            running_logger.debug(f'虚拟机{self.vm_id}执行命令{cmd}失败，命令执行报错：\n{err_out}')
            exec_out = err_out
        else:
            exec_out = exec_result['return']['out-data']
        
        return base64_decode(exec_out), exit_code
