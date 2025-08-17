"""
AI分析模块
使用DeepSeek AI分析新闻对A股板块的影响
"""

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import openai
import yaml
from openai import OpenAI

from .utils.database import NewsItem, db_manager
from .utils.logger import get_logger

logger = get_logger("ai_analyzer")


@dataclass
class AnalysisResult:
    """分析结果数据模型"""

    news_id: str
    affected_sectors: List[str]
    impact_score: float  # -10到10，负数表示负面影响
    impact_level: str  # 高/中/低
    sentiment: str  # 正面/负面/中性
    summary: str
    recommendation: str
    analysis_time: datetime

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "news_id": self.news_id,
            "affected_sectors": json.dumps(self.affected_sectors, ensure_ascii=False),
            "impact_score": self.impact_score,
            "impact_level": self.impact_level,
            "sentiment": self.sentiment,
            "summary": self.summary,
            "recommendation": self.recommendation,
            "analysis_time": self.analysis_time.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisResult":
        """从字典创建AnalysisResult对象"""
        affected_sectors = json.loads(data.get("affected_sectors", "[]"))
        analysis_time = (
            datetime.fromisoformat(data["analysis_time"])
            if data.get("analysis_time")
            else datetime.now()
        )

        return cls(
            news_id=data["news_id"],
            affected_sectors=affected_sectors,
            impact_score=data["impact_score"],
            impact_level=data["impact_level"],
            sentiment=data["sentiment"],
            summary=data["summary"],
            recommendation=data["recommendation"],
            analysis_time=analysis_time,
        )


class AIAnalyzer:
    """AI新闻分析器"""

    def __init__(self, config_path: str = None):
        """
        初始化AI分析器

        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self._setup_client()

        # 统计信息
        self.stats = {"analyzed": 0, "errors": 0, "api_calls": 0, "total_tokens": 0}

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

    def _setup_client(self):
        """设置OpenAI客户端（兼容DeepSeek API）"""
        ai_config = self.config.get("ai_analysis", {}).get("deepseek", {})

        # 从环境变量或配置文件获取API密钥
        api_key = os.getenv("DEEPSEEK_API_KEY") or ai_config.get("api_key", "")
        if api_key.startswith("${") and api_key.endswith("}"):
            # 处理环境变量引用
            env_var = api_key[2:-1]
            api_key = os.getenv(env_var, "")

        if not api_key:
            logger.warning("未找到DeepSeek API密钥，将使用模拟模式")
            self.client = None
            return

        try:
            self.client = OpenAI(
                api_key=api_key,
                base_url=ai_config.get("base_url", "https://api.deepseek.com/v1"),
            )
            logger.info("DeepSeek API客户端初始化成功")
        except Exception as e:
            logger.error(f"DeepSeek API客户端初始化失败: {e}")
            self.client = None

    def analyze_news(self, news_item: NewsItem) -> AnalysisResult:
        """
        分析单条新闻

        Args:
            news_item: 新闻项

        Returns:
            AnalysisResult: 分析结果
        """
        try:
            if not self.client:
                return self._mock_analysis(news_item)

            # 构建提示词
            prompt = self._build_analysis_prompt(news_item)

            # 调用DeepSeek API
            response = self._call_deepseek_api(prompt)

            # 解析响应
            result = self._parse_analysis_response(news_item.id, response)

            self.stats["analyzed"] += 1
            logger.debug(f"新闻分析完成: {news_item.title[:50]}...")

            return result

        except Exception as e:
            logger.error(f"新闻分析失败: {e}")
            self.stats["errors"] += 1
            return self._error_fallback_analysis(news_item)

    def batch_analyze(self, news_list: List[NewsItem]) -> List[AnalysisResult]:
        """
        批量分析新闻

        Args:
            news_list: 新闻列表

        Returns:
            List[AnalysisResult]: 分析结果列表
        """
        results = []
        batch_size = (
            self.config.get("ai_analysis", {})
            .get("analysis_params", {})
            .get("batch_size", 10)
        )

        logger.info(f"开始批量分析 {len(news_list)} 条新闻，批量大小: {batch_size}")

        for i in range(0, len(news_list), batch_size):
            batch = news_list[i : i + batch_size]

            for news_item in batch:
                try:
                    result = self.analyze_news(news_item)
                    results.append(result)

                    # 保存分析结果到数据库
                    self._save_analysis_result(result)

                    # 避免API限流
                    time.sleep(0.1)

                except Exception as e:
                    logger.error(f"批量分析中单项失败: {e}")
                    continue

            # 批次间暂停
            if i + batch_size < len(news_list):
                time.sleep(1)

        logger.info(
            f"批量分析完成: 成功 {len(results)} 条，失败 {len(news_list) - len(results)} 条"
        )
        return results

    def _build_analysis_prompt(self, news_item: NewsItem) -> str:
        """
        构建分析提示词

        Args:
            news_item: 新闻项

        Returns:
            str: 提示词
        """
        prompt = f"""
