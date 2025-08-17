"""
新闻收集模块
实现从多个数据源收集A股相关新闻的功能
"""

import concurrent.futures
import hashlib
import os
import re
import time
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup

from .utils.database import NewsItem, db_manager
from .utils.logger import get_logger

logger = get_logger("news_collector")


class NewsCollector:
    """新闻收集器主类"""

    def __init__(self, config_path: str = None):
        """
        初始化新闻收集器

        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.config.get("system", {}).get(
                    "user_agent",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                )
            }
        )

        # 设置请求超时
        self.timeout = self.config.get("system", {}).get("request_timeout", 30)

        # 并发控制
        self.max_workers = self.config.get("system", {}).get(
            "max_concurrent_requests", 5
        )
        self._lock = Lock()

        # 统计信息
        self.stats = {"collected": 0, "duplicates": 0, "errors": 0, "sources": {}}

    def _load_config(self, config_path: Optional[str]) -> dict:
        """加载配置文件"""
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), "../config/config.yaml"
            )

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}

    def collect_all_news(self) -> List[NewsItem]:
        """
        从所有配置的新闻源收集新闻

        Returns:
            List[NewsItem]: 收集到的新闻列表
        """
        logger.info("开始收集新闻...")
        all_news = []

        news_config = self.config.get("news_collection", {})
        sources = news_config.get("sources", {})

        # 收集RSS新闻
        rss_feeds = sources.get("rss_feeds", [])
        if rss_feeds:
            rss_news = self._collect_rss_news(rss_feeds)
            all_news.extend(rss_news)

        # 收集API新闻
        api_sources = sources.get("api_sources", {})
        if api_sources:
            api_news = self._collect_api_news(api_sources)
            all_news.extend(api_news)

        # 收集网页爬虫新闻（谨慎使用）
        web_scraping = sources.get("web_scraping", [])
        if web_scraping:
            web_news = self._collect_web_news(web_scraping)
            all_news.extend(web_news)

        # 过滤和去重
        filtered_news = self._filter_and_deduplicate(all_news)

        # 保存到数据库
        if filtered_news:
            saved_count = db_manager.save_news_items_batch(filtered_news)
            logger.info(
                f"新闻收集完成: 收集 {len(all_news)} 条，过滤后 {len(filtered_news)} 条，保存 {saved_count} 条"
            )
        else:
            logger.info("未收集到新的新闻")

        self._log_stats()
        return filtered_news

    def _collect_rss_news(self, rss_feeds: List[Dict]) -> List[NewsItem]:
        """
        收集RSS新闻

        Args:
            rss_feeds: RSS源配置列表

        Returns:
            List[NewsItem]: 新闻列表
        """
        news_list = []

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            future_to_feed = {
                executor.submit(self._fetch_rss_feed, feed): feed
                for feed in rss_feeds
                if feed.get("enabled", True)
            }

            for future in concurrent.futures.as_completed(future_to_feed):
                feed = future_to_feed[future]
                try:
                    feed_news = future.result()
                    news_list.extend(feed_news)

                    with self._lock:
                        self.stats["sources"][feed["name"]] = len(feed_news)

                except Exception as e:
                    logger.error(f"RSS源 {feed['name']} 收集失败: {e}")
                    with self._lock:
                        self.stats["errors"] += 1

        return news_list

    def _fetch_rss_feed(self, feed_config: Dict) -> List[NewsItem]:
        """
        获取单个RSS源的新闻

        Args:
            feed_config: RSS源配置

        Returns:
            List[NewsItem]: 新闻列表
        """
        news_list = []

        try:
            logger.debug(f"获取RSS源: {feed_config['name']}")

            # 解析RSS
            feed = feedparser.parse(feed_config["url"])

            if hasattr(feed, "bozo") and feed.bozo:
                logger.warning(f"RSS源格式异常: {feed_config['name']}")

            for entry in feed.entries:
                try:
                    # 创建新闻项
                    news_item = NewsItem()
                    news_item.title = entry.get("title", "").strip()
                    news_item.content = self._extract_content_from_entry(entry)
                    news_item.source = feed_config["name"]
                    news_item.url = entry.get("link", "")
                    news_item.category = feed_config.get("category", "未分类")

                    # 解析发布时间
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        news_item.publish_time = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, "published"):
                        news_item.publish_time = self._parse_time_string(
                            entry.published
                        )
                    else:
                        news_item.publish_time = datetime.now()

                    # 提取关键词
                    news_item.keywords = self._extract_keywords(
                        news_item.title, news_item.content
                    )

                    if news_item.title:  # 确保有标题
                        news_list.append(news_item)

                except Exception as e:
                    logger.error(f"处理RSS条目失败: {e}")
                    continue

            logger.info(f"RSS源 {feed_config['name']} 获取到 {len(news_list)} 条新闻")

        except Exception as e:
            logger.error(f"获取RSS源失败 {feed_config['name']}: {e}")

        return news_list

    def _collect_api_news(self, api_sources: Dict) -> List[NewsItem]:
        """
        收集API新闻

        Args:
            api_sources: API源配置

        Returns:
            List[NewsItem]: 新闻列表
        """
        news_list = []

        # 东方财富API
        if "eastmoney" in api_sources and api_sources["eastmoney"].get("enabled"):
            eastmoney_news = self._fetch_eastmoney_news(api_sources["eastmoney"])
            news_list.extend(eastmoney_news)

        return news_list

    def _fetch_eastmoney_news(self, config: Dict) -> List[NewsItem]:
        """
        获取东方财富新闻数据

        Args:
            config: 东方财富API配置

        Returns:
            List[NewsItem]: 新闻列表
        """
        news_list = []

        try:
            url = config["base_url"]
            params = config.get("params", {})

            logger.debug("获取东方财富数据...")

            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            # 东方财富返回的是JSONP格式，需要处理
            content = response.text
            if content.startswith("jQuery"):
                # 提取JSON部分
                start = content.find("(") + 1
                end = content.rfind(")")
                json_str = content[start:end]

                import json

                data = json.loads(json_str)

                # 解析股票数据为新闻格式
                if "data" in data and "diff" in data["data"]:
                    for item in data["data"]["diff"]:
                        try:
                            news_item = NewsItem()
                            news_item.title = f"股票动态: {item.get('f14', '未知')} ({item.get('f12', '')})"
                            news_item.content = self._format_stock_data(item)
                            news_item.source = "东方财富API"
                            news_item.category = "股票行情"
                            news_item.publish_time = datetime.now()
                            news_item.url = (
                                f"http://quote.eastmoney.com/{item.get('f12', '')}.html"
                            )
                            news_item.keywords = ["A股", "股票", "行情"]

                            news_list.append(news_item)

                        except Exception as e:
                            logger.error(f"处理东方财富数据项失败: {e}")
                            continue

            logger.info(f"东方财富API获取到 {len(news_list)} 条数据")

        except Exception as e:
            logger.error(f"获取东方财富数据失败: {e}")

        return news_list

    def _format_stock_data(self, item: Dict) -> str:
        """
        格式化股票数据为新闻内容

        Args:
            item: 股票数据项

        Returns:
            str: 格式化的内容
        """
        try:
            name = item.get("f14", "未知股票")
            code = item.get("f12", "")
            price = item.get("f2", 0)
            change = item.get("f3", 0)
            change_pct = item.get("f3", 0)
            volume = item.get("f5", 0)
            amount = item.get("f6", 0)

            content = f"""
