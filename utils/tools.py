import json
import time
from utils.logger_config import running_logger
from utils.ssh_host import sshToEnv

def watch_task(task_id:str, req_session, time_out:int=300)->bool:
    """
    任务监控方法

    :param task_id: 任务ID
    :param req_session: 请求会话
    :param time_out: 任务执行超时时间，单位秒，默认值为300s
    :return: 任务执行成功返回True，否则返回False
    :rtype: bool
    """
    api_path = f'/bcs/api/system/operlog/getLogsByTaskId'

    payload = {"taskIds":[f"{task_id}"]}
    is_success = False
    loop_count = 0
    max_loop_count = time_out // 3
    while True:
        if loop_count > max_loop_count:
            running_logger.error(f'任务执行超时，任务ID：{task_id}')
            break
        res = req_session.post(api_path, json.dumps(payload), params='', headers={'Content-Type': 'application/json'})
        running_logger.info(f'{res}\n')
        task_status = json.loads(res)['data'][0]['log']['status']
        if task_status == 'success':
            is_success = True
            break
        elif task_status == 'failed':
            break
        else:
            time.sleep(3)
        loop_count += 1

    if is_success:
        running_logger.info(f'任务执行成功，任务ID：{task_id}')
    else:
        running_logger.error(f'任务执行失败，任务ID：{task_id}')
        running_logger.error(f'任务查询结果：{res}')
    
    return is_success

def nvs_map_comparison(ssh:sshToEnv, map_name:str)->bool:
    """
    节点间nvs_map对比，仅实现比较数量

    :param ssh: ssh对象
    :param map_name: 需要比较的nvs_map名称
    """
    stdout, _ = ssh.exec_cmd("cat /etc/hosts|grep host-|awk '{print $1}'")
    node_ip_list = stdout.rstrip().split('\n')
    pop_ip = node_ip_list.pop()

    is_pass = True
    map_lines_tmp, stderr = ssh.exec_cmd(f'ssh {pop_ip} "/bhci/nvs/nvs-tool map dump {map_name}|wc -l"')
    if stderr and 'Authorized users only' not in stderr:
        running_logger.error(f'节点{pop_ip}ssh命令执行失败，命令执行报错：\n{stderr}')
        raise RuntimeError('ssh命令执行失败')

    for ip in node_ip_list:
        stdout, stderr = ssh.exec_cmd(f'ssh {ip} "/bhci/nvs/nvs-tool map dump {map_name}|wc -l"')
        
        if stderr and 'Authorized users only' not in stderr:
            running_logger.error(f'节点{ip}ssh命令执行失败，命令执行报错：\n{stderr}')
            raise RuntimeError('ssh命令执行失败')
        
        if stdout != map_lines_tmp:
            running_logger.error(f'节点{pop_ip}与{ip}的nvs_map不一致，请检查！')
            is_pass = False
            break
        
    return is_pass

def list_id_2_map_id(list_id:str)->str:
    return str(int(list_id, 16))

def map_id_2_list_id(map_id:str)->str:
    return str(hex(map_id)).removeprefix('0x')






        