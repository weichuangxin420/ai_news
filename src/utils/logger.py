"""
日志工具模块
提供统一的日志记录功能
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

import yaml


class Logger:
    """日志管理器"""

    _instances = {}

    def __new__(cls, name: str = "ai_news", config_path: Optional[str] = None):
        """单例模式确保每个名称只有一个日志实例"""
        if name not in cls._instances:
            cls._instances[name] = super().__new__(cls)
        return cls._instances[name]

    def __init__(self, name: str = "ai_news", config_path: Optional[str] = None):
        """
        初始化日志器

        Args:
            name: 日志器名称
            config_path: 配置文件路径
        """
        if hasattr(self, "_initialized"):
            return

        self._initialized = True
        self.name = name
        self.logger = logging.getLogger(name)

        # 加载配置
        self.config = self._load_config(config_path)

        # 设置日志级别
        log_level = self.config.get("logging", {}).get("level", "INFO")
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # 避免重复添加处理器
        if not self.logger.handlers:
            self._setup_handlers()

    def _load_config(self, config_path: Optional[str]) -> dict:
        """加载配置文件"""
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), "../../config/config.yaml"
            )

        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return {}
        else:
            print(f"配置文件不存在: {config_path}")
            return {}

    def _setup_handlers(self):
        """设置日志处理器"""
        logging_config = self.config.get("logging", {})

        # 日志格式
        formatter = logging.Formatter(
            logging_config.get(
                "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # 文件处理器
        log_file = logging_config.get("file", "data/logs/app.log")
        log_dir = os.path.dirname(log_file)

        # 确保日志目录存在
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # 创建轮转文件处理器
        max_size_str = logging_config.get("max_size", "10MB")
        max_size = self._parse_size(max_size_str)
        backup_count = logging_config.get("backup_count", 5)

        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_size, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def _parse_size(self, size_str: str) -> int:
        """解析大小字符串（如'10MB'）为字节数"""
        size_str = size_str.upper()
        multipliers = {"B": 1, "KB": 1024, "MB": 1024 * 1024, "GB": 1024 * 1024 * 1024}

        for suffix, multiplier in multipliers.items():
            if size_str.endswith(suffix):
                try:
                    return int(size_str[: -len(suffix)]) * multiplier
                except ValueError:
                    break

        # 默认10MB
        return 10 * 1024 * 1024

    def debug(self, message: str):
        """记录调试信息"""
        self.logger.debug(message)

    def info(self, message: str):
        """记录一般信息"""
        self.logger.info(message)

    def warning(self, message: str):
        """记录警告信息"""
        self.logger.warning(message)

    def error(self, message: str):
        """记录错误信息"""
        self.logger.error(message)

    def critical(self, message: str):
        """记录严重错误信息"""
        self.logger.critical(message)

    def exception(self, message: str):
        """记录异常信息（包含堆栈跟踪）"""
        self.logger.exception(message)


# 全局日志实例
logger = Logger()


def get_logger(name: str = "ai_news") -> Logger:
    """获取日志器实例"""
    return Logger(name)


# 便捷函数
def debug(message: str):
    """记录调试信息"""
    logger.debug(message)


def info(message: str):
    """记录一般信息"""
    logger.info(message)


def warning(message: str):
    """记录警告信息"""
    logger.warning(message)


def error(message: str):
    """记录错误信息"""
    logger.error(message)


def critical(message: str):
    """记录严重错误信息"""
    logger.critical(message)


def exception(message: str):
    """记录异常信息（包含堆栈跟踪）"""
    logger.exception(message)
