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
        importance_score: int = 0,
        importance_reasoning: str = "",
        importance_factors: List[str] = None,
        impact_degree: str = "",  # 新增：影响程度（高/中/低）
    ):
        self.id = id
        self.title = title
        self.content = content
        self.source = source
        self.publish_time = publish_time or datetime.now()
        self.url = url
        self.category = category
        self.keywords = keywords or []
        self.importance_score = importance_score
        self.importance_reasoning = importance_reasoning
        self.importance_factors = importance_factors or []
        self.impact_degree = impact_degree
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
            "importance_score": self.importance_score,
            "importance_reasoning": self.importance_reasoning,
            "importance_factors": json.dumps(self.importance_factors, ensure_ascii=False),
            "impact_degree": self.impact_degree,
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
        
        # 处理重要性分析
        item.importance_score = data.get("importance_score", 0)
        item.importance_reasoning = data.get("importance_reasoning", "")
        
        # 处理重要性因素
        factors_str = data.get("importance_factors", "[]")
        try:
            item.importance_factors = json.loads(factors_str) if factors_str else []
        except (json.JSONDecodeError, TypeError):
            item.importance_factors = []
        
        # 新增：影响程度
        item.impact_degree = data.get("impact_degree", "")

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
                        importance_score INTEGER DEFAULT 0,
                        importance_reasoning TEXT,
                        importance_factors TEXT,
                        impact_degree TEXT,
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
                        impact_score REAL,
                        summary TEXT,
                        analysis_time TEXT,
                        FOREIGN KEY (news_id) REFERENCES news_items (id)
                    )
                """
                )

                # 增量迁移：如缺少impact_degree列则添加
                try:
                    cursor.execute("SELECT impact_degree FROM news_items LIMIT 1")
                except Exception:
                    cursor.execute("ALTER TABLE news_items ADD COLUMN impact_degree TEXT")

                # 索引
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
            news_item: 新闻项

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
                    (id, title, content, source, publish_time, url, category, keywords, 
                     importance_score, importance_reasoning, importance_factors, impact_degree, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        data["importance_score"],
                        data["importance_reasoning"],
                        data["importance_factors"],
                        data["impact_degree"],
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
                            (id, title, content, source, publish_time, url, category, keywords, 
                             importance_score, importance_reasoning, importance_factors, impact_degree, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                                data["importance_score"],
                                data["importance_reasoning"],
                                data["importance_factors"],
                                data["impact_degree"],
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

    def get_news_items_by_date_range(self, start_date: datetime, end_date: datetime) -> List[NewsItem]:
        """
        获取指定日期范围内的新闻
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            List[NewsItem]: 新闻列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    SELECT * FROM news_items 
                    WHERE datetime(publish_time) BETWEEN datetime(?) AND datetime(?)
                    ORDER BY importance_score DESC, publish_time DESC
                    """,
                    (start_date.isoformat(), end_date.isoformat())
                )
                
                rows = cursor.fetchall()
                news_items = []
                
                for row in rows:
                    data = {
                        "id": row[0],
                        "title": row[1],
                        "content": row[2],
                        "source": row[3],
                        "publish_time": row[4],
                        "url": row[5],
                        "category": row[6],
                        "keywords": row[7],
                        "importance_score": row[8] if len(row) > 8 else 0,
                        "importance_reasoning": row[9] if len(row) > 9 else "",
                        "importance_factors": row[10] if len(row) > 10 else "[]",
                        "impact_degree": row[11] if len(row) > 11 else "",
                        "created_at": row[12] if len(row) > 12 else None,
                        "updated_at": row[13] if len(row) > 13 else None,
                    }
                    news_items.append(NewsItem.from_dict(data))
                
                return news_items
                
        except Exception as e:
            logger.error(f"获取日期范围内新闻失败: {e}")
            return []
    
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

    def cleanup_old_data(self, days: int = 7) -> Dict[str, int]:
        """
        清理旧数据
        
        Args:
            days: 保留天数，默认7天
            
        Returns:
            Dict[str, int]: 清理统计信息
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_str = cutoff_date.isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 统计要删除的数据
                cursor.execute(
                    "SELECT COUNT(*) FROM news_items WHERE created_at < ?",
                    (cutoff_str,)
                )
                old_news_count = cursor.fetchone()[0]
                
                # 删除旧新闻
                cursor.execute(
                    "DELETE FROM news_items WHERE created_at < ?",
                    (cutoff_str,)
                )
                
                # 删除孤立的分析结果（如果存在analysis_results表）
                cursor.execute(
                    """DELETE FROM analysis_results 
                       WHERE news_id NOT IN (SELECT id FROM news_items)"""
                )
                old_analysis_count = cursor.rowcount
                
                conn.commit()
                
                logger.info(f"数据清理完成：删除 {old_news_count} 条新闻，{old_analysis_count} 条分析结果")
                
                return {
                    "deleted_news": old_news_count,
                    "deleted_analysis": old_analysis_count,
                    "cutoff_date": cutoff_str
                }
                
        except Exception as e:
            logger.error(f"数据清理失败: {e}")
            return {"deleted_news": 0, "deleted_analysis": 0, "error": str(e)}

    def optimize_database(self) -> Dict[str, Any]:
        """
        优化数据库性能
        
        Returns:
            Dict[str, Any]: 优化结果
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 获取优化前的数据库大小
                cursor.execute("PRAGMA page_count")
                page_count_before = cursor.fetchone()[0]
                
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                size_before = page_count_before * page_size
                
                # 执行VACUUM来压缩数据库
                cursor.execute("VACUUM")
                
                # 重建统计信息
                cursor.execute("ANALYZE")
                
                # 获取优化后的数据库大小
                cursor.execute("PRAGMA page_count")
                page_count_after = cursor.fetchone()[0]
                size_after = page_count_after * page_size
                
                saved_bytes = size_before - size_after
                
                logger.info(f"数据库优化完成：节省 {saved_bytes} 字节")
                
                return {
                    "size_before": size_before,
                    "size_after": size_after,
                    "saved_bytes": saved_bytes,
                    "optimization_ratio": saved_bytes / size_before if size_before > 0 else 0
                }
                
        except Exception as e:
            logger.error(f"数据库优化失败: {e}")
            return {"error": str(e)}


# 全局数据库实例
db_manager = DatabaseManager()
