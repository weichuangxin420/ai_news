"""
AI分析模块
使用DeepSeek AI分析新闻对A股板块的影响
支持串行、并发和异步分析
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import multiprocessing as mp
from functools import partial
import threading
import queue

import openai
import yaml
from openai import OpenAI, AsyncOpenAI
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.database import NewsItem, db_manager
from ..utils.logger import get_logger

logger = get_logger("ai_analyzer")


@dataclass
class BatchAnalysisConfig:
    """批量分析配置"""
    max_concurrent_requests: int = 10
    batch_size: int = 20
    use_async: bool = True
    use_threading: bool = True
    use_multiprocessing: bool = False
    max_workers: int = None
    retry_attempts: int = 3
    timeout_seconds: int = 300
    rate_limit_per_minute: int = 100


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, max_calls_per_minute: int):
        self.max_calls = max_calls_per_minute
        self.calls = queue.Queue()
        self.lock = threading.Lock()
    
    async def acquire(self):
        """异步获取许可"""
        current_time = time.time()
        
        with self.lock:
            # 清理过期的调用记录
            while not self.calls.empty():
                call_time = self.calls.queue[0]
                if current_time - call_time > 60:
                    self.calls.get()
                else:
                    break
            
            # 检查是否超过限制
            if self.calls.qsize() >= self.max_calls:
                oldest_call = self.calls.queue[0]
                wait_time = 60 - (current_time - oldest_call)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            
            self.calls.put(current_time)


@dataclass
class AnalysisResult:
    """分析结果数据模型"""

    news_id: str
    impact_score: float  # 0到100，数值越高影响越大
    summary: str
    analysis_time: datetime

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "news_id": self.news_id,
            "impact_score": self.impact_score,
            "summary": self.summary,
            "analysis_time": self.analysis_time.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisResult":
        """从字典创建AnalysisResult对象"""
        analysis_time = (
            datetime.fromisoformat(data["analysis_time"])
            if data.get("analysis_time")
            else datetime.now()
        )

        return cls(
            news_id=data["news_id"],
            impact_score=data["impact_score"],
            summary=data["summary"],
            analysis_time=analysis_time,
        )


class AIAnalyzer:
    """AI新闻分析器，支持串行和并发分析"""

    def __init__(self, config_path: str = None, batch_config: BatchAnalysisConfig = None):
        """
        初始化AI分析器

        Args:
            config_path: 配置文件路径
            batch_config: 批量分析配置
        """
        self.config = self._load_config(config_path)
        self.batch_config = batch_config or BatchAnalysisConfig()
        
        # 客户端设置
        self.client = None
        self.async_client = None
        self.semaphore = None
        self.rate_limiter = None
        
        # 初始化客户端
        self._setup_client()
        if self.batch_config.use_async:
            self._setup_async_client()
            self._setup_concurrency_controls()

        # 统计信息
        self.stats = {"analyzed": 0, "errors": 0, "api_calls": 0, "total_tokens": 0}

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

    def _setup_async_client(self):
        """设置异步客户端"""
        ai_config = self.config.get("ai_analysis", {}).get("deepseek", {})
        
        # 从环境变量或配置文件获取API密钥
        api_key = os.getenv("DEEPSEEK_API_KEY") or ai_config.get("api_key", "")
        if api_key.startswith("${") and api_key.endswith("}"):
            # 处理环境变量引用
            env_var = api_key[2:-1]
            api_key = os.getenv(env_var, "")

        if api_key:
            try:
                self.async_client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=ai_config.get("base_url", "https://api.deepseek.com/v1"),
                )
                logger.info("异步DeepSeek API客户端初始化成功")
            except Exception as e:
                logger.error(f"异步DeepSeek API客户端初始化失败: {e}")
                self.async_client = None

    def _setup_concurrency_controls(self):
        """设置并发控制"""
        self.semaphore = asyncio.Semaphore(self.batch_config.max_concurrent_requests)
        self.rate_limiter = RateLimiter(self.batch_config.rate_limit_per_minute)

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

            # 首先尝试使用主模型（思考模型）
            try:
                response = self._call_deepseek_api(prompt)
                result = self._parse_analysis_response(news_item.id, response)
                self.stats["analyzed"] += 1
                logger.debug(f"新闻分析完成（主模型）: {news_item.title[:50]}...")
                return result
                
            except Exception as primary_error:
                logger.warning(f"主模型分析失败，尝试备用模型: {primary_error}")
                
                # 使用备用模型重试
                response = self._call_deepseek_api_fallback(prompt)
                result = self._parse_analysis_response(news_item.id, response)
                self.stats["analyzed"] += 1
                logger.debug(f"新闻分析完成（备用模型）: {news_item.title[:50]}...")
                return result

        except Exception as e:
            logger.error(f"新闻分析失败: {e}")
            self.stats["errors"] += 1
            return self._error_fallback_analysis(news_item)

    def analyze_single_news(self, news_item: NewsItem) -> AnalysisResult:
        """
        分析单条新闻（别名方法，兼容测试）

        Args:
            news_item: 新闻项

        Returns:
            AnalysisResult: 分析结果
        """
        return self.analyze_news(news_item)

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
请你作为一位专业的A股市场分析师，对以下新闻进行深度分析，重点关注其对A股市场的影响。

新闻信息：
标题：{news_item.title}
内容：{news_item.content}
来源：{news_item.source}
发布时间：{news_item.publish_time}
关键词：{', '.join(news_item.keywords)}

请按照以下JSON格式输出分析结果：
{{
    "impact_score": 数值(0到100，数值越高影响越大),
    "summary": "新闻影响摘要(100字以内)"
}}

分析要求：
1. 影响评分范围：0（无影响）到 100（极度正面），数值越高影响越大
2. 投资建议要具体、可操作，避免模糊表述

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

        # 记录API请求详情
        model = ai_config.get("model", "deepseek-chat")
        max_tokens = ai_config.get("max_tokens", 2000)
        temperature = ai_config.get("temperature", 0.1)
        timeout = analysis_params.get("timeout", 30)
        base_url = ai_config.get("base_url", "https://api.deepseek.com/v1")
        
        logger.info(f"🔄 准备调用DeepSeek API")
        logger.info(f"   模型: {model}")
        logger.info(f"   基础URL: {base_url}")
        logger.info(f"   最大令牌: {max_tokens}")
        logger.info(f"   温度: {temperature}")
        logger.info(f"   超时: {timeout}秒")
        logger.info(f"   提示词长度: {len(prompt)} 字符")

        try:
            import time
            start_time = time.time()
            
            logger.info(f"📤 开始API请求...")
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位专业的A股市场分析师，具有丰富的股票投资经验和深厚的市场洞察力。请严格按照要求的JSON格式输出分析结果。",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            )

            end_time = time.time()
            response_time = end_time - start_time
            
            logger.info(f"📥 API响应成功")
            logger.info(f"   响应时间: {response_time:.2f}秒")

            self.stats["api_calls"] += 1
            if hasattr(response, "usage") and response.usage:
                self.stats["total_tokens"] += response.usage.total_tokens
                logger.info(f"   使用令牌: {response.usage.total_tokens}")
                logger.info(f"   输入令牌: {response.usage.prompt_tokens}")
                logger.info(f"   输出令牌: {response.usage.completion_tokens}")

            response_content = response.choices[0].message.content
            logger.info(f"   响应内容长度: {len(response_content)} 字符")
            logger.debug(f"   响应内容预览: {response_content[:200]}...")
            
            # 记录完整响应内容用于调试
            logger.info(f"📄 完整API响应内容:")
            logger.info(f"   {response_content}")

            return response_content

        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time
            
            logger.error(f"❌ DeepSeek API调用失败")
            logger.error(f"   错误类型: {type(e).__name__}")
            logger.error(f"   错误信息: {str(e)}")
            logger.error(f"   失败时间: {response_time:.2f}秒")
            
            # 记录更详细的错误信息
            if hasattr(e, 'response'):
                logger.error(f"   HTTP状态码: {getattr(e.response, 'status_code', 'N/A')}")
                logger.error(f"   响应头: {getattr(e.response, 'headers', 'N/A')}")
                try:
                    logger.error(f"   响应内容: {e.response.text[:500]}...")
                except:
                    logger.error(f"   无法读取响应内容")
            
            if hasattr(e, 'code'):
                logger.error(f"   错误代码: {e.code}")
                
            raise

    def _call_deepseek_api_fallback(self, prompt: str) -> str:
        """
        调用DeepSeek API（备用模型）

        Args:
            prompt: 提示词

        Returns:
            str: API响应内容
        """
        ai_config = self.config.get("ai_analysis", {}).get("deepseek", {})
        analysis_params = self.config.get("ai_analysis", {}).get("analysis_params", {})

        # 使用备用模型配置
        fallback_model = ai_config.get("fallback_model", "deepseek-chat")
        fallback_timeout = analysis_params.get("fallback_timeout", 30)
        
        logger.info(f"🔄 准备调用DeepSeek API（备用模型）")
        logger.info(f"   备用模型: {fallback_model}")
        logger.info(f"   备用超时: {fallback_timeout}秒")

        try:
            import time
            start_time = time.time()
            
            logger.info(f"📤 开始备用API请求...")
            
            response = self.client.chat.completions.create(
                model=fallback_model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位专业的A股市场分析师，具有丰富的股票投资经验和深厚的市场洞察力。请严格按照要求的JSON格式输出分析结果。",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=ai_config.get("max_tokens", 2000),
                temperature=ai_config.get("temperature", 0.1),
                timeout=fallback_timeout,
            )

            end_time = time.time()
            response_time = end_time - start_time
            
            logger.info(f"📥 备用API响应成功")
            logger.info(f"   响应时间: {response_time:.2f}秒")

            response_content = response.choices[0].message.content
            logger.info(f"   响应内容长度: {len(response_content)} 字符")
            
            # 记录完整响应内容用于调试
            logger.info(f"📄 备用API完整响应内容:")
            logger.info(f"   {response_content}")

            return response_content

        except Exception as e:
            logger.error(f"❌ 备用DeepSeek API调用也失败: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _async_analyze_news(self, news_item: NewsItem) -> AnalysisResult:
        """异步分析单条新闻"""
        if not self.semaphore:
            self.semaphore = asyncio.Semaphore(self.batch_config.max_concurrent_requests)
        if not self.rate_limiter:
            self.rate_limiter = RateLimiter(self.batch_config.rate_limit_per_minute)
            
        logger.info(f"🔄 开始异步分析新闻: {news_item.title[:30]}...")
        logger.info(f"   信号量状态: {self.semaphore._value}/{self.batch_config.max_concurrent_requests}")
        
        async with self.semaphore:
            logger.info(f"📥 获取到信号量，开始分析: {news_item.title[:30]}...")
            
            try:
                await self.rate_limiter.acquire()
                logger.info(f"📊 通过速率限制检查")
                
                if not self.async_client:
                    logger.warning(f"❗ 异步客户端不可用，使用模拟分析")
                    return self._mock_analysis(news_item)
                
                prompt = self._build_analysis_prompt(news_item)
                
                logger.info(f"🚀 发起API请求 (模型: {self.config.get('ai_analysis', {}).get('deepseek', {}).get('model', 'deepseek-chat')})")
                start_time = time.time()
                
                response = await self.async_client.chat.completions.create(
                    model=self.config.get("ai_analysis", {}).get("deepseek", {}).get("model", "deepseek-chat"),
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一位专业的A股市场分析师。请严格按照JSON格式输出分析结果。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=self.config.get("ai_analysis", {}).get("deepseek", {}).get("max_tokens", 2000),
                    temperature=self.config.get("ai_analysis", {}).get("deepseek", {}).get("temperature", 0.1),
                    timeout=self.batch_config.timeout_seconds,
                )
                
                end_time = time.time()
                response_time = end_time - start_time
                
                logger.info(f"✅ API响应成功: {news_item.title[:30]}...")
                logger.info(f"   响应时间: {response_time:.2f}秒")
                
                if hasattr(response, "usage") and response.usage:
                    logger.info(f"   Token使用: {response.usage.total_tokens}")
                
                result = self._parse_analysis_response(
                    news_item.id, 
                    response.choices[0].message.content
                )
                
                self.stats["analyzed"] += 1
                logger.info(f"🎯 异步分析完成: {news_item.title[:30]}... (影响评分: {result.impact_score})")
                return result
                
            except asyncio.TimeoutError as e:
                logger.error(f"⏰ 异步分析超时: {news_item.title[:30]}... (超时时间: {self.batch_config.timeout_seconds}秒)")
                self.stats["errors"] += 1
                return self._error_fallback_analysis(news_item)
            except Exception as e:
                error_type = type(e).__name__
                logger.error(f"❌ 异步分析失败: {news_item.title[:30]}...")
                logger.error(f"   错误类型: {error_type}")
                logger.error(f"   错误信息: {str(e)}")
                
                # 特殊处理API限流错误
                if "429" in str(e) or "rate" in str(e).lower():
                    logger.warning(f"🚦 遇到速率限制，延迟后重试")
                    await asyncio.sleep(2)
                elif "503" in str(e) or "server" in str(e).lower():
                    logger.warning(f"🔧 服务器繁忙，延迟后重试")
                    await asyncio.sleep(5)
                
                self.stats["errors"] += 1
                return self._error_fallback_analysis(news_item)

    async def async_batch_analyze(self, news_list: List[NewsItem]) -> List[AnalysisResult]:
        """异步批量分析新闻"""
        if not news_list:
            return []
        
        logger.info(f"🚀 开始异步批量分析 {len(news_list)} 条新闻")
        logger.info(f"   并发设置: {self.batch_config.max_concurrent_requests} 个并发请求")
        logger.info(f"   批次大小: {self.batch_config.batch_size}")
        logger.info(f"   超时设置: {self.batch_config.timeout_seconds} 秒")
        logger.info(f"   速率限制: {self.batch_config.rate_limit_per_minute} 请求/分钟")
        
        start_time = time.time()
        
        # 重新设置信号量
        if not self.semaphore:
            self.semaphore = asyncio.Semaphore(self.batch_config.max_concurrent_requests)
            logger.info(f"🔧 创建新的信号量: {self.batch_config.max_concurrent_requests}")
        
        # 创建异步任务
        logger.info(f"📋 创建 {len(news_list)} 个异步任务...")
        tasks = [self._async_analyze_news(news_item) for news_item in news_list]
        
        # 分批处理，避免创建过多任务
        results = []
        batch_size = self.batch_config.batch_size
        total_batches = (len(tasks) + batch_size - 1) // batch_size
        
        logger.info(f"📦 分为 {total_batches} 个批次处理，每批 {batch_size} 个任务")
        
        for batch_idx in range(0, len(tasks), batch_size):
            batch_tasks = tasks[batch_idx:batch_idx + batch_size]
            current_batch = (batch_idx // batch_size) + 1
            
            logger.info(f"⚡ 处理第 {current_batch}/{total_batches} 批次 ({len(batch_tasks)} 个任务)")
            batch_start_time = time.time()
            
            try:
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                batch_end_time = time.time()
                batch_duration = batch_end_time - batch_start_time
                logger.info(f"✅ 批次 {current_batch} 完成，耗时: {batch_duration:.2f} 秒")
                
                # 处理异常结果
                success_count = 0
                error_count = 0
                
                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        error_count += 1
                        logger.error(f"❌ 批次 {current_batch} 任务 {j+1} 失败: {result}")
                        # 创建错误后备结果
                        news_item = news_list[batch_idx + j]
                        result = self._error_fallback_analysis(news_item)
                    else:
                        success_count += 1
                    
                    results.append(result)
                
                logger.info(f"📊 批次 {current_batch} 统计: 成功 {success_count}, 失败 {error_count}")
                
                # 避免API速率限制
                if current_batch < total_batches:
                    sleep_time = 0.5
                    logger.info(f"😴 批次间暂停 {sleep_time} 秒...")
                    await asyncio.sleep(sleep_time)
                    
            except Exception as e:
                logger.error(f"💥 批次 {current_batch} 整体失败: {e}")
                # 为整个批次创建错误结果
                for j in range(len(batch_tasks)):
                    news_item = news_list[batch_idx + j]
                    results.append(self._error_fallback_analysis(news_item))
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"🎯 异步批量分析完成!")
        logger.info(f"   总结果: {len(results)} 条")
        logger.info(f"   总耗时: {duration:.2f} 秒")
        logger.info(f"   平均耗时: {duration/len(results):.2f} 秒/条")
        logger.info(f"   成功率: {self.stats['analyzed']}/{len(results)} ({self.stats['analyzed']/len(results)*100:.1f}%)")
        
        return results

    def enhanced_batch_analyze(self, news_list: List[NewsItem]) -> List[AnalysisResult]:
        """增强版批量分析 - 强制使用并发策略"""
        if not news_list:
            return []
        
        news_count = len(news_list)
        logger.info(f"开始并发批量分析 {news_count} 条新闻")
        
        # 只要新闻数量大于2就使用并发
        if news_count > 2:
            logger.info("✅ 使用异步并发策略")
            try:
                # 确保异步客户端和并发控制已初始化
                if not self.async_client:
                    logger.info("初始化异步客户端...")
                    self._setup_async_client()
                    
                if not self.semaphore or not self.rate_limiter:
                    logger.info("初始化并发控制...")
                    self._setup_concurrency_controls()
                
                if not self.async_client:
                    logger.warning("异步客户端初始化失败，使用模拟分析")
                    return [self._mock_analysis(news) for news in news_list]
                
                return asyncio.run(self.async_batch_analyze(news_list))
            except Exception as e:
                logger.error(f"异步分析失败: {e}")
                import traceback
                traceback.print_exc()
                # 失败时使用模拟分析而不是串行分析
                return [self._mock_analysis(news) for news in news_list]
        else:
            logger.info("📊 新闻数量≤2，使用单条分析")
            return [self.analyze_news(news) for news in news_list]

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
            impact_score = float(data.get("impact_score", 0))
            impact_score = max(0, min(100, impact_score))  # 限制范围

            return AnalysisResult(
                news_id=news_id,
                impact_score=impact_score,
                summary=data.get("summary", ""),
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
            impact_score=0,
            summary="AI解析失败，使用默认分析结果",
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

        # 简单情感分析
        positive_words = ["上涨", "增长", "利好", "突破", "创新", "成功", "盈利"]
        negative_words = ["下跌", "亏损", "风险", "危机", "失败", "暴跌", "问题"]

        positive_score = sum(1 for word in positive_words if word in title_content)
        negative_score = sum(1 for word in negative_words if word in title_content)

        if positive_score > negative_score:
            impact_score = min(positive_score * 15, 80)  # 调整到0-100范围
        elif negative_score > positive_score:
            impact_score = max(100 - negative_score * 15, 20)  # 负面影响用较低分数表示
        else:
            impact_score = 50  # 中性影响

        return AnalysisResult(
            news_id=news_item.id,
            impact_score=impact_score,
            summary=f"基于关键词分析，新闻对A股市场有{impact_score:.0f}分的影响",
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
            impact_score=0,
            summary="分析过程中出现错误，无法生成有效分析",
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
                    (news_id, impact_score, summary, analysis_time)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        data["news_id"],
                        data["impact_score"],
                        data["summary"],
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
        positive_count = sum(1 for r in results if r.impact_score > 0) # 影响为正的新闻
        negative_count = sum(1 for r in results if r.impact_score < 0) # 影响为负的新闻
        neutral_count = sum(1 for r in results if r.impact_score == 0) # 影响为0的新闻

        report += f"""
