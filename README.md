``````shell
.
├── Pipfile
├── Pipfile.lock
├── README.md
├── apis #平台相关API抽象类
│   ├── computer #计算
│   │   └── instance.py 
│   └── network #网络
│       ├── dvrouter.py
│       └── dvswitch.py
├── conftest.py #pytest最上层conftest
├── logs #日志目录
├── main.py #程序入口
├── test_dvroute #分布式路由器测试
│   ├── test_create_address_transform.py 
│   └── test_create_dvroute.py
├── test_dvswitch #分布式交换机测试
│   └── test_create_dvswith.py
├── test_firewall #分布式防火墙测试
├── test_vnic #虚拟网卡测试
│   └── test_create_vm.py
└── utils #工具类
    ├── logger_config.py #日志配置
    ├── requests_wrapper.py #requests封装
    ├── ssh_host.py #ssh封装
    └── tools.py #其余工具类
``````

