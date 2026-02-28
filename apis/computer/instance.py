import json
from copy import deepcopy
from utils.logger_config import running_logger
from utils.tools import watch_task

CREATE_DATA = {
    "architecture":"x86_64",
    "deadline":None,
    "description":"",
    "disableTermination":False,
    "guestOSId":"",
    "vclusterId":"vcr-aarch64",
    "icon":"",
    "instanceName":"test",
    "bootFromKernel":False,
    "kernelId":"",
    "isHA":True,
    "isImportant":False,
    "password":"",
    "platform":"linux",
    "groupId":"instance-default",
    "scheduleGroup":"",
    "scheduleType":"ROUND_ROBIN",
    "expectedHost":"",
    "rebootIfFailed":False,
    "priority":5,
    "publicKey":"",
    "tag":"",
    "bootType":"bios",
    "poolId":"sp-00e9cff7d0",
    "hostId":"",
    "vmConfig":{
        "architecture":"aarch64",
        "isUefi":False,
        "enableKvmClock":True,
        "enableDiskEncryption":False,
        "enableEscapeDetection":False,
        "poolId":"sp-00e9cff7d0",
        "poolType":"",
        "cpu":{
            "cpuCurrent":2,
            "cpuSocket":1,
            "corePerSocket":2,
            "enableHostCpu":False,
            "enableCpuHotPlug":False,
            "enableMonopolyCpu":False,
            "monopolyConfig":None,
            "cpuFrequency":0,
            "quota":0,
            "isAutoDedicatedPCpu":False
        },
        "memory":{
            "memorySize":2048,
            "enableHugePage":False,
            "memHugePage":None,
            "enableMemHotPlug":False,
            "hardLimit":0
        },
        "hardDisk":[
            {
                "volumeSize":20,
                "volumeName":"",
                "volumeId":"",
                "hasOperatingSystem":True,
                "srcFileId":"",
                "srcSnapshotId":"",
                "iopsLimit":0,
                "bpsLimit":0,
                "slot":0,
                "srcIncBackupVolId":"",
                "kmsId":"",
                "encryptedKey":"",
                "isEncrypted":False,
                "poolId":"sp-00e9cff7d0",
                "ioReadRate":0,
                "ioWriteRate":0,
                "ioReadPs":0,
                "ioWritePs":0
            }
        ],
        "cdrom":[
            {
                "isoId":""
            },
            {
                "isoId":""
            }
        ],
        "networkInterfaces":[
            {
                "uplinkDeviceId":"dvs-008fe93a76",
                "connectedToName":"内部策略交换机",
                "firewallId":"",
                "ipv4Enable":True,
                "gatewayIp":"",
                "ipAddress":"",
                "netMask":"",
                "isUplink":True,
                "hwAddr":"",
                "ipCheck":True,
                "inBandwidth":0,
                "outBandwidth":0,
                "txChecksumDisabled":False,
                "inBrustBandwidth":0,
                "outBrustBandwidth":0,
                "ipv6Enable":False,
                "ipv6Address":"",
                "ipv6Gateway":"",
                "ipv6NetMask":"",
                "queues":0,
                "ipv4SecondaryIpCount":0,
                "ipv4SecondaryIps":[],
                "ipv4SecondaryIpsStr":"",
                "ipv6SecondaryIpCount":0,
                "ipv6SecondaryIps":[],
                "ipv6SecondaryIpsStr":""
            }
        ],
        "usb":[],
        "pci":[],
        "extendDomain":"",
        "extendDevices":"",
        "aliveEdit":None
    },
    "cloneMode":"fastFullClone",
    "count":1,
    "srcInstanceId":"i-009df1cf60",
    "srcTemplateId":"vmt-00e8c69c7e",
    "startAfterCreated":True,
    "sufBegin":1,
    "tags":None,
    "createType":"CREATE_TYPE_TEMPLATE"
}


class Instance:
    def __init__(self, req_session):
        self.logger = running_logger
        self.req_session = req_session

        self.create_by_templ_api = '/bcs/api/compute/instance/createByTmpl'
        self.view_vm_details_api = '/bcs/api/compute/instance/get'
        self.shutdown_vm_api = '/bcs/api/compute/instance/stop'
        self.delete_vm_api = '/bcs/api/compute/instance/delete'

    def get_create_payload_tmpl(self)->dict:
        return deepcopy(CREATE_DATA)

    def get_vm_info(self, vm_id:str)-> str:
        """
        查询指定ID的虚拟机信息

        :param vm_id: 虚拟机ID
        :param req_session: 请求会话
        :return: 虚拟机信息
        :rtype: str
        """
        payload = f'instanceId={vm_id}&needMonitorData=true&wrapVmConfig=true'
        res = self.req_session.get(self.view_vm_details_api, payload)
        return res

    def shutdown_vm(self, vm_id:str, is_force:bool=False):
        """
        虚拟机关机,关机失败或任务监控超时则抛出runtimeerror

        :param vm_id: 虚拟机ID
        :param req_session: 请求会话
        :param is_force: 是否强制关机
        """

        payload = {"force":is_force,"instanceIds":[vm_id],"reason":"pytest shutdown"}
        print(payload)
        res = self.req_session.post(self.shutdown_vm_api, json.dumps(payload), '', headers={'Content-Type':'application/json'})  
        res = json.loads(res) 
        task_id = res['data']['taskIds'][0]
        if not watch_task(task_id, self.req_session):
            raise RuntimeError(f'虚拟机关机失败，虚拟机名称：{vm_id}')

    def delete_vm(self, vm_id:str, login_user_passwd:str,
              deleteDirectly:bool=True, skip_if_shutdown_fail:bool=True):
        """
        关闭虚拟机并删除

        :param vm_id: 虚拟机ID
        :param login_user_passwd: 当前登录用户的密码，混淆后
        :param req_session: 请求会话
        :param deleteDirectly: 是否直接删除虚拟机，False时则移至回收站
        :param skip_if_shutdown_fail: 虚拟机关机失败时是否忽略该虚拟机，false时关机失败则抛出异常
        """
        try:
            self.shutdown_vm(vm_id)
        except RuntimeError as e:
            self.logger.warning(f'虚拟机关机失败，虚拟机名称：{vm_id}')
            if not skip_if_shutdown_fail:
                raise e
            self.logger.debug(f'删除操作跳过虚拟机：{vm_id}')
        else:
            payload = {
                "instanceIds":[vm_id],
                "deleteDirectly":True,
                "loginPassword":login_user_passwd
                }

            res = self.req_session.post(self.delete_vm_api, json.dumps(payload), '', headers={'Content-Type':'application/json'})

    def create_vm(self, payload:dict)->str:
        res = self.req_session.post(self.create_by_templ_api, json.dumps(payload), '', headers={'Content-Type': 'application/json'})
        return res