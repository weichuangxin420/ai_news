"""
配置管理模块
处理应用程序配置的加载、验证和管理
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .utils.logger import get_logger

logger = get_logger("config_manager")


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path or self._find_config_file()
        self.config = {}
        self._load_config()
        self._validate_config()
        self._set_defaults()

    def _find_config_file(self) -> str:
        """查找配置文件"""
        possible_paths = [
            "config/config.yaml",
            "config.yaml",
            "config/config.yml",
            "config.yml",
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        # 如果找不到配置文件，使用示例配置
        example_path = "config/config.yaml.example"
        if os.path.exists(example_path):
            logger.warning(
                f"未找到配置文件，建议复制 {example_path} 为 config/config.yaml"
            )
            return example_path

        # 创建默认配置文件路径
        return "config/config.yaml"

    def _load_config(self):
        """加载配置文件"""
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"配置文件不存在: {self.config_path}，将使用默认配置")
                self.config = {}
                return

            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}

            # 处理环境变量替换
            self._resolve_env_vars(self.config)

            logger.info(f"配置文件加载成功: {self.config_path}")

        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            self.config = {}

    def _resolve_env_vars(self, obj):
        """递归解析环境变量"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                obj[key] = self._resolve_env_vars(value)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                obj[i] = self._resolve_env_vars(item)
        elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
            # 解析环境变量 ${VAR_NAME}
            env_var = obj[2:-1]
            return os.getenv(env_var, obj)  # 如果环境变量不存在，返回原值

        return obj

    def _validate_config(self):
        """验证配置"""
        errors = []

        # 验证必要的配置节
        required_sections = ["news_collection", "ai_analysis", "database"]
        for section in required_sections:
            if section not in self.config:
                errors.append(f"缺少必要配置节: {section}")

        # 验证新闻收集配置
        if "news_collection" in self.config:
            news_config = self.config["news_collection"]
            if "sources" not in news_config:
                errors.append("新闻收集配置缺少 'sources' 节")

        # 验证AI分析配置
        if "ai_analysis" in self.config:
            ai_config = self.config["ai_analysis"]
            if "deepseek" not in ai_config:
                errors.append("AI分析配置缺少 'deepseek' 节")

        if errors:
            logger.warning("配置验证发现问题:")
            for error in errors:
                logger.warning(f"  - {error}")

    def _set_defaults(self):
        """设置默认值"""
        defaults = {
            "news_collection": {
                "collection_interval": 30,
                "sources": {"rss_feeds": [], "api_sources": {}, "web_scraping": []},
                "keywords": {
                    "include": ["A股", "股市", "上证", "深证", "创业板"],
                    "exclude": ["广告", "推广"],
                },
            },
            "ai_analysis": {
                "deepseek": {
                    "model": "deepseek-chat",
                    "base_url": "https://api.deepseek.com/v1",
                    "max_tokens": 2000,
                    "temperature": 0.1,
                },
                "analysis_params": {
                    "batch_size": 10, 
                    "max_concurrent": 5,
                    "timeout": 30, 
                    "retry_count": 3
                },
            },
            "email": {
                "smtp": {"server": "smtp.qq.com", "port": 587, "use_tls": True},
                "recipients": [],
                "template": {
                    "subject": "AI新闻分析报告 - {date}",
                    "from_name": "AI新闻助手",
                },
            },
            "database": {
                "sqlite": {"db_path": "data/news.db"},
                "retention": {"max_days": 30, "cleanup_interval": 24},
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "data/logs/app.log",
                "max_size": "10MB",
                "backup_count": 5,
            },
            "system": {
                "timezone": "Asia/Shanghai",
                "user_agent": "AI-News-Collector/1.0",
                "request_timeout": 30,
                "max_concurrent_requests": 5,
            },
        }

        # 递归合并默认值
        self.config = self._merge_configs(defaults, self.config)

    def _merge_configs(
        self, default: Dict[str, Any], user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        递归合并配置字典

        Args:
            default: 默认配置
            user: 用户配置

        Returns:
            Dict[str, Any]: 合并后的配置
        """
        result = default.copy()

        for key, value in user.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号分隔的嵌套键

        Args:
            key: 配置键，如 'news_collection.collection_interval'
            default: 默认值

        Returns:
            Any: 配置值
        """
        keys = key.split(".")
        value = self.config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any):
        """
        设置配置值

        Args:
            key: 配置键
            value: 配置值
        """
        keys = key.split(".")
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def save(self, path: Optional[str] = None):
        """
        保存配置到文件

        Args:
            path: 保存路径，默认为当前配置文件路径
        """
        save_path = path or self.config_path

        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            with open(save_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    self.config,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    indent=2,
                )

            logger.info(f"配置文件保存成功: {save_path}")

        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            raise

    def reload(self):
        """重新加载配置文件"""
        self._load_config()
        self._validate_config()
        self._set_defaults()
        logger.info("配置文件重新加载完成")

    def get_news_sources(self) -> Dict[str, Any]:
        """获取新闻源配置"""
        return self.get("news_collection.sources", {})

    def get_ai_config(self) -> Dict[str, Any]:
        """获取AI配置"""
        return self.get("ai_analysis", {})

    def get_email_config(self) -> Dict[str, Any]:
        """获取邮箱配置"""
        return self.get("email", {})

    def get_database_config(self) -> Dict[str, Any]:
        """获取数据库配置"""
        return self.get("database", {})

    def is_source_enabled(self, source_type: str, source_name: str) -> bool:
        """
        检查指定数据源是否启用

        Args:
            source_type: 数据源类型 (rss_feeds, api_sources, web_scraping)
            source_name: 数据源名称

        Returns:
            bool: 是否启用
        """
        sources = self.get_news_sources()

        if source_type not in sources:
            return False

        if source_type == "rss_feeds":
            for source in sources[source_type]:
                if source.get("name") == source_name:
                    return source.get("enabled", False)
        elif source_type == "api_sources":
            source_config = sources[source_type].get(source_name, {})
            return source_config.get("enabled", False)
        elif source_type == "web_scraping":
            for source in sources[source_type]:
                if source.get("name") == source_name:
                    return source.get("enabled", False)

        return False

    def get_keywords(self) -> Dict[str, list]:
        """获取关键词配置"""
        return self.get("news_collection.keywords", {"include": [], "exclude": []})

    def validate_api_keys(self) -> Dict[str, bool]:
        """
        验证API密钥是否存在

        Returns:
            Dict[str, bool]: 各服务的API密钥状态
        """
        status = {}

        # 检查DeepSeek API密钥
        deepseek_key = self.get("ai_analysis.deepseek.api_key", "")
        status["deepseek"] = bool(
            deepseek_key and deepseek_key != "${DEEPSEEK_API_KEY}"
        )

        # 检查邮箱配置
        email_user = self.get("email.smtp.username", "")
        email_pass = self.get("email.smtp.password", "")
        status["email"] = bool(
            email_user
            and email_pass
            and not email_user.startswith("${")
            and not email_pass.startswith("${")
        )

        return status

    def create_example_config(self, output_path: str = "config/config.yaml.example"):
        """
        创建示例配置文件

        Args:
            output_path: 输出路径
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 复制当前配置作为示例
            example_config = self.config.copy()

            # 替换敏感信息为占位符
            if (
                "ai_analysis" in example_config
                and "deepseek" in example_config["ai_analysis"]
            ):
                example_config["ai_analysis"]["deepseek"][
                    "api_key"
                ] = "${DEEPSEEK_API_KEY}"

            if "email" in example_config and "smtp" in example_config["email"]:
                example_config["email"]["smtp"]["username"] = "${EMAIL_USERNAME}"
                example_config["email"]["smtp"]["password"] = "${EMAIL_PASSWORD}"

            with open(output_path, "w", encoding="utf-8") as f:
                f.write("# AI新闻收集与影响分析系统 - 配置文件示例\n")
                f.write("# 复制此文件为 config.yaml 并根据需要修改\n\n")
                yaml.dump(
                    example_config,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    indent=2,
                )

            logger.info(f"示例配置文件创建成功: {output_path}")

        except Exception as e:
            logger.error(f"创建示例配置文件失败: {e}")
            raise


# 全局配置管理器实例
config_manager = ConfigManager()


def get_config() -> ConfigManager:
    """获取全局配置管理器实例"""
    return config_manager


if __name__ == "__main__":
    # 测试配置管理器
    config = ConfigManager()

    print("配置验证结果:")
    api_status = config.validate_api_keys()
    for service, status in api_status.items():
        print(f"  {service}: {'✓' if status else '✗'}")

    print(f"\n数据库路径: {config.get('database.sqlite.db_path')}")
    print(f"收集间隔: {config.get('news_collection.collection_interval')} 分钟")
    print(f"AI模型: {config.get('ai_analysis.deepseek.model')}")
