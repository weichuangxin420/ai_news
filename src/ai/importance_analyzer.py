#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻重要程度分析器

使用DeepSeek思考模型分析新闻的重要程度，评分范围0-100分
"""

import json
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Union
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
except ImportError:
    # 如果无法导入项目模块，使用相对导入
    from ..utils.database import NewsItem
    from ..utils.logger import get_logger

logger = get_logger("importance_analyzer")


@dataclass
class ImportanceResult:
    """重要程度分析结果"""
    news_id: str
    title: str
    importance_score: int  # 0-100分
    reasoning: str  # 分析推理过程
    key_factors: List[str]  # 影响重要程度的关键因素
    analysis_time: str
    model_used: str


class ImportanceAnalyzer:
    """新闻重要程度分析器"""
    
    def __init__(self, config: Dict = None):
        """
        初始化分析器
        
        Args:
            config: 配置字典
        """
        self.config = config or self._load_config()
        self.client = None
        self._init_client()
        
    def _load_config(self) -> Dict:
        """加载配置文件"""
        import os
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
        """初始化DeepSeek客户端"""
        try:
            deepseek_config = self.config.get("ai_analysis", {}).get("deepseek", {})
            
            if not deepseek_config.get("api_key"):
                logger.warning("未配置DeepSeek API密钥，将使用模拟模式")
                self.client = None
                return
            
            self.client = OpenAI(
                api_key=deepseek_config.get("api_key"),
                base_url=deepseek_config.get("base_url", "https://api.deepseek.com/v1")
            )
            
            logger.info("DeepSeek思考模型API客户端初始化成功")
            
        except Exception as e:
            logger.error(f"初始化DeepSeek客户端失败: {e}")
            self.client = None
    
    def analyze_importance(self, news_item: NewsItem) -> ImportanceResult:
        """
        分析单条新闻的重要程度
        
        Args:
            news_item: 新闻项
            
        Returns:
            ImportanceResult: 重要程度分析结果
        """
        if self.client is None:
            return self._mock_analysis(news_item)
        
        try:
            # 构建分析prompt
            prompt = self._build_importance_prompt(news_item)
            
            # 调用思考模型
            response = self._call_thinking_model(prompt)
            
            # 解析结果
            result = self._parse_importance_result(news_item, response)
            
            logger.info(f"完成新闻重要程度分析: {news_item.title[:50]}... -> {result.importance_score}分")
            
            return result
            
        except Exception as e:
            logger.error(f"分析新闻重要程度失败: {e}")
            return self._mock_analysis(news_item, error=True)
    
    def batch_analyze_importance(self, news_list: List[NewsItem]) -> List[ImportanceResult]:
        """
        批量分析新闻重要程度
        
        Args:
            news_list: 新闻列表
            
        Returns:
            List[ImportanceResult]: 重要程度分析结果列表
        """
        results = []
        total = len(news_list)
        
        logger.info(f"开始批量重要程度分析，共 {total} 条新闻")
        
        for i, news_item in enumerate(news_list, 1):
            try:
                result = self.analyze_importance(news_item)
                results.append(result)
                
                logger.info(f"进度: {i}/{total} - {result.importance_score}分")
                
                # 添加延时避免API限制
                if i < total and self.client is not None:
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"分析第{i}条新闻失败: {e}")
                # 添加错误占位结果
                error_result = self._mock_analysis(news_item, error=True)
                results.append(error_result)
        
        logger.info(f"批量重要程度分析完成，共分析 {len(results)} 条新闻")
        return results
    
    def _build_importance_prompt(self, news_item: NewsItem) -> str:
        """构建重要程度分析的prompt"""
        
        prompt = f"""请分析以下财经新闻的重要程度，并给出0-100分的评分。

新闻信息：
- 标题：{news_item.title}
- 内容：{news_item.content}
- 来源：{news_item.source}
- 分类：{news_item.category}
- 发布时间：{news_item.publish_time}

评分标准：
- 90-100分：极其重要，可能引发市场剧烈波动的重大事件
- 80-89分：很重要，对市场有显著影响的重要消息
- 70-79分：重要，对相关行业或板块有明显影响
- 60-69分：中等重要，有一定市场关注度
- 40-59分：一般重要，日常性财经新闻
- 20-39分：较低重要，影响有限的消息
- 0-19分：不重要，几乎无市场影响

请深入思考并分析：
1. 这条新闻涉及哪些关键要素？
2. 对股市、行业、经济的潜在影响有多大？
3. 新闻的时效性和权威性如何？
4. 是否涉及政策、监管、重大事件？
5. 对投资者决策的参考价值有多高？

