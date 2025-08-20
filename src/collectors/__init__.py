"""
新闻收集模块

包含各种新闻源的收集器实现：
- RSS订阅源收集器
- API接口收集器
- 网页爬虫收集器
"""

from .chinanews_rss import ChinaNewsRSSCollector
from .news_collector import NewsCollector

__all__ = [
    'ChinaNewsRSSCollector',
    'NewsCollector'
] 