股票名称: {name} ({code})
最新价格: {price}
涨跌额: {change}
涨跌幅: {change_pct}%
成交量: {volume}
成交额: {amount}
数据时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            return content.strip()

        except Exception as e:
            logger.error(f"格式化股票数据失败: {e}")
            return "股票数据解析失败"

    def _collect_web_news(self, web_sources: List[Dict]) -> List[NewsItem]:
        """
        收集网页爬虫新闻（谨慎使用）

        Args:
            web_sources: 网页源配置列表

        Returns:
            List[NewsItem]: 新闻列表
        """
        news_list = []

        for source in web_sources:
            if not source.get("enabled", False):
                continue

            try:
                source_news = self._scrape_website(source)
                news_list.extend(source_news)

                # 添加延迟避免被封
                delay = source.get("delay", 2)
                time.sleep(delay)

            except Exception as e:
                logger.error(f"爬取网站失败 {source['name']}: {e}")
                self.stats["errors"] += 1

        return news_list

    def _scrape_website(self, source: Dict) -> List[NewsItem]:
        """
        爬取单个网站

        Args:
            source: 网站配置

        Returns:
            List[NewsItem]: 新闻列表
        """
        news_list = []

        try:
            logger.debug(f"爬取网站: {source['name']}")

            response = self.session.get(source["base_url"], timeout=self.timeout)
            response.raise_for_status()
            response.encoding = "utf-8"

            soup = BeautifulSoup(response.text, "html.parser")
            selectors = source.get("selectors", {})

            # 查找新闻标题
            title_selector = selectors.get("title", "h1, h2, h3")
            titles = soup.select(title_selector)

            for title_elem in titles[:10]:  # 限制数量
                try:
                    news_item = NewsItem()
                    news_item.title = title_elem.get_text().strip()
                    news_item.source = source["name"]
                    news_item.category = source.get("category", "网页爬虫")
                    news_item.publish_time = datetime.now()

                    # 尝试获取链接
                    link_elem = title_elem.find("a") or title_elem.find_parent("a")
                    if link_elem and link_elem.get("href"):
                        news_item.url = urljoin(source["base_url"], link_elem["href"])

                    # 尝试获取内容
                    content_selector = selectors.get("content")
                    if content_selector:
                        content_elem = soup.select_one(content_selector)
                        if content_elem:
                            news_item.content = content_elem.get_text().strip()[
                                :500
                            ]  # 限制长度

                    # 提取关键词
                    news_item.keywords = self._extract_keywords(
                        news_item.title, news_item.content
                    )

                    if news_item.title:
                        news_list.append(news_item)

                except Exception as e:
                    logger.error(f"处理网页元素失败: {e}")
                    continue

            logger.info(f"网站 {source['name']} 爬取到 {len(news_list)} 条新闻")

        except Exception as e:
            logger.error(f"爬取网站失败: {e}")

        return news_list

    def _extract_content_from_entry(self, entry) -> str:
        """
        从RSS条目中提取内容

        Args:
            entry: RSS条目

        Returns:
            str: 提取的内容
        """
        content = ""

        # 尝试多个字段
        for field in ["content", "summary", "description"]:
            if hasattr(entry, field):
                field_content = getattr(entry, field)
                if isinstance(field_content, list) and field_content:
                    content = field_content[0].get("value", "")
                elif isinstance(field_content, str):
                    content = field_content
                break

        # 清理HTML标签
        if content:
            soup = BeautifulSoup(content, "html.parser")
            content = soup.get_text().strip()

        return content[:1000]  # 限制长度

    def _parse_time_string(self, time_str: str) -> datetime:
        """
        解析时间字符串

        Args:
            time_str: 时间字符串

        Returns:
            datetime: 解析后的时间
        """
        try:
            from dateutil import parser

            return parser.parse(time_str)
        except:
            return datetime.now()

    def _extract_keywords(self, title: str, content: str) -> List[str]:
        """
        提取关键词

        Args:
            title: 标题
            content: 内容

        Returns:
            List[str]: 关键词列表
        """
        keywords = []
        text = f"{title} {content}".lower()

        # 从配置中获取关键词
        include_keywords = (
            self.config.get("news_collection", {})
            .get("keywords", {})
            .get("include", [])
        )

        for keyword in include_keywords:
            if keyword.lower() in text:
                keywords.append(keyword)

        return list(set(keywords))  # 去重

    def _filter_and_deduplicate(self, news_list: List[NewsItem]) -> List[NewsItem]:
        """
        过滤和去重新闻

        Args:
            news_list: 原始新闻列表

        Returns:
            List[NewsItem]: 过滤后的新闻列表
        """
        filtered_news = []
        seen_titles = set()

        keywords_config = self.config.get("news_collection", {}).get("keywords", {})
        include_keywords = keywords_config.get("include", [])
        exclude_keywords = keywords_config.get("exclude", [])

        for news in news_list:
            # 跳过空标题
            if not news.title.strip():
                continue

            # 去重检查
            title_hash = hashlib.md5(news.title.encode()).hexdigest()
            if title_hash in seen_titles:
                self.stats["duplicates"] += 1
                continue

            # 数据库去重检查
            if db_manager.check_news_exists(news.title, news.url):
                self.stats["duplicates"] += 1
                continue

            # 关键词过滤
            text = f"{news.title} {news.content}".lower()

            # 检查排除关键词
            if exclude_keywords and any(
                keyword.lower() in text for keyword in exclude_keywords
            ):
                continue

            # 检查包含关键词（如果配置了的话）
            if include_keywords and not any(
                keyword.lower() in text for keyword in include_keywords
            ):
                continue

            seen_titles.add(title_hash)
            filtered_news.append(news)
            self.stats["collected"] += 1

        return filtered_news

    def _log_stats(self):
        """记录统计信息"""
        logger.info("=== 收集统计 ===")
        logger.info(f"收集数量: {self.stats['collected']}")
        logger.info(f"重复数量: {self.stats['duplicates']}")
        logger.info(f"错误数量: {self.stats['errors']}")

        if self.stats["sources"]:
            logger.info("=== 来源统计 ===")
            for source, count in self.stats["sources"].items():
                logger.info(f"{source}: {count} 条")

    def get_stats(self) -> Dict[str, Any]:
        """
        获取收集器统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        return {**self.stats, "last_collection_time": datetime.now().isoformat()}


def collect_news() -> List[NewsItem]:
    """
    便捷函数：收集新闻

    Returns:
        List[NewsItem]: 收集到的新闻列表
    """
    collector = NewsCollector()
    return collector.collect_all_news()


if __name__ == "__main__":
    # 测试收集功能
    news_list = collect_news()
    print(f"收集到 {len(news_list)} 条新闻")
