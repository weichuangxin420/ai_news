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
        
        # AI自驱动检索配置
        self.max_search_rounds = self.deep_config.get("max_search_rounds", 3)
        self.evidence_threshold = self.deep_config.get("evidence_threshold", 2)  # 至少需要的有效证据数
        self.max_evidence_kept = self.deep_config.get("max_evidence_kept", 5)   # 保留的最大证据数
        
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
                error_msg = "未配置OpenRouter API密钥，深度分析无法正常工作"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            self.client = OpenAI(
                api_key=openrouter_config.get("api_key"),
                base_url=openrouter_config.get("base_url", "https://openrouter.ai/api/v1")
            )
            
            logger.info("OpenRouter深度分析API客户端初始化成功")
            
        except Exception as e:
            error_msg = f"初始化OpenRouter客户端失败: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
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
            
            # 使用AI自驱动检索模式进行深度分析
            if self.client is not None:
                logger.info("使用AI自驱动检索模式进行深度分析")
                return self._analyze_with_ai_self_search(news_item)
            else:
                raise RuntimeError("OpenRouter客户端未初始化，无法进行深度分析")
                
        except Exception as e:
            logger.error(f"深度分析失败: {e}")
            return self._create_error_result(news_item, str(e))
    
    def _analyze_with_ai_self_search(self, news_item: NewsItem) -> DeepAnalysisResult:
        """
        使用AI自驱动检索模式进行深度分析
        
        Args:
            news_item: 新闻项
            
        Returns:
            DeepAnalysisResult: 深度分析结果
        """
        try:
            # 1. AI查询规划：生成检索问题列表
            search_queries = self._generate_search_queries(news_item)
            logger.info(f"AI生成检索查询: {search_queries}")
            
            # 2. 多轮搜索：执行每个查询
            all_search_results = []
            successful_searches = 0
            
            for i, query in enumerate(search_queries):
                logger.info(f"执行第{i+1}轮搜索: {query}")
                search_result, success = self._perform_single_search(query)
                
                if success:
                    all_search_results.append({
                        'query': query,
                        'result': search_result,
                        'round': i + 1
                    })
                    successful_searches += 1
                    logger.info(f"第{i+1}轮搜索成功，获得{len(search_result)}字符结果")
                else:
                    logger.warning(f"第{i+1}轮搜索失败: {query}")
                
                # 提前停止条件：获得足够证据
                if successful_searches >= self.evidence_threshold:
                    logger.info(f"已获得{successful_searches}个有效搜索结果，满足证据阈值")
                    break
            
            # 3. 证据汇总与评分
            evidence_summary = self._evaluate_and_summarize_evidence(all_search_results, news_item)
            logger.info(f"证据汇总完成，保留{len(evidence_summary.get('top_evidence', []))}个高质量证据")
            
            # 4. 基于证据生成深度分析报告
            deep_report = self._generate_evidence_based_analysis(news_item, evidence_summary)
            
            # 5. 重新评估重要性分数
            adjusted_score = self._adjust_score_with_evidence(
                news_item, deep_report, evidence_summary
            ) if self.enable_score_adjustment else news_item.importance_score
            
            # 构建结果
            result = DeepAnalysisResult(
                news_id=news_item.id or f"ai_deep_{int(time.time())}",
                title=news_item.title,
                original_score=news_item.importance_score,
                search_keywords=[result['query'] for result in all_search_results],
                search_results_summary=evidence_summary.get('summary', ''),
                deep_analysis_report=deep_report,
                adjusted_score=adjusted_score,
                analysis_time=datetime.now().isoformat(),
                search_success=successful_searches > 0,
                model_used=self.config.get("ai_analysis", {}).get("openrouter", {}).get("model", "deepseek/deepseek-chat-v3.1")
            )
            
            logger.info(f"AI自驱动深度分析完成: {news_item.title[:50]}... -> {adjusted_score}分 (原{news_item.importance_score}分)")
            logger.info("深度分析报告全文:")
            logger.info(deep_report)
            return result
            
        except Exception as e:
            logger.error(f"AI自驱动深度分析失败: {e}")
            raise RuntimeError(f"AI自驱动深度分析失败: {e}")
    

    
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
    
    def _generate_search_queries(self, news_item: NewsItem) -> List[str]:
        """
        AI生成检索查询列表
        
        Args:
            news_item: 新闻项
            
        Returns:
            List[str]: 检索查询列表
        """
        try:
            prompt = f"""作为专业的财经信息分析师，请基于以下新闻生成1-3个最有价值的搜索查询，用于获取相关背景信息和深度分析素材。

新闻信息：
标题：{news_item.title}
内容：{news_item.content}
来源：{news_item.source}
重要性分数：{news_item.importance_score}分

请生成查询时考虑：
1.先查询原新闻，再查询相关新闻
2.考虑相关公司、行业、政策

要求：
- 每个查询15-30字，精确有针对性
- 避免过于宽泛的搜索词
- 优先获取权威、时效性强的信息
- 查询应互补，覆盖不同维度

请直接输出查询列表，每行一个，格式如：
1. 查询内容1
2. 查询内容2
3. 查询内容3"""

            response = self._call_ai_model(prompt)
            
            # 解析查询列表
            queries = self._parse_search_queries(response)
            
            # 限制查询数量
            queries = queries[:self.max_search_rounds]
            
            if not queries:
                # 降级方案：基于新闻标题生成查询
                fallback_query = news_item.title[:25] + " 最新消息"
                queries = [fallback_query]
                logger.warning(f"AI查询生成失败，使用降级查询: {fallback_query}")
            
            return queries
            
        except Exception as e:
            logger.error(f"生成搜索查询失败: {e}")
            # 降级方案
            fallback_query = news_item.title[:25] + " 相关信息"
            return [fallback_query]
    
    def _parse_search_queries(self, response: str) -> List[str]:
        """
        解析AI生成的搜索查询响应
        
        Args:
            response: AI响应文本
            
        Returns:
            List[str]: 解析出的查询列表
        """
        try:
            queries = []
            lines = response.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                # 匹配编号格式：1. 、2. 、3. 等
                if re.match(r'^\d+\.?\s*', line):
                    query = re.sub(r'^\d+\.?\s*', '', line).strip()
                    if query and len(query) >= 5:  # 过滤过短的查询
                        queries.append(query)
                elif line and not line.startswith(('要求', '请', '注意', '格式')):
                    # 没有编号但是有内容的行
                    if len(line) >= 5:
                        queries.append(line)
            
            return queries[:self.max_search_rounds]
            
        except Exception as e:
            logger.error(f"解析搜索查询失败: {e}")
            return []
    

    
    def _perform_single_search(self, query: str) -> Tuple[str, bool]:
        """
        执行单次搜索
        
        Args:
            query: 搜索查询
            
        Returns:
            Tuple[str, bool]: (搜索结果, 搜索是否成功)
        """
        try:
            logger.debug(f"执行搜索查询: {query}")
            
            # 调用百度搜索工具
            search_result = baidu_search_tool(query, max_results=3)
            
            if search_result and "搜索失败" not in search_result and len(search_result) > 50:
                return search_result, True
            else:
                logger.warning(f"搜索查询无效结果: {query}")
                return f"查询'{query}'未获取到有效结果", False
                
        except Exception as e:
            logger.error(f"搜索查询出错: {query} - {e}")
            return f"搜索过程出现错误: {str(e)}", False
    
    def _evaluate_and_summarize_evidence(self, search_results: List[Dict], news_item: NewsItem) -> Dict:
        """
        评估和汇总搜索证据
        
        Args:
            search_results: 搜索结果列表，每个元素包含 query, result, round
            news_item: 原始新闻项
            
        Returns:
            Dict: 包含评分、汇总等信息的证据字典
        """
        try:
            if not search_results:
                return {
                    'summary': '未获取到有效搜索结果',
                    'top_evidence': [],
                    'evidence_count': 0,
                    'avg_score': 0
                }
            
            # 为每个搜索结果评分
            scored_evidence = []
            
            for search_data in search_results:
                query = search_data['query']
                result = search_data['result']
                round_num = search_data['round']
                
                # 计算证据质量分数
                score = self._calculate_evidence_score(result, query, news_item)
                
                scored_evidence.append({
                    'query': query,
                    'result': result,
                    'round': round_num,
                    'score': score,
                    'length': len(result)
                })
                
                logger.debug(f"第{round_num}轮搜索证据评分: {score:.2f} - {query[:20]}...")
            
            # 按分数排序，取前N个
            scored_evidence.sort(key=lambda x: x['score'], reverse=True)
            top_evidence = scored_evidence[:self.max_evidence_kept]
            
            # 生成汇总
            evidence_summary = self._create_evidence_summary(top_evidence, news_item)
            
            avg_score = sum(e['score'] for e in scored_evidence) / len(scored_evidence) if scored_evidence else 0
            
            return {
                'summary': evidence_summary,
                'top_evidence': top_evidence,
                'evidence_count': len(search_results),
                'avg_score': avg_score,
                'total_length': sum(e['length'] for e in scored_evidence)
            }
            
        except Exception as e:
            logger.error(f"证据评估与汇总失败: {e}")
            return {
                'summary': f'证据处理过程出现错误: {str(e)}',
                'top_evidence': [],
                'evidence_count': 0,
                'avg_score': 0
            }
    
    def _calculate_evidence_score(self, result: str, query: str, news_item: NewsItem) -> float:
        """
        计算单个证据的质量分数
        
        Args:
            result: 搜索结果文本
            query: 搜索查询
            news_item: 原始新闻
            
        Returns:
            float: 证据质量分数 (0-10)
        """
        try:
            score = 0.0
            
            # 1. 权威度评分 (0-3分)
            authority_keywords = ['官方', '政府', '央行', '证监会', '银保监会', '发改委', '财政部', '商务部', '新华社', '人民日报']
            authority_score = 0
            for keyword in authority_keywords:
                if keyword in result:
                    authority_score += 0.5
                    if authority_score >= 3:
                        break
            score += min(authority_score, 3)
            
            # 2. 相关度评分 (0-2分)
            # 检查新闻标题关键词在结果中的出现
            title_words = [word for word in news_item.title if len(word) >= 2]
            relevance_score = 0
            for word in title_words[:5]:  # 取前5个词
                if word in result:
                    relevance_score += 0.4
            score += min(relevance_score, 2)
            
            # 3. 信息密度评分 (0-2分)
            info_keywords = ['数据', '统计', '报告', '分析', '预测', '影响', '政策', '措施', '方案']
            info_score = 0
            for keyword in info_keywords:
                if keyword in result:
                    info_score += 0.3
            score += min(info_score, 2)
            
            # 4. 时效性评分 (0-2分)
            time_keywords = ['最新', '今日', '刚刚', '今年', '近期', '目前', '现在', '2024', '2025']
            time_score = 0
            for keyword in time_keywords:
                if keyword in result:
                    time_score += 0.4
            score += min(time_score, 2)
            
            # 5. 长度合理性 (0-1分)
            length = len(result)
            if 100 <= length <= 2000:
                length_score = 1.0
            elif 50 <= length < 100 or 2000 < length <= 5000:
                length_score = 0.5
            else:
                length_score = 0.1
            score += length_score
            
            return min(score, 10.0)
            
        except Exception as e:
            logger.error(f"计算证据分数失败: {e}")
            return 0.0
    
    def _create_evidence_summary(self, top_evidence: List[Dict], news_item: NewsItem) -> str:
        """
        创建证据汇总
        
        Args:
            top_evidence: 排序后的顶级证据列表
            news_item: 原始新闻
            
        Returns:
            str: 证据汇总文本
        """
        try:
            if not top_evidence:
                return "未获取到有效证据"
            
            summary_parts = []
            
            for i, evidence in enumerate(top_evidence):
                query = evidence['query']
                result = evidence['result']
                score = evidence['score']
                
                # 截取结果的关键部分
                result_excerpt = result[:200] + "..." if len(result) > 200 else result
                
                summary_parts.append(f"证据{i+1}[查询: {query}][评分: {score:.1f}]: {result_excerpt}")
            
            return "\n\n".join(summary_parts)
            
        except Exception as e:
            logger.error(f"创建证据汇总失败: {e}")
            return "证据汇总处理出错"
    
    def _generate_evidence_based_analysis(self, news_item: NewsItem, evidence_summary: Dict) -> str:
        """
        基于证据生成深度分析报告
        
        Args:
            news_item: 新闻项
            evidence_summary: 证据汇总字典
            
        Returns:
            str: 深度分析报告
        """
        try:
            prompt = self._build_evidence_based_analysis_prompt(news_item, evidence_summary)
            response = self._call_ai_model(prompt)
            
            # 解析和清理分析结果
            analysis = self._parse_analysis_response(response)
            
            # 确保长度限制
            if len(analysis) > self.report_max_length:
                analysis = analysis[:self.report_max_length-3] + "..."
            
            return analysis
            
        except Exception as e:
            logger.error(f"生成证据基于深度分析报告失败: {e}")
            raise RuntimeError(f"生成证据基于深度分析报告失败: {e}")
    
    def _build_evidence_based_analysis_prompt(self, news_item: NewsItem, evidence_summary: Dict) -> str:
        """构建基于证据生成深度分析的prompt"""
        
        prompt = f"""作为专业的财经分析师，请基于以下证据和新闻信息，生成一份200字以内的深度分析报告。

原始新闻：
标题：{news_item.title}
内容：{news_item.content}
来源：{news_item.source}
重要性分数：{news_item.importance_score}分

证据汇总：
{evidence_summary.get('summary', '未获取到有效证据')}

请基于原始新闻和证据，生成一份200字以内的深度分析报告，重点分析：
1. 新闻的深层影响和意义
2. 对相关行业或市场的潜在影响
3. 可能的发展趋势
4. 投资者需要关注的要点

要求：
- 专业、客观、准确
- 控制在200字以内
- 重点突出，条理清晰
- 结合证据提供更深层次的洞察

深度分析报告："""

        return prompt
    

    

    
    def _call_ai_model(self, prompt: str) -> str:
        """调用AI模型进行分析"""
        try:
            openrouter_config = self.config.get("ai_analysis", {}).get("openrouter", {})
            model = openrouter_config.get("model", "deepseek/deepseek-chat-v3.1")
            
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
    
    def _adjust_score_with_evidence(self, news_item: NewsItem, deep_analysis: str, evidence_summary: Dict) -> int:
        """
        基于证据和深度分析调整重要性分数
        
        Args:
            news_item: 新闻项
            deep_analysis: 深度分析报告
            evidence_summary: 证据汇总字典
            
        Returns:
            int: 调整后的重要性分数
        """
        try:
            original_score = news_item.importance_score
            adjustment = 0
            
            # 1. 基于证据质量调整 (0-15分)
            avg_evidence_score = evidence_summary.get('avg_score', 0)
            evidence_count = evidence_summary.get('evidence_count', 0)
            
            if avg_evidence_score >= 7.0:
                adjustment += 10  # 高质量证据
            elif avg_evidence_score >= 5.0:
                adjustment += 6   # 中等质量证据
            elif avg_evidence_score >= 3.0:
                adjustment += 3   # 低质量证据
            
            # 额外奖励多个证据来源
            if evidence_count >= 3:
                adjustment += 3
            elif evidence_count >= 2:
                adjustment += 2
            
            # 2. 基于深度分析内容调整 (0-10分)
            analysis_text = deep_analysis.lower()
            
            # 高影响关键词
            high_impact_keywords = ['重大', '突破', '关键', '显著', '急剧', '暴跌', '暴涨', '重要']
            high_impact_count = sum(1 for keyword in high_impact_keywords if keyword in analysis_text)
            adjustment += min(high_impact_count * 2, 6)
            
            # 市场敏感词
            market_keywords = ['政策', '利率', '汇率', '央行', '监管', '改革', '风险']
            market_count = sum(1 for keyword in market_keywords if keyword in analysis_text)
            adjustment += min(market_count * 1, 4)
            
            # 3. 基于证据权威性额外调整 (0-5分)
            evidence_text = evidence_summary.get('summary', '')
            authority_keywords = ['央行', '银保监会', '证监会', '政府', '官方', '新华社', '人民日报']
            authority_count = sum(1 for keyword in authority_keywords if keyword in evidence_text)
            adjustment += min(authority_count * 1, 5)
            
            # 计算最终分数
            adjusted_score = min(100, max(0, original_score + adjustment))
            
            logger.info(f"基于证据的分数调整: {original_score} -> {adjusted_score} (调整值: +{adjustment})")
            logger.info(f"调整因子 - 证据质量: {avg_evidence_score:.1f}, 证据数量: {evidence_count}, 权威性: {authority_count}")
            
            return adjusted_score
            
        except Exception as e:
            logger.error(f"基于证据调整重要性分数失败: {e}")
            return news_item.importance_score  # 返回原始分数


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