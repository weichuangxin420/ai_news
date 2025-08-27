#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻深度分析器
针对高重要性新闻（>70分）进行深度分析，包括：
1. 百度搜索获取背景信息
2. 深度分析报告生成
3. 重要性分数重新评估
"""

import json
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Union, Tuple
import re

from openai import OpenAI
import yaml

import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from src.utils.database import NewsItem
    from src.utils.logger import get_logger
    from src.ai.ai_tools.baidu_search import baidu_search_tool
except ImportError:
    # 如果无法导入项目模块，使用相对导入
    from ..utils.database import NewsItem
    from ..utils.logger import get_logger
    from ..ai_tools.baidu_search import baidu_search_tool

logger = get_logger("deep_analyzer")


@dataclass
class DeepAnalysisResult:
    """深度分析结果"""
    news_id: str
    title: str
    original_score: int           # 原始重要性分数
    search_keywords: List[str]    # 搜索关键词
    search_results_summary: str   # 搜索结果摘要
    deep_analysis_report: str     # 200字深度分析报告
    adjusted_score: int           # 调整后的重要性分数
    analysis_time: str
    search_success: bool          # 搜索是否成功
    model_used: str              # 使用的AI模型


class DeepAnalyzer:
    """新闻深度分析器"""
    
    def __init__(self, config: Dict = None):
        """
        初始化深度分析器
        
        Args:
            config: 配置字典
        """
        self.config = config or self._load_config()
        self.client = None
        self._init_client()
        
        # 深度分析配置
        self.deep_config = self.config.get("ai_analysis", {}).get("deep_analysis", {})
        self.enabled = self.deep_config.get("enabled", True)
        self.score_threshold = self.deep_config.get("score_threshold", 70)
        self.max_concurrent = self.deep_config.get("max_concurrent", 3)
        self.search_timeout = self.deep_config.get("search_timeout", 30)
        self.max_keywords = self.deep_config.get("max_search_keywords", 5)
        self.report_max_length = self.deep_config.get("report_max_length", 200)
        self.enable_score_adjustment = self.deep_config.get("enable_score_adjustment", True)
        self.search_retry_count = self.deep_config.get("search_retry_count", 2)
        
    def _load_config(self) -> Dict:
        """加载配置文件"""
        config_path = os.path.join(
            os.path.dirname(__file__), "../../config/config.yaml"
        )
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def _init_client(self):
        """初始化OpenRouter客户端"""
        try:
            openrouter_config = self.config.get("ai_analysis", {}).get("openrouter", {})
            
            if not openrouter_config.get("api_key"):
                logger.warning("未配置OpenRouter API密钥，深度分析将使用模拟模式")
                self.client = None
                return
            
            self.client = OpenAI(
                api_key=openrouter_config.get("api_key"),
                base_url=openrouter_config.get("base_url", "https://openrouter.ai/api/v1")
            )
            
            logger.info("OpenRouter深度分析API客户端初始化成功")
            
        except Exception as e:
            logger.error(f"初始化OpenRouter客户端失败: {e}")
            self.client = None
    
    def should_analyze(self, news_item: NewsItem) -> bool:
        """
        判断是否需要进行深度分析
        
        Args:
            news_item: 新闻项
            
        Returns:
            bool: 是否需要深度分析
        """
        if not self.enabled:
            return False
            
        if not hasattr(news_item, 'importance_score') or news_item.importance_score is None:
            return False
            
        return news_item.importance_score >= self.score_threshold
    
    def analyze_news_deep(self, news_item: NewsItem) -> DeepAnalysisResult:
        """
        对单条新闻进行深度分析
        
        Args:
            news_item: 新闻项
            
        Returns:
            DeepAnalysisResult: 深度分析结果
        """
        if not self.should_analyze(news_item):
            logger.debug(f"新闻不满足深度分析条件: {news_item.title}")
            return self._create_skip_result(news_item)
        
        try:
            logger.info(f"开始深度分析: {news_item.title[:50]}...")
            
            # 1. 提取搜索关键词
            keywords = self._extract_search_keywords(news_item)
            
            # 2. 执行百度搜索
            search_results, search_success = self._perform_search(keywords, news_item.title)
            
            # 3. 生成深度分析报告
            deep_report = self._generate_deep_analysis(news_item, search_results, keywords)
            
            # 4. 重新评估重要性分数
            adjusted_score = self._adjust_importance_score(
                news_item, deep_report, search_results
            ) if self.enable_score_adjustment else news_item.importance_score
            
            result = DeepAnalysisResult(
                news_id=news_item.id or f"deep_{int(time.time())}",
                title=news_item.title,
                original_score=news_item.importance_score,
                search_keywords=keywords,
                search_results_summary=search_results,
                deep_analysis_report=deep_report,
                adjusted_score=adjusted_score,
                analysis_time=datetime.now().isoformat(),
                search_success=search_success,
                model_used=self.config.get("ai_analysis", {}).get("openrouter", {}).get("model", "deepseek/deepseek-r1-0528:free")
            )
            
            logger.info(f"深度分析完成: {news_item.title[:50]}... -> {adjusted_score}分 (原{news_item.importance_score}分)")
            logger.info("深度分析报告全文:")
            logger.info(deep_report)
            return result
            
        except Exception as e:
            logger.error(f"深度分析失败: {e}")
            return self._create_error_result(news_item, str(e))
    
    def batch_analyze_deep(self, news_list: List[NewsItem]) -> List[DeepAnalysisResult]:
        """
        批量深度分析新闻
        
        Args:
            news_list: 新闻列表
            
        Returns:
            List[DeepAnalysisResult]: 深度分析结果列表
        """
        # 筛选需要深度分析的新闻
        high_importance_news = [news for news in news_list if self.should_analyze(news)]
        
        if not high_importance_news:
            logger.info("没有新闻需要深度分析")
            return []
        
        logger.info(f"开始批量深度分析，共 {len(high_importance_news)} 条高重要性新闻")
        
        results = []
        
        # 使用线程池进行并发分析
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            # 提交所有任务
            future_to_news = {
                executor.submit(self.analyze_news_deep, news): news
                for news in high_importance_news
            }
            
            # 收集结果
            for future in as_completed(future_to_news):
                news = future_to_news[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.debug(f"深度分析完成: {news.title[:30]}...")
                except Exception as e:
                    logger.error(f"深度分析任务失败: {news.title[:30]}... - {e}")
                    # 添加错误结果
                    error_result = self._create_error_result(news, str(e))
                    results.append(error_result)
        
        # 按原始顺序排序
        results.sort(key=lambda x: x.original_score, reverse=True)
        
        logger.info(f"批量深度分析完成，共处理 {len(results)} 条新闻")
        return results
    
    def _extract_search_keywords(self, news_item: NewsItem) -> List[str]:
        """
        从新闻中提取搜索关键词
        
        Args:
            news_item: 新闻项
            
        Returns:
            List[str]: 搜索关键词列表
        """
        try:
            # 使用简单的关键词提取策略
            title = news_item.title
            content = news_item.content
            
            keywords = []
            
            # 从标题中提取关键词
            title_keywords = self._extract_keywords_from_text(title)
            keywords.extend(title_keywords[:3])  # 取前3个
            
            # 从内容中提取关键词
            if content and len(keywords) < self.max_keywords:
                content_keywords = self._extract_keywords_from_text(content)
                remaining_slots = self.max_keywords - len(keywords)
                keywords.extend(content_keywords[:remaining_slots])
            
            # 如果关键词不足，使用标题作为搜索词
            if not keywords:
                keywords = [title[:20]]  # 使用标题前20字符
            
            logger.debug(f"提取搜索关键词: {keywords}")
            return keywords[:self.max_keywords]
            
        except Exception as e:
            logger.error(f"提取搜索关键词失败: {e}")
            return [news_item.title[:20]]  # 降级方案
    
    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """
        从文本中提取关键词
        
        Args:
            text: 输入文本
            
        Returns:
            List[str]: 关键词列表
        """
        if not text:
            return []
        
        # 简单的关键词提取：查找常见的财经关键词
        financial_keywords = [
            "股票", "股市", "上市", "IPO", "融资", "投资", "基金", "证券",
            "银行", "保险", "地产", "科技", "医药", "能源", "汽车", "消费",
            "制造", "金融", "互联网", "人工智能", "新能源", "半导体",
            "涨停", "跌停", "涨幅", "跌幅", "成交", "市值", "业绩", "财报"
        ]
        
        # 查找匹配的关键词
        found_keywords = []
        for keyword in financial_keywords:
            if keyword in text and keyword not in found_keywords:
                found_keywords.append(keyword)
                if len(found_keywords) >= 5:  # 最多提取5个
                    break
        
        # 如果没有找到财经关键词，提取其他关键词
        if not found_keywords:
            # 简单分词：提取3-8字符的词组
            import re
            words = re.findall(r'[\u4e00-\u9fff]{3,8}', text)
            found_keywords = list(set(words))[:3]
        
        return found_keywords
    
    def _perform_search(self, keywords: List[str], title: str) -> Tuple[str, bool]:
        """
        执行百度搜索
        
        Args:
            keywords: 搜索关键词列表
            title: 新闻标题（作为备用搜索词）
            
        Returns:
            Tuple[str, bool]: (搜索结果摘要, 搜索是否成功)
        """
        try:
            # 组合关键词进行搜索
            search_query = " ".join(keywords[:3])  # 使用前3个关键词
            
            if not search_query.strip():
                search_query = title[:30]  # 使用标题前30字符作为备用
            
            logger.info(f"执行百度搜索: {search_query}")
            
            # 调用百度搜索工具
            search_result = baidu_search_tool(search_query, max_results=5)
            
            if search_result and "搜索失败" not in search_result:
                logger.info(f"搜索成功: {search_query}")
                return search_result, True
            else:
                logger.warning(f"搜索失败: {search_query}")
                return f"搜索关键词'{search_query}'未获取到有效结果", False
                
        except Exception as e:
            logger.error(f"执行搜索时出错: {e}")
            return f"搜索过程中出现错误: {str(e)}", False
    
    def _generate_deep_analysis(self, news_item: NewsItem, search_results: str, keywords: List[str]) -> str:
        """
        生成深度分析报告
        
        Args:
            news_item: 新闻项
            search_results: 搜索结果
            keywords: 搜索关键词
            
        Returns:
            str: 深度分析报告
        """
        if self.client is None:
            return self._generate_mock_analysis(news_item, search_results, keywords)
        
        try:
            prompt = self._build_deep_analysis_prompt(news_item, search_results, keywords)
            response = self._call_ai_model(prompt)
            
            # 解析和清理分析结果
            analysis = self._parse_analysis_response(response)
            
            # 确保长度限制
            if len(analysis) > self.report_max_length:
                analysis = analysis[:self.report_max_length-3] + "..."
            
            return analysis
            
        except Exception as e:
            logger.error(f"生成深度分析报告失败: {e}")
            return self._generate_mock_analysis(news_item, search_results, keywords)
    
    def _build_deep_analysis_prompt(self, news_item: NewsItem, search_results: str, keywords: List[str]) -> str:
        """构建深度分析的prompt"""
        
        prompt = f"""作为专业的财经分析师，请对以下新闻进行深度分析。