请以JSON格式返回分析结果：
{{
    "importance_score": 分数(0-100整数),
    "reasoning": "详细的分析推理过程",
    "key_factors": ["影响重要程度的关键因素1", "关键因素2", "关键因素3"]
}}"""

        return prompt
    
    def _call_thinking_model(self, prompt: str) -> str:
        """调用DeepSeek思考模型"""
        try:
            deepseek_config = self.config.get("ai_analysis", {}).get("deepseek", {})
            
            # 从配置文件获取思考模型型号，默认为deepseek-reasoner
            thinking_model = deepseek_config.get("model", "deepseek-chat")
            
            logger.info(f"调用模型: {thinking_model}")
            
            # 使用配置的思考模型
            response = self.client.chat.completions.create(
                model=thinking_model,
                messages=[
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=deepseek_config.get("max_tokens", 2000),
                temperature=deepseek_config.get("temperature", 0.1)
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"调用DeepSeek思考模型失败: {e}")
            raise
    
    def _parse_importance_result(self, news_item: NewsItem, response: str) -> ImportanceResult:
        """解析重要程度分析结果"""
        try:
            # 尝试提取JSON部分
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result_data = json.loads(json_str)
            else:
                # 如果没有找到JSON，尝试解析纯文本
                result_data = self._parse_text_result(response)
            
            # 验证和清理数据
            importance_score = int(result_data.get("importance_score", 50))
            importance_score = max(0, min(100, importance_score))  # 确保在0-100范围内
            
            reasoning = result_data.get("reasoning", "AI分析过程")
            key_factors = result_data.get("key_factors", [])
            
            # 确保key_factors是列表
            if not isinstance(key_factors, list):
                key_factors = [str(key_factors)] if key_factors else ["未识别关键因素"]
            
            # 从配置文件获取模型名称
            deepseek_config = self.config.get("ai_analysis", {}).get("deepseek", {})
            model_used = deepseek_config.get("thinking_model", "deepseek-reasoner")
            
            return ImportanceResult(
                news_id=news_item.id or f"news_{int(time.time())}",
                title=news_item.title,
                importance_score=importance_score,
                reasoning=reasoning,
                key_factors=key_factors[:5],  # 最多保留5个关键因素
                analysis_time=datetime.now().isoformat(),
                model_used=model_used
            )
            
        except Exception as e:
            logger.error(f"解析分析结果失败: {e}")
            # 返回默认结果
            return self._mock_analysis(news_item, error=True)
    
    def _parse_text_result(self, response: str) -> Dict:
        """解析纯文本格式的结果"""
        result = {
            "importance_score": 50,
            "reasoning": response[:500],  # 取前500字符作为推理过程
            "key_factors": ["AI文本分析"]
        }
        
        # 尝试从文本中提取分数
        score_patterns = [
            r'(\d+)分',
            r'评分[：:]\s*(\d+)',
            r'重要程度[：:]\s*(\d+)',
            r'分数[：:]\s*(\d+)'
        ]
        
        for pattern in score_patterns:
            match = re.search(pattern, response)
            if match:
                try:
                    score = int(match.group(1))
                    if 0 <= score <= 100:
                        result["importance_score"] = score
                        break
                except ValueError:
                    continue
        
        return result
    
    def _mock_analysis(self, news_item: NewsItem, error: bool = False) -> ImportanceResult:
        """模拟分析结果（用于测试或API不可用时）"""
        
        if error:
            score = 50
            reasoning = "由于API调用失败，使用默认评分"
            factors = ["API错误", "默认评分"]
        else:
            # 基于标题关键词简单评分
            title = news_item.title.lower()
            score = 40  # 基础分数
            factors = []
            
            # 高重要性关键词
            high_keywords = ["央行", "政策", "监管", "重大", "重要", "突发", "紧急", "暴跌", "暴涨", "停牌", "IPO"]
            for keyword in high_keywords:
                if keyword in title:
                    score += 15
                    factors.append(f"包含高重要性关键词: {keyword}")
            
            # 中等重要性关键词
            medium_keywords = ["财报", "业绩", "增长", "下跌", "上涨", "合作", "投资", "收购"]
            for keyword in medium_keywords:
                if keyword in title:
                    score += 8
                    factors.append(f"包含中等重要性关键词: {keyword}")
            
            # 确保分数在合理范围内
            score = max(20, min(80, score))
            
            reasoning = f"基于标题关键词的模拟分析，评分为{score}分"
            
            if not factors:
                factors = ["标题分析", "模拟评分"]
        
        return ImportanceResult(
            news_id=news_item.id or f"mock_{int(time.time())}",
            title=news_item.title,
            importance_score=score,
            reasoning=reasoning,
            key_factors=factors,
            analysis_time=datetime.now().isoformat(),
            model_used="mock_analyzer"
        )


if __name__ == '__main__':
    # 测试功能
    print("🔍 测试新闻重要程度分析器...")
    
    # 创建测试新闻
    test_news = NewsItem(
        title="央行宣布降准0.5个百分点，释放流动性约1万亿元",
        content="中国人民银行决定于2024年12月15日下调金融机构存款准备金率0.5个百分点，此次降准将释放长期资金约1万亿元。",
        source="央行官网",
        category="货币政策"
    )
    
    analyzer = ImportanceAnalyzer()
    result = analyzer.analyze_importance(test_news)
    
    logger.info(f"📰 新闻: {result.title}")
    logger.info(f"📊 重要程度: {result.importance_score} 分")
    logger.info(f"🔍 关键因素: {', '.join(result.key_factors)}")
    logger.info(f"💭 分析推理: {result.reasoning}")
    logger.info(f"🤖 使用模型: {result.model_used}") 