请你作为一位专业的A股市场分析师，对以下新闻进行深度分析，重点关注其对A股各板块的影响。

新闻信息：
标题：{news_item.title}
内容：{news_item.content}
来源：{news_item.source}
发布时间：{news_item.publish_time}
关键词：{', '.join(news_item.keywords)}

请按照以下JSON格式输出分析结果：
{{
    "affected_sectors": ["受影响的板块1", "受影响的板块2"],
    "impact_score": 数值(-10到10，负数表示负面影响),
    "impact_level": "影响级别(高/中/低)",
    "sentiment": "情感倾向(正面/负面/中性)",
    "summary": "新闻影响摘要(100字以内)",
    "recommendation": "投资建议(150字以内)"
}}

分析要求：
1. 影响评分范围：-10（极度负面）到 +10（极度正面），0为中性
2. 影响级别：高（绝对值>7）、中（绝对值3-7）、低（绝对值<3）
3. 受影响板块包括但不限于：科技、金融、医药、消费、地产、新能源、军工、农业、有色金属、钢铁、化工、建筑建材等
4. 情感分析要准确判断新闻对市场的情绪影响
5. 投资建议要具体、可操作，避免模糊表述

请确保输出严格按照JSON格式，不要包含其他文本。
"""
        return prompt.strip()

    def _call_deepseek_api(self, prompt: str) -> str:
        """
        调用DeepSeek API

        Args:
            prompt: 提示词

        Returns:
            str: API响应内容
        """
        ai_config = self.config.get("ai_analysis", {}).get("deepseek", {})
        analysis_params = self.config.get("ai_analysis", {}).get("analysis_params", {})

        try:
            response = self.client.chat.completions.create(
                model=ai_config.get("model", "deepseek-chat"),
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位专业的A股市场分析师，具有丰富的股票投资经验和深厚的市场洞察力。请严格按照要求的JSON格式输出分析结果。",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=ai_config.get("max_tokens", 2000),
                temperature=ai_config.get("temperature", 0.1),
                timeout=analysis_params.get("timeout", 30),
            )

            self.stats["api_calls"] += 1
            if hasattr(response, "usage") and response.usage:
                self.stats["total_tokens"] += response.usage.total_tokens

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"DeepSeek API调用失败: {e}")
            raise

    def _parse_analysis_response(self, news_id: str, response: str) -> AnalysisResult:
        """
        解析API响应

        Args:
            news_id: 新闻ID
            response: API响应内容

        Returns:
            AnalysisResult: 解析后的分析结果
        """
        try:
            # 尝试提取JSON部分
            response = response.strip()

            # 查找JSON开始和结束位置
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("响应中未找到有效的JSON格式")

            json_str = response[start_idx:end_idx]
            data = json.loads(json_str)

            # 验证和规范化数据
            affected_sectors = data.get("affected_sectors", [])
            if isinstance(affected_sectors, str):
                affected_sectors = [affected_sectors]

            impact_score = float(data.get("impact_score", 0))
            impact_score = max(-10, min(10, impact_score))  # 限制范围

            impact_level = data.get("impact_level", "低")
            if impact_level not in ["高", "中", "低"]:
                impact_level = "低"

            sentiment = data.get("sentiment", "中性")
            if sentiment not in ["正面", "负面", "中性"]:
                sentiment = "中性"

            return AnalysisResult(
                news_id=news_id,
                affected_sectors=affected_sectors,
                impact_score=impact_score,
                impact_level=impact_level,
                sentiment=sentiment,
                summary=data.get("summary", ""),
                recommendation=data.get("recommendation", ""),
                analysis_time=datetime.now(),
            )

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"解析API响应失败: {e}, 响应内容: {response[:200]}...")
            return self._create_fallback_result(news_id, response)

    def _create_fallback_result(self, news_id: str, response: str) -> AnalysisResult:
        """
        创建后备分析结果

        Args:
            news_id: 新闻ID
            response: 原始响应

        Returns:
            AnalysisResult: 后备分析结果
        """
        return AnalysisResult(
            news_id=news_id,
            affected_sectors=["综合"],
            impact_score=0,
            impact_level="低",
            sentiment="中性",
            summary="AI解析失败，使用默认分析结果",
            recommendation="建议人工进一步分析",
            analysis_time=datetime.now(),
        )

    def _mock_analysis(self, news_item: NewsItem) -> AnalysisResult:
        """
        模拟分析（当API不可用时）

        Args:
            news_item: 新闻项

        Returns:
            AnalysisResult: 模拟的分析结果
        """
        # 基于关键词的简单规则分析
        title_content = f"{news_item.title} {news_item.content}".lower()

        # 板块映射
        sector_keywords = {
            "科技": ["ai", "人工智能", "芯片", "半导体", "互联网", "云计算", "大数据"],
            "金融": ["银行", "保险", "证券", "基金", "金融", "贷款"],
            "医药": ["医药", "生物", "疫苗", "医疗", "健康", "制药"],
            "新能源": ["新能源", "锂电池", "光伏", "风电", "电动车", "充电桩"],
            "消费": ["消费", "零售", "电商", "食品", "饮料", "服装"],
            "地产": ["房地产", "建筑", "地产", "楼市", "住房"],
        }

        affected_sectors = []
        for sector, keywords in sector_keywords.items():
            if any(keyword in title_content for keyword in keywords):
                affected_sectors.append(sector)

        if not affected_sectors:
            affected_sectors = ["综合"]

        # 简单情感分析
        positive_words = ["上涨", "增长", "利好", "突破", "创新", "成功", "盈利"]
        negative_words = ["下跌", "亏损", "风险", "危机", "失败", "暴跌", "问题"]

        positive_score = sum(1 for word in positive_words if word in title_content)
        negative_score = sum(1 for word in negative_words if word in title_content)

        if positive_score > negative_score:
            sentiment = "正面"
            impact_score = min(positive_score * 2, 5)
        elif negative_score > positive_score:
            sentiment = "负面"
            impact_score = -min(negative_score * 2, 5)
        else:
            sentiment = "中性"
            impact_score = 0

        impact_level = (
            "高" if abs(impact_score) > 3 else "中" if abs(impact_score) > 1 else "低"
        )

        return AnalysisResult(
            news_id=news_item.id,
            affected_sectors=affected_sectors,
            impact_score=impact_score,
            impact_level=impact_level,
            sentiment=sentiment,
            summary=f"基于关键词分析，新闻对{', '.join(affected_sectors)}板块有{impact_level}度{sentiment}影响",
            recommendation="建议关注相关板块动态，谨慎投资决策",
            analysis_time=datetime.now(),
        )

    def _error_fallback_analysis(self, news_item: NewsItem) -> AnalysisResult:
        """
        错误时的后备分析

        Args:
            news_item: 新闻项

        Returns:
            AnalysisResult: 后备分析结果
        """
        return AnalysisResult(
            news_id=news_item.id,
            affected_sectors=["未知"],
            impact_score=0,
            impact_level="低",
            sentiment="中性",
            summary="分析过程中出现错误，无法生成有效分析",
            recommendation="建议人工分析或稍后重试",
            analysis_time=datetime.now(),
        )

    def _save_analysis_result(self, result: AnalysisResult) -> bool:
        """
        保存分析结果到数据库

        Args:
            result: 分析结果

        Returns:
            bool: 保存是否成功
        """
        try:
            import sqlite3

            db_path = (
                self.config.get("database", {})
                .get("sqlite", {})
                .get("db_path", "data/news.db")
            )

            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()

                data = result.to_dict()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO analysis_results 
                    (news_id, affected_sectors, impact_score, impact_level, sentiment, 
                     summary, recommendation, analysis_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        data["news_id"],
                        data["affected_sectors"],
                        data["impact_score"],
                        data["impact_level"],
                        data["sentiment"],
                        data["summary"],
                        data["recommendation"],
                        data["analysis_time"],
                    ),
                )

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"保存分析结果失败: {e}")
            return False

    def format_analysis_report(self, results: List[AnalysisResult]) -> str:
        """
        格式化分析报告

        Args:
            results: 分析结果列表

        Returns:
            str: 格式化的报告
        """
        if not results:
            return "暂无分析结果"

        report = f"""