原始新闻：
标题：{news_item.title}
内容：{news_item.content}
来源：{news_item.source}
重要性分数：{news_item.importance_score}分

相关背景信息（通过搜索关键词"{', '.join(keywords)}"获取）：
{search_results}

请基于原始新闻和背景信息，生成一份200字以内的深度分析报告，重点分析：
1. 新闻的深层影响和意义
2. 对相关行业或市场的潜在影响
3. 可能的发展趋势
4. 投资者需要关注的要点

要求：
- 专业、客观、准确
- 控制在200字以内
- 重点突出，条理清晰
- 结合背景信息提供更深层次的洞察

深度分析报告："""

        return prompt
    
    def _call_ai_model(self, prompt: str) -> str:
        """调用AI模型进行分析"""
        try:
            openrouter_config = self.config.get("ai_analysis", {}).get("openrouter", {})
            model = openrouter_config.get("model", "deepseek/deepseek-r1-0528:free")
            
            # 读取深度分析专属max_tokens，默认100000，并做安全裁剪
            deep_max_tokens = self.deep_config.get("max_tokens", 100000)
            # OpenRouter很多模型存在上下文限制，这里设定硬上限100000，避免请求被拒
            safe_max_tokens = max(1, min(deep_max_tokens, 100000))

            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=safe_max_tokens,
                temperature=openrouter_config.get("temperature", 0.1)
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"调用AI模型失败: {e}")
            raise
    
    def _parse_analysis_response(self, response: str) -> str:
        """解析AI分析响应"""
        try:
            # 简单清理响应内容
            analysis = response.strip()
            
            # 移除可能的前缀
            prefixes = ["深度分析报告：", "分析报告：", "报告：", "分析："]
            for prefix in prefixes:
                if analysis.startswith(prefix):
                    analysis = analysis[len(prefix):].strip()
                    break
            
            return analysis
            
        except Exception as e:
            logger.error(f"解析分析响应失败: {e}")
            return response  # 返回原始响应
    
    def _adjust_importance_score(self, news_item: NewsItem, deep_analysis: str, search_results: str) -> int:
        """
        根据深度分析调整重要性分数
        
        Args:
            news_item: 新闻项
            deep_analysis: 深度分析报告
            search_results: 搜索结果
            
        Returns:
            int: 调整后的重要性分数
        """
        try:
            original_score = news_item.importance_score
            
            # 简单的分数调整逻辑
            adjustment = 0
            
            # 基于深度分析内容的关键词调整
            high_impact_keywords = ["重大", "突破", "重要", "关键", "显著", "大幅", "急剧"]
            medium_impact_keywords = ["一定", "可能", "预期", "有望", "影响"]
            
            analysis_text = deep_analysis.lower()
            
            for keyword in high_impact_keywords:
                if keyword in analysis_text:
                    adjustment += 2
            
            for keyword in medium_impact_keywords:
                if keyword in analysis_text:
                    adjustment += 1
            
            # 基于搜索结果成功与否调整
            if "搜索成功" in search_results or len(search_results) > 100:
                adjustment += 3  # 搜索结果丰富，增加可信度
            
            # 计算最终分数
            adjusted_score = min(100, max(0, original_score + adjustment))
            
            logger.debug(f"分数调整: {original_score} -> {adjusted_score} (调整值: +{adjustment})")
            return adjusted_score
            
        except Exception as e:
            logger.error(f"调整重要性分数失败: {e}")
            return news_item.importance_score  # 返回原始分数
    
    def _generate_mock_analysis(self, news_item: NewsItem, search_results: str, keywords: List[str]) -> str:
        """生成模拟深度分析报告"""
        
        has_search_results = search_results and "搜索失败" not in search_results
        
        analysis = f"基于新闻'{news_item.title}'的深度分析：该新闻涉及{', '.join(keywords[:2])}等关键领域。"
        
        if has_search_results:
            analysis += "结合相关背景信息，此事件可能对相关行业产生一定影响。"
        else:
            analysis += "由于背景信息有限，建议持续关注后续发展。"
        
        analysis += "投资者应关注相关政策动向和市场反应，谨慎评估投资风险。"
        
        # 确保长度限制
        if len(analysis) > self.report_max_length:
            analysis = analysis[:self.report_max_length-3] + "..."
        
        return analysis
    
    def _create_skip_result(self, news_item: NewsItem) -> DeepAnalysisResult:
        """创建跳过分析的结果"""
        return DeepAnalysisResult(
            news_id=news_item.id or f"skip_{int(time.time())}",
            title=news_item.title,
            original_score=getattr(news_item, 'importance_score', 0),
            search_keywords=[],
            search_results_summary="未触发深度分析条件",
            deep_analysis_report="该新闻重要性分数未达到深度分析阈值",
            adjusted_score=getattr(news_item, 'importance_score', 0),
            analysis_time=datetime.now().isoformat(),
            search_success=False,
            model_used="skip"
        )
    
    def _create_error_result(self, news_item: NewsItem, error_msg: str) -> DeepAnalysisResult:
        """创建错误结果"""
        return DeepAnalysisResult(
            news_id=news_item.id or f"error_{int(time.time())}",
            title=news_item.title,
            original_score=getattr(news_item, 'importance_score', 0),
            search_keywords=[],
            search_results_summary=f"分析过程出错: {error_msg}",
            deep_analysis_report="由于技术问题，无法完成深度分析",
            adjusted_score=getattr(news_item, 'importance_score', 0),
            analysis_time=datetime.now().isoformat(),
            search_success=False,
            model_used="error"
        )


if __name__ == '__main__':
    # 测试功能
    logger.info("🔍 测试新闻深度分析器...")
    
    # 创建测试新闻
    test_news = NewsItem(
        title="央行宣布降准0.5个百分点，释放流动性约1万亿元",
        content="中国人民银行决定于2024年12月15日下调金融机构存款准备金率0.5个百分点，此次降准将释放长期资金约1万亿元。",
        source="央行官网",
        category="货币政策"
    )
    test_news.importance_score = 85  # 设置高重要性分数
    
    analyzer = DeepAnalyzer()
    result = analyzer.analyze_news_deep(test_news)
    
    logger.info(f"📰 新闻: {result.title}")
    logger.info(f"📊 原始重要性: {result.original_score} 分")
    logger.info(f"📊 调整后重要性: {result.adjusted_score} 分")
    logger.info(f"🔍 搜索关键词: {', '.join(result.search_keywords)}")
    logger.info(f"🔍 搜索成功: {result.search_success}")
    logger.info(f"📝 深度分析: {result.deep_analysis_report}")
    logger.info(f"🤖 使用模型: {result.model_used}") 