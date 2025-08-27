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

from ..utils.database import NewsItem, db_manager
from ..utils.logger import get_logger
from .chinanews_rss import ChinaNewsRSSCollector

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
                os.path.dirname(__file__), "../../config/config.yaml"
            )

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}

    def collect_all_news(self) -> List[NewsItem]:
        """
        从中国新闻网RSS源收集财经新闻

        Returns:
            List[NewsItem]: 收集到的新闻列表
        """
        logger.info("开始从中国新闻网RSS收集财经新闻...")
        all_news = []

        # 使用中国新闻网RSS收集器
        try:
            collector = ChinaNewsRSSCollector()
            
            # 获取配置的最大新闻数量
            news_config = self.config.get("news_collection", {})
            sources = news_config.get("sources", {})
            rss_feeds = sources.get("rss_feeds", [])
            
            max_items = 50  # 默认值
            if rss_feeds and len(rss_feeds) > 0:
                max_items = rss_feeds[0].get("max_items", 50)
            
            # 收集新闻
            raw_news = collector.fetch_news(max_items=max_items)
            
            # 转换为NewsItem格式
            for news_data in raw_news:
                try:
                    news_item = self._convert_to_news_item(news_data)
                    if news_item:
                        all_news.append(news_item)
                        self.stats['collected'] += 1
                except Exception as e:
                    logger.error(f"转换新闻数据失败: {e}")
                    self.stats['errors'] += 1
                    
            logger.info(f"从中国新闻网RSS收集到 {len(all_news)} 条新闻")
            
        except Exception as e:
            logger.error(f"RSS收集失败: {e}")
            self.stats['errors'] += 1

        # 仅去重，不进行关键词过滤
        filtered_news = self._deduplicate_news(all_news)

        # 保存到数据库
        if filtered_news:
            saved_count = db_manager.save_news_items_batch(filtered_news)
            logger.info(
                f"新闻收集完成: 收集 {len(all_news)} 条，去重后 {len(filtered_news)} 条，保存 {saved_count} 条"
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

                    # 生成简单标签（不进行关键字筛选）
                    news_item.keywords = self._generate_simple_tags(
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

        # 腾讯财经API  
        if "tencent_finance" in api_sources and api_sources["tencent_finance"].get("enabled"):
            tencent_news = self._fetch_tencent_news(api_sources["tencent_finance"])
            news_list.extend(tencent_news)

        # 新浪财经API
        if "sina_finance" in api_sources and api_sources["sina_finance"].get("enabled"):
            sina_news = self._fetch_sina_news(api_sources["sina_finance"])
            news_list.extend(sina_news)

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
                    for item in data["data"]["diff"][:20]:  # 限制数量
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

    def _fetch_tencent_news(self, config: Dict) -> List[NewsItem]:
        """
        获取腾讯财经数据（示例实现）

        Args:
            config: 腾讯API配置

        Returns:
            List[NewsItem]: 新闻列表
        """
        news_list = []
        
        try:
            # 腾讯股票接口示例：获取主要指数
            symbols = ["s_sh000001", "s_sz399001", "s_sz399006"]  # 上证指数、深证成指、创业板指
            url = config["base_url"] + ",".join(symbols)
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            lines = response.text.strip().split('\n')
            for line in lines:
                if line.startswith('v_'):
                    try:
                        # 解析腾讯数据格式
                        parts = line.split('=')
                        if len(parts) >= 2:
                            symbol = parts[0].replace('v_', '')
                            data = parts[1].strip('"').split('~')
                            
                            if len(data) > 3:
                                news_item = NewsItem()
                                news_item.title = f"指数动态: {data[1]} 最新价格 {data[3]}"
                                news_item.content = f"当前价格: {data[3]}, 涨跌: {data[31] if len(data) > 31 else 'N/A'}"
                                news_item.source = "腾讯财经API"
                                news_item.category = "指数行情"
                                news_item.publish_time = datetime.now()
                                news_item.url = f"https://gu.qq.com/{symbol}"
                                news_item.keywords = ["指数", "行情"]
                                
                                news_list.append(news_item)
                    except Exception as e:
                        logger.error(f"处理腾讯数据行失败: {e}")
                        continue
                        
            logger.info(f"腾讯财经API获取到 {len(news_list)} 条数据")
            
        except Exception as e:
            logger.error(f"获取腾讯财经数据失败: {e}")
            
        return news_list

    def _fetch_sina_news(self, config: Dict) -> List[NewsItem]:
        """
        获取新浪财经数据（示例实现）

        Args:
            config: 新浪API配置

        Returns:
            List[NewsItem]: 新闻列表
        """
        news_list = []
        
        try:
            # 新浪股票接口示例
            symbols = ["sh000001", "sz399001", "sz399006"]  # 主要指数
            url = config["base_url"] + ",".join(symbols)
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            lines = response.text.strip().split('\n')
            for line in lines:
                if 'hq_str_' in line:
                    try:
                        # 解析新浪数据格式
                        parts = line.split('=')
                        if len(parts) >= 2:
                            symbol = parts[0].split('_')[-1].replace('"', '')
                            data = parts[1].strip('"').split(',')
                            
                            if len(data) > 3:
                                news_item = NewsItem()
                                news_item.title = f"股市快讯: {data[0]} 当前 {data[3]}"
                                news_item.content = f"开盘: {data[1]}, 最高: {data[4]}, 最低: {data[5]}, 当前: {data[3]}"
                                news_item.source = "新浪财经API"
                                news_item.category = "股市行情"
                                news_item.publish_time = datetime.now()
                                news_item.url = f"https://finance.sina.com.cn/realstock/company/{symbol}/nc.shtml"
                                news_item.keywords = ["股市", "行情"]
                                
                                news_list.append(news_item)
                    except Exception as e:
                        logger.error(f"处理新浪数据行失败: {e}")
                        continue
                        
            logger.info(f"新浪财经API获取到 {len(news_list)} 条数据")
            
        except Exception as e:
            logger.error(f"获取新浪财经数据失败: {e}")
            
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

                    # 生成简单标签
                    news_item.keywords = self._generate_simple_tags(
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
        except (ValueError, TypeError, ImportError):
            return datetime.now()

    def _generate_simple_tags(self, title: str, content: str) -> List[str]:
        """
        生成简单标签（不使用关键字筛选）

        Args:
            title: 标题
            content: 内容

        Returns:
            List[str]: 标签列表
        """
        tags = []
        text = f"{title} {content}".lower()

        # 基于常见财经术语生成标签
        common_terms = {
            "股票": ["股票", "股价", "上市", "涨停", "跌停"],
            "指数": ["上证", "深证", "创业板", "科创板", "指数"],
            "基金": ["基金", "ETF", "私募", "公募"],
            "债券": ["债券", "国债", "企业债"],
            "外汇": ["汇率", "美元", "人民币", "外汇"],
            "期货": ["期货", "大宗商品", "原油", "黄金"],
            "银行": ["银行", "存款", "贷款", "利率"],
            "保险": ["保险", "寿险", "财险"],
            "房地产": ["房价", "楼市", "地产", "房产"],
            "科技": ["科技", "互联网", "AI", "芯片"]
        }

        for category, keywords in common_terms.items():
            if any(keyword in text for keyword in keywords):
                tags.append(category)

        return tags[:5]  # 限制标签数量

    def _deduplicate_news(self, news_list: List[NewsItem]) -> List[NewsItem]:
        """
        新闻去重（移除关键字筛选功能）

        Args:
            news_list: 原始新闻列表

        Returns:
            List[NewsItem]: 去重后的新闻列表
        """
        filtered_news = []
        seen_titles = set()

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

    def _convert_to_news_item(self, news_data: Dict) -> Optional[NewsItem]:
        """
        将RSS收集器的数据格式转换为NewsItem

        Args:
            news_data: RSS收集器返回的新闻数据

        Returns:
            NewsItem: 转换后的新闻项，如果转换失败返回None
        """
        try:
            # 解析发布时间
            publish_time = None
            if news_data.get('published_time'):
                try:
                    publish_time = datetime.fromisoformat(
                        news_data['published_time'].replace('Z', '+00:00')
                    )
                except (ValueError, TypeError):
                    logger.warning(f"时间解析失败: {news_data.get('published_time')}")
                    publish_time = datetime.now()
            else:
                publish_time = datetime.now()

            # 转换标签为关键词列表
            keywords = news_data.get('tags', []) if news_data.get('tags') else []

            # 创建NewsItem
            news_item = NewsItem(
                title=news_data.get('title', ''),
                content=news_data.get('content', ''),
                url=news_data.get('url', ''),
                publish_time=publish_time,
                source=news_data.get('source', '中国新闻网'),
                category=news_data.get('category', '财经'),
                keywords=keywords
            )

            return news_item

        except Exception as e:
            logger.error(f"转换新闻数据失败: {e}")
            return None

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
