#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中国新闻网RSS收集器

从中国新闻网RSS订阅源收集财经新闻
RSS源：https://www.chinanews.com.cn/rss/finance.xml
"""

import feedparser
import requests
from datetime import datetime, timezone
from typing import List, Dict, Optional
import logging
from urllib.parse import urljoin
import time
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from src.utils.logger import logger
except ImportError:
    # 如果无法导入项目logger，使用标准logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)


class ChinaNewsRSSCollector:
    """中国新闻网RSS财经新闻收集器"""
    
    def __init__(self):
        self.base_url = "https://www.chinanews.com.cn"
        self.rss_url = "https://www.chinanews.com.cn/rss/finance.xml"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        self.timeout = 30
        
    def fetch_news(self, max_items: int = 50) -> List[Dict]:
        """
        获取财经新闻
        
        Args:
            max_items: 最大获取条数
            
        Returns:
            新闻列表
        """
        try:
            logger.info(f"开始获取中国新闻网财经RSS: {self.rss_url}")
            
            # 获取RSS内容
            response = self.session.get(
                self.rss_url, 
                timeout=self.timeout,
                verify=False  # 有些网站SSL证书可能有问题
            )
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            # 解析RSS
            feed = feedparser.parse(response.content)
            
            if feed.bozo:
                logger.warning(f"RSS解析可能有问题: {feed.bozo_exception}")
            
            news_list = []
            total_entries = len(feed.entries)
            logger.info(f"RSS包含 {total_entries} 条新闻")
            
            for i, entry in enumerate(feed.entries[:max_items]):
                try:
                    news_item = self._parse_entry(entry)
                    if news_item:
                        news_list.append(news_item)
                        
                except Exception as e:
                    logger.error(f"解析第{i+1}条新闻失败: {e}")
                    continue
                    
                # 添加小延时，避免请求过快
                if i > 0 and i % 10 == 0:
                    time.sleep(0.1)
            
            logger.info(f"成功获取 {len(news_list)} 条财经新闻")
            return news_list
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取RSS失败: {e}")
            return []
        except Exception as e:
            logger.error(f"解析RSS失败: {e}")
            return []
    
    def _parse_entry(self, entry) -> Optional[Dict]:
        """
        解析RSS条目
        
        Args:
            entry: RSS条目
            
        Returns:
            新闻数据字典
        """
        try:
            # 标题
            title = entry.get('title', '').strip()
            if not title:
                return None
            
            # 链接
            link = entry.get('link', '').strip()
            if not link:
                return None
            
            # 确保链接是完整的URL
            if link.startswith('/'):
                link = urljoin(self.base_url, link)
            
            # 发布时间
            published_time = self._parse_time(entry)
            
            # 摘要/描述
            summary = entry.get('summary', '') or entry.get('description', '')
            summary = self._clean_html(summary)
            
            # 作者
            author = entry.get('author', '') or entry.get('dc_creator', '')
            
            # 分类
            categories = []
            if hasattr(entry, 'tags'):
                categories = [tag.get('term', '') for tag in entry.tags if tag.get('term')]
            
            # 构建新闻项
            news_item = {
                'title': title,
                'url': link,
                'content': summary,
                'published_time': published_time,
                'source': '中国新闻网',
                'category': '财经',
                'author': author,
                'tags': categories,
                'collected_time': datetime.now(timezone.utc).isoformat(),
                'source_type': 'rss',
                'source_url': self.rss_url
            }
            
            return news_item
            
        except Exception as e:
            logger.error(f"解析RSS条目失败: {e}")
            return None
    
    def _parse_time(self, entry) -> str:
        """
        解析发布时间
        
        Args:
            entry: RSS条目
            
        Returns:
            ISO格式时间字符串
        """
        # 尝试多个时间字段
        time_fields = ['published', 'updated', 'created']
        
        for field in time_fields:
            if hasattr(entry, f'{field}_parsed') and getattr(entry, f'{field}_parsed'):
                try:
                    time_struct = getattr(entry, f'{field}_parsed')
                    dt = datetime(*time_struct[:6], tzinfo=timezone.utc)
                    return dt.isoformat()
                except (ValueError, TypeError):
                    continue
        
        # 如果没有找到有效时间，使用当前时间
        return datetime.now(timezone.utc).isoformat()
    
    def _clean_html(self, text: str) -> str:
        """
        清理HTML标签
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        if not text:
            return ''
        
        import re
        
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 解码HTML实体
        import html
        text = html.unescape(text)
        
        # 清理多余空白字符
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def test_connection(self) -> Dict:
        """
        测试RSS连接
        
        Returns:
            测试结果
        """
        try:
            start_time = time.time()
            
            response = self.session.get(
                self.rss_url,
                timeout=self.timeout,
                verify=False
            )
            response.raise_for_status()
            
            elapsed_time = time.time() - start_time
            
            # 简单解析检查
            feed = feedparser.parse(response.content)
            entry_count = len(feed.entries)
            
            result = {
                'status': 'success',
                'response_time': round(elapsed_time, 2),
                'status_code': response.status_code,
                'entry_count': entry_count,
                'feed_title': feed.feed.get('title', ''),
                'feed_description': feed.feed.get('description', ''),
                'last_updated': feed.feed.get('updated', ''),
                'error': None
            }
            
            logger.info(f"中国新闻网RSS连接测试成功: {entry_count}条新闻")
            return result
            
        except requests.exceptions.Timeout:
            error_msg = f"连接超时 (>{self.timeout}s)"
            logger.error(f"RSS连接测试失败: {error_msg}")
            return {
                'status': 'timeout',
                'response_time': self.timeout,
                'error': error_msg
            }
        except requests.exceptions.RequestException as e:
            error_msg = f"网络错误: {e}"
            logger.error(f"RSS连接测试失败: {error_msg}")
            return {
                'status': 'error',
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"解析错误: {e}"
            logger.error(f"RSS连接测试失败: {error_msg}")
            return {
                'status': 'error',
                'error': error_msg
            }


def main():
    """测试函数"""
    collector = ChinaNewsRSSCollector()
    
    print("🔍 测试中国新闻网财经RSS连接...")
    test_result = collector.test_connection()
    print(f"连接状态: {test_result['status']}")
    print(f"响应时间: {test_result.get('response_time', 'N/A')}s")
    print(f"新闻条数: {test_result.get('entry_count', 'N/A')}")
    
    if test_result['status'] == 'success':
        print("\n📰 获取最新财经新闻...")
        news_list = collector.fetch_news(max_items=5)
        
        for i, news in enumerate(news_list, 1):
            print(f"\n--- 新闻 {i} ---")
            print(f"标题: {news['title']}")
            print(f"来源: {news['source']} - {news['category']}")
            print(f"时间: {news['published_time']}")
            print(f"链接: {news['url']}")
            print(f"摘要: {news['content'][:100]}...")
    else:
        print(f"❌ 连接失败: {test_result.get('error', 'Unknown error')}")


if __name__ == '__main__':
    main() 