- **正面新闻**: {positive_count} 条
- **负面新闻**: {negative_count} 条  
- **中性新闻**: {neutral_count} 条

"""

        # 板块影响统计
        sector_impact = {}
        # 板块影响分析已删除
        
        if False:  # 板块影响分析已删除，跳过此部分
            report += "## 板块影响排名\n\n"

        # 重要分析结果
        high_impact_results = [r for r in results if r.impact_score > 50] # 高影响新闻
        if high_impact_results:
            report += f"\n## 高影响新闻分析 ({len(high_impact_results)}条)\n\n"

            for i, result in enumerate(high_impact_results[:5], 1):
                report += f"""
### {i}. 影响评分: {result.impact_score:.1f} | 影响级别: 高

**新闻摘要**: {result.summary}

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


def create_enhanced_analyzer(
    max_concurrent: int = 10,
    use_async: bool = True,
    timeout_seconds: int = 300,
    rate_limit: int = 100
) -> AIAnalyzer:
    """创建增强版分析器的便捷函数，默认启用并发"""
    config = BatchAnalysisConfig(
        max_concurrent_requests=max_concurrent,
        use_async=use_async,
        timeout_seconds=timeout_seconds,
        rate_limit_per_minute=rate_limit
    )
    return AIAnalyzer(batch_config=config)


if __name__ == "__main__":
    # 测试分析功能
    results = analyze_latest_news(5)
    print(f"分析了 {len(results)} 条新闻")

    if results:
        analyzer = AIAnalyzer()
        report = analyzer.format_analysis_report(results)
        print(report)