# A股新闻影响分析报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**分析新闻数量**: {len(results)}

## 整体概况

"""

        # 统计信息
        positive_count = sum(1 for r in results if r.sentiment == "正面")
        negative_count = sum(1 for r in results if r.sentiment == "负面")
        neutral_count = sum(1 for r in results if r.sentiment == "中性")

        report += f"""
- **正面新闻**: {positive_count} 条
- **负面新闻**: {negative_count} 条  
- **中性新闻**: {neutral_count} 条

"""

        # 板块影响统计
        sector_impact = {}
        for result in results:
            for sector in result.affected_sectors:
                if sector not in sector_impact:
                    sector_impact[sector] = {"count": 0, "total_score": 0}
                sector_impact[sector]["count"] += 1
                sector_impact[sector]["total_score"] += result.impact_score

        if sector_impact:
            report += "## 板块影响排名\n\n"
            sorted_sectors = sorted(
                sector_impact.items(),
                key=lambda x: abs(x[1]["total_score"]),
                reverse=True,
            )

            for sector, data in sorted_sectors[:10]:
                avg_score = data["total_score"] / data["count"]
                report += (
                    f"- **{sector}**: {data['count']}条新闻，平均影响{avg_score:.1f}\n"
                )

        # 重要分析结果
        high_impact_results = [r for r in results if r.impact_level == "高"]
        if high_impact_results:
            report += f"\n## 高影响新闻分析 ({len(high_impact_results)}条)\n\n"

            for i, result in enumerate(high_impact_results[:5], 1):
                report += f"""
### {i}. 影响评分: {result.impact_score:.1f} | {result.sentiment}

**影响板块**: {', '.join(result.affected_sectors)}

**分析摘要**: {result.summary}

**投资建议**: {result.recommendation}

---

"""

        return report

    def get_stats(self) -> Dict[str, Any]:
        """
        获取分析器统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            **self.stats,
            "last_analysis_time": datetime.now().isoformat(),
            "api_available": self.client is not None,
        }


def analyze_latest_news(limit: int = 20) -> List[AnalysisResult]:
    """
    便捷函数：分析最新新闻

    Args:
        limit: 分析的新闻数量限制

    Returns:
        List[AnalysisResult]: 分析结果列表
    """
    analyzer = AIAnalyzer()
    news_list = db_manager.get_news_items(limit=limit)

    if not news_list:
        logger.info("没有找到待分析的新闻")
        return []

    return analyzer.batch_analyze(news_list)


if __name__ == "__main__":
    # 测试分析功能
    results = analyze_latest_news(5)
    print(f"分析了 {len(results)} 条新闻")

    if results:
        analyzer = AIAnalyzer()
        report = analyzer.format_analysis_report(results)
        print(report)
