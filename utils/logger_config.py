import logging
import os
from logging.handlers import RotatingFileHandler

class LoggerConfig:
    def __init__(self):
        # 创建日志目录
        self.LOG_DIR = "./logs"
        if not os.path.exists(self.LOG_DIR):
            os.makedirs(self.LOG_DIR)
        self.LOGGER_CACHE:dict[str, logging.Logger] = {}

        # 定义日志格式
        self.LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        self.DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
        

        logging.getLogger().handlers.clear()
        logging.basicConfig(level=logging.INFO, format=self.LOG_FORMAT, datefmt=self.DATE_FORMAT)

        self.log_level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }

    # 配置根日志器
    def setup_logger(self, logger_name:str, logger_level:str, log_file_size:int, log_file_count:int)->logging.Logger:
        """
        同名logger将使用最先初始化的logger实例
        
        :param logger_name: 日志器名称
        :param logger_level: 日志级别
        :param log_file_size: 单个日志文件大小（MB）
        :param log_file_count: 保留日志文件数量
        :return logger: 返回日志处理器
        """

        # 创建网络请求日志器
        if logger_name in self.LOGGER_CACHE:  # 缓存中已存在该日志器
            print(self.LOGGER_CACHE[logger_name])
            return self.LOGGER_CACHE[logger_name]
        
        logger = logging.getLogger(logger_name)
        logger.setLevel(self.log_level_map[logger_level.upper()])
        logger_handler = RotatingFileHandler(
            filename=os.path.join(self.LOG_DIR, f"{logger_name}.log"),
            maxBytes= log_file_size * 1024 * 1024,  # 单个日志文件最大 10MB
            backupCount=log_file_count,               # 最多保留 5 个备份文件
            encoding='UTF-8'
        )
        logger_handler.setFormatter(logging.Formatter(self.LOG_FORMAT, datefmt=self.DATE_FORMAT))
        logger.addHandler(logger_handler)
        logger.propagate = False  # 防止日志传播到根日志器
        self.LOGGER_CACHE[logger_name] = logger
        return logger
    
    def check_logger_is_exists(self, logger_name:str=''):
        """
        检查是否有名称为logger_name的日志处理器存在，logger_name置空时则返回
        所有已有logger_handler实例名称
        
        :param logger_name: 实例名称，默认为空字符串
        :type logger_name: str
        :return: 返回名称tuple或者指定名称logger_handler实例是否存在
        :rtype: tuple | bool
        """
        if logger_name == '':
            return tuple(self.LOGGER_CACHE.keys())
        
        return True if logger_name in self.LOGGER_CACHE.keys() else False
    
logger_singleton = LoggerConfig()

requests_logger = logger_singleton.setup_logger('requests_logger', 'DEBUG', 50, 5)
running_logger = logger_singleton.setup_logger('running_logger', 'DEBUG', 50, 5)