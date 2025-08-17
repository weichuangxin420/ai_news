"""
数据库操作模块
提供SQLite数据库的CRUD操作
"""

import json
import os
import sqlite3
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .logger import get_logger

logger = get_logger("database")


class NewsItem:
    """新闻数据模型"""

    def __init__(
        self,
        id: str = None,
        title: str = "",
        content: str = "",
        source: str = "",
        publish_time: datetime = None,
        url: str = "",
        category: str = "",
        keywords: List[str] = None,
    ):
        self.id = id
        self.title = title
        self.content = content
        self.source = source
        self.publish_time = publish_time or datetime.now()
        self.url = url
        self.category = category
        self.keywords = keywords or []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "publish_time": (
                self.publish_time.isoformat() if self.publish_time else None
            ),
            "url": self.url,
            "category": self.category,
            "keywords": json.dumps(self.keywords, ensure_ascii=False),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NewsItem":
        """从字典创建NewsItem对象"""
        item = cls()
        item.id = data.get("id")
        item.title = data.get("title", "")
        item.content = data.get("content", "")
        item.source = data.get("source", "")

        # 处理时间字段
        if data.get("publish_time"):
            item.publish_time = datetime.fromisoformat(data["publish_time"])
        if data.get("created_at"):
            item.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            item.updated_at = datetime.fromisoformat(data["updated_at"])

        item.url = data.get("url", "")
        item.category = data.get("category", "")

        # 处理关键词
        keywords_str = data.get("keywords", "[]")
        try:
            item.keywords = json.loads(keywords_str) if keywords_str else []
        except (json.JSONDecodeError, TypeError):
            item.keywords = []

        return item


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_path: str = "data/news.db"):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_database()

    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"创建数据库目录: {db_dir}")

    def _init_database(self):
        """初始化数据库表结构"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 创建新闻表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS news_items (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        content TEXT,
                        source TEXT,
                        publish_time TEXT,
                        url TEXT,
                        category TEXT,
                        keywords TEXT,
                        created_at TEXT,
                        updated_at TEXT
                    )
                """
                )

                # 创建分析结果表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS analysis_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        news_id TEXT,
                        affected_sectors TEXT,
                        impact_score REAL,
                        impact_level TEXT,
                        sentiment TEXT,
                        summary TEXT,
                        recommendation TEXT,
                        analysis_time TEXT,
                        FOREIGN KEY (news_id) REFERENCES news_items (id)
                    )
                """
                )

                # 创建索引
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_news_publish_time ON news_items(publish_time)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_news_source ON news_items(source)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_news_category ON news_items(category)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_analysis_news_id ON analysis_results(news_id)"
                )

                conn.commit()
                logger.info("数据库初始化完成")

        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise

    def save_news_item(self, news_item: NewsItem) -> bool:
        """
        保存新闻项

        Args:
            news_item: 新闻项对象

        Returns:
            bool: 保存是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 生成ID（如果没有）
                if not news_item.id:
                    news_item.id = f"{news_item.source}_{hash(news_item.title + news_item.url)}_{int(datetime.now().timestamp())}"

                news_item.updated_at = datetime.now()
                data = news_item.to_dict()

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO news_items 
                    (id, title, content, source, publish_time, url, category, keywords, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        data["id"],
                        data["title"],
                        data["content"],
                        data["source"],
                        data["publish_time"],
                        data["url"],
                        data["category"],
                        data["keywords"],
                        data["created_at"],
                        data["updated_at"],
                    ),
                )

                conn.commit()
                logger.debug(f"保存新闻: {news_item.title[:50]}...")
                return True

        except Exception as e:
            logger.error(f"保存新闻失败: {e}")
            return False

    def save_news_items_batch(self, news_items: List[NewsItem]) -> int:
        """
        批量保存新闻项

        Args:
            news_items: 新闻项列表

        Returns:
            int: 成功保存的数量
        """
        success_count = 0

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                for news_item in news_items:
                    try:
                        # 生成ID（如果没有）
                        if not news_item.id:
                            news_item.id = f"{news_item.source}_{hash(news_item.title + news_item.url)}_{int(datetime.now().timestamp())}"

                        news_item.updated_at = datetime.now()
                        data = news_item.to_dict()

                        cursor.execute(
                            """
                            INSERT OR REPLACE INTO news_items 
                            (id, title, content, source, publish_time, url, category, keywords, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                data["id"],
                                data["title"],
                                data["content"],
                                data["source"],
                                data["publish_time"],
                                data["url"],
                                data["category"],
                                data["keywords"],
                                data["created_at"],
                                data["updated_at"],
                            ),
                        )

                        success_count += 1

                    except Exception as e:
                        logger.error(f"保存单个新闻失败: {e}")
                        continue

                conn.commit()
                logger.info(f"批量保存新闻完成: {success_count}/{len(news_items)}")

        except Exception as e:
            logger.error(f"批量保存新闻失败: {e}")

        return success_count

    def get_news_items(
        self,
        limit: int = 100,
        offset: int = 0,
        source: str = None,
        category: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
    ) -> List[NewsItem]:
        """
        获取新闻项列表

        Args:
            limit: 限制数量
            offset: 偏移量
            source: 新闻源过滤
            category: 分类过滤
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            List[NewsItem]: 新闻项列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 构建查询条件
                conditions = []
                params = []

                if source:
                    conditions.append("source = ?")
                    params.append(source)

                if category:
                    conditions.append("category = ?")
                    params.append(category)

                if start_time:
                    conditions.append("publish_time >= ?")
                    params.append(start_time.isoformat())

                if end_time:
                    conditions.append("publish_time <= ?")
                    params.append(end_time.isoformat())

                where_clause = (
                    " WHERE " + " AND ".join(conditions) if conditions else ""
                )

                query = f"""
                    SELECT * FROM news_items
                    {where_clause}
                    ORDER BY publish_time DESC
                    LIMIT ? OFFSET ?
                """

                params.extend([limit, offset])
                cursor.execute(query, params)

                results = []
                for row in cursor.fetchall():
                    # 将行数据转换为字典
                    columns = [description[0] for description in cursor.description]
                    row_dict = dict(zip(columns, row))
                    results.append(NewsItem.from_dict(row_dict))

                return results

        except Exception as e:
            logger.error(f"获取新闻列表失败: {e}")
            return []

    def get_news_item_by_id(self, news_id: str) -> Optional[NewsItem]:
        """
        根据ID获取新闻项

        Args:
            news_id: 新闻ID

        Returns:
            Optional[NewsItem]: 新闻项或None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM news_items WHERE id = ?", (news_id,))
                row = cursor.fetchone()

                if row:
                    columns = [description[0] for description in cursor.description]
                    row_dict = dict(zip(columns, row))
                    return NewsItem.from_dict(row_dict)

                return None

        except Exception as e:
            logger.error(f"获取新闻项失败: {e}")
            return None

    def delete_old_news(self, days: int = 30) -> int:
        """
        删除过期新闻

        Args:
            days: 保留天数

        Returns:
            int: 删除的记录数
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 删除分析结果
                cursor.execute(
                    """
                    DELETE FROM analysis_results 
                    WHERE news_id IN (
                        SELECT id FROM news_items 
                        WHERE publish_time < ?
                    )
                """,
                    (cutoff_date.isoformat(),),
                )

                # 删除新闻项
                cursor.execute(
                    """
                    DELETE FROM news_items 
                    WHERE publish_time < ?
                """,
                    (cutoff_date.isoformat(),),
                )

                deleted_count = cursor.rowcount
                conn.commit()

                logger.info(f"删除过期新闻: {deleted_count} 条")
                return deleted_count

        except Exception as e:
            logger.error(f"删除过期新闻失败: {e}")
            return 0

    def check_news_exists(self, title: str, url: str = None) -> bool:
        """
        检查新闻是否已存在（去重）

        Args:
            title: 新闻标题
            url: 新闻URL（可选）

        Returns:
            bool: 是否存在
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if url:
                    cursor.execute(
                        "SELECT 1 FROM news_items WHERE title = ? OR url = ?",
                        (title, url),
                    )
                else:
                    cursor.execute("SELECT 1 FROM news_items WHERE title = ?", (title,))

                return cursor.fetchone() is not None

        except Exception as e:
            logger.error(f"检查新闻存在性失败: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        获取数据库统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 总新闻数
                cursor.execute("SELECT COUNT(*) FROM news_items")
                total_news = cursor.fetchone()[0]

                # 今日新闻数
                today = datetime.now().date()
                cursor.execute(
                    "SELECT COUNT(*) FROM news_items WHERE date(publish_time) = ?",
                    (today.isoformat(),),
                )
                today_news = cursor.fetchone()[0]

                # 按来源统计
                cursor.execute(
                    """
                    SELECT source, COUNT(*) as count 
                    FROM news_items 
                    GROUP BY source 
                    ORDER BY count DESC
                """
                )
                source_stats = dict(cursor.fetchall())

                # 按分类统计
                cursor.execute(
                    """
                    SELECT category, COUNT(*) as count 
                    FROM news_items 
                    GROUP BY category 
                    ORDER BY count DESC
                """
                )
                category_stats = dict(cursor.fetchall())

                return {
                    "total_news": total_news,
                    "today_news": today_news,
                    "source_stats": source_stats,
                    "category_stats": category_stats,
                    "last_updated": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}


# 全局数据库实例
db_manager = DatabaseManager()
