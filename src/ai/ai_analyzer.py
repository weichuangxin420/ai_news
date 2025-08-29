"""
AI分析模块
使用DeepSeek AI分析新闻对A股板块的影响
支持单条新闻分析
"""

import json
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import openai
import yaml
from openai import OpenAI

from ..utils.database import NewsItem, db_manager
from ..utils.logger import get_logger

logger = get_logger("ai_analyzer")


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
    """AI新闻分析器，支持单条新闻分析和备用模型调用"""

    def __init__(self, config_path: str = None, provider: str = "openrouter"):
        """
        初始化AI分析器

        Args:
            config_path: 配置文件路径
            provider: API提供商，支持 'deepseek' 或 'openrouter'
        """
        self.config = self._load_config(config_path)
        # 强制默认使用openrouter，除非明确传入deepseek
        self.provider = provider if provider in ["openrouter", "deepseek"] else "openrouter"
        
        # 客户端设置
        self.client = None
        self.fallback_client = None  # 备用客户端
        
        # 初始化客户端
        self._setup_client()

        # 统计信息
        self.stats = {"analyzed": 0, "errors": 0, "api_calls": 0, "total_tokens": 0, "provider": provider, "fallback_used": 0}

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
        """设置OpenAI客户端（兼容DeepSeek和OpenRouter API）和备用客户端"""
        if self.provider == "openrouter":
            ai_config = self.config.get("ai_analysis", {}).get("openrouter", {})
            provider_name = "OpenRouter"
            default_base_url = "https://openrouter.ai/api/v1"
            config_path_info = "config/config.yaml -> ai_analysis -> openrouter -> api_key"
        else:  # deepseek
            ai_config = self.config.get("ai_analysis", {}).get("deepseek", {})
            provider_name = "DeepSeek"
            default_base_url = "https://api.deepseek.com/v1"
            config_path_info = "config/config.yaml -> ai_analysis -> deepseek -> api_key"

        # 只从配置文件获取API密钥
        api_key = ai_config.get("api_key", "")
        
        if not api_key:
            error_msg = f"配置文件中未找到{provider_name} API密钥，程序无法正常运行"
            logger.error(error_msg)
            logger.error(f"请在配置文件中添加相应的API密钥配置项")
            logger.error(f"配置路径: {config_path_info}")
            raise ValueError(error_msg)

        try:
            base_url = ai_config.get("base_url", default_base_url)
            logger.info(f"正在初始化{provider_name} API客户端，base_url: {base_url}")
            
            # OpenRouter需要设置额外的headers
            extra_headers = {}
            if self.provider == "openrouter":
                extra_headers = {
                    "HTTP-Referer": "https://ai-news-collector.com",  # 可选，用于在openrouter.ai排行榜显示
                    "X-Title": "AI-News-Analysis-System",  # 可选，应用名称（使用英文避免编码问题）
                }
            
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                default_headers=extra_headers if extra_headers else None,
            )
            logger.info(f"{provider_name} API客户端初始化成功")
            
            # 初始化备用客户端
            self._setup_fallback_client(ai_config, extra_headers)
            
        except Exception as e:
            error_msg = f"{provider_name} API客户端初始化失败: {e}"
            logger.error(error_msg)
            logger.error(f"API密钥长度: {len(api_key) if api_key else 0}")
            logger.error(f"Base URL: {base_url}")
            raise RuntimeError(error_msg)
    
    def _setup_fallback_client(self, ai_config: dict, extra_headers: dict):
        """设置备用客户端"""
        try:
            fallback_model = ai_config.get("fallback_model")
            if not fallback_model:
                logger.info("未配置备用模型，跳过备用客户端初始化")
                return
            
            # 使用相同的API密钥和基础URL，但使用备用模型
            base_url = ai_config.get("base_url")
            api_key = ai_config.get("api_key")
            
            logger.info(f"正在初始化备用客户端，模型: {fallback_model}")
            
            self.fallback_client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                default_headers=extra_headers if extra_headers else None,
            )
            logger.info(f"备用客户端初始化成功，模型: {fallback_model}")
            
        except Exception as e:
            logger.warning(f"备用客户端初始化失败: {e}")
            self.fallback_client = None

    def analyze_news(self, news_item: NewsItem) -> AnalysisResult:
        """
        分析单条新闻（支持失败重试）

        Args:
            news_item: 新闻项

        Returns:
            AnalysisResult: 分析结果
        """
        if not self.client:
            logger.error(f"{self.provider.upper()} API客户端不可用，无法进行分析")
            raise RuntimeError(f"{self.provider.upper()} API客户端不可用")

        # 构建提示词
        prompt = self._build_analysis_prompt(news_item)

        # 调用AI API进行分析（支持重试）
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self._call_ai_api(prompt)
                result = self._parse_analysis_response(news_item.id, response)
                self.stats["analyzed"] += 1
                logger.debug(f"新闻分析完成: {news_item.title[:50]}...")
                return result
                
            except Exception as e:
                # 检查是否是HTTP错误（状态码不是200）
                is_http_error = False
                status_code = None
                
                if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                    status_code = e.response.status_code
                    is_http_error = status_code != 200
                
                if is_http_error:
                    logger.error(f"❌ 第{attempt + 1}次尝试失败 - HTTP状态码: {status_code}")
                    logger.error(f"   错误信息: {str(e)}")
                    
                    if attempt < max_retries - 1:  # 不是最后一次尝试
                        # 计算等待时间：第1次1-30秒，第2次30-60秒，第3次60-90秒
                        if attempt == 0:
                            wait_time = random.randint(1, 30)
                        elif attempt == 1:
                            wait_time = random.randint(30, 60)
                        else:
                            wait_time = random.randint(60, 90)
                        
                        logger.info(f"⏳ 等待 {wait_time} 秒后进行第 {attempt + 2} 次重试...")
                        time.sleep(wait_time)
                        continue
                    else:
                        # 最后一次尝试失败，尝试使用备用客户端
                        if self.fallback_client:
                            logger.warning(f"🔄 主客户端三次重试均失败，尝试使用备用客户端...")
                            try:
                                response = self._call_ai_api_with_fallback(prompt)
                                result = self._parse_analysis_response(news_item.id, response)
                                self.stats["analyzed"] += 1
                                self.stats["fallback_used"] += 1
                                logger.info(f"✅ 备用客户端调用成功！")
                                logger.debug(f"新闻分析完成: {news_item.title[:50]}...")
                                return result
                            except Exception as fallback_error:
                                logger.error(f"❌ 备用客户端也失败，最终失败原因:")
                                if status_code is not None:
                                    logger.error(f"   主客户端HTTP状态码: {status_code}")
                                logger.error(f"   主客户端错误: {str(e)}")
                                logger.error(f"   备用客户端错误: {str(fallback_error)}")
                                raise RuntimeError(f"主客户端和备用客户端均失败: 主客户端({str(e)})，备用客户端({str(fallback_error)})")
                        else:
                            # 没有备用客户端，记录详细错误并抛出异常
                            logger.error(f"❌ 所有重试尝试均失败，且无备用客户端，最终失败原因:")
                            if status_code is not None:
                                logger.error(f"   HTTP状态码: {status_code}")
                            logger.error(f"   错误类型: {type(e).__name__}")
                            logger.error(f"   错误信息: {str(e)}")
                            raise
                else:
                    # 非HTTP错误，直接抛出异常
                    logger.error(f"❌ 非HTTP错误，不进行重试: {str(e)}")
                    raise



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

    def _call_ai_api(self, prompt: str) -> str:
        """
        调用AI API（支持DeepSeek和OpenRouter）

        Args:
            prompt: 提示词

        Returns:
            str: API响应内容
        """
        # 根据provider获取对应的配置
        if self.provider == "openrouter":
            ai_config = self.config.get("ai_analysis", {}).get("openrouter", {})
            default_model = "deepseek/deepseek-chat-v3.1"
            default_base_url = "https://openrouter.ai/api/v1"
        else:  # deepseek（仅显式传入才使用）
            ai_config = self.config.get("ai_analysis", {}).get("deepseek", {})
            default_model = "deepseek-chat"
            default_base_url = "https://api.deepseek.com/v1"
        
        analysis_params = self.config.get("ai_analysis", {}).get("analysis_params", {})

        # 记录API请求详情
        model = ai_config.get("model", default_model)
        max_tokens = ai_config.get("max_tokens", 10000)
        temperature = ai_config.get("temperature", 0.1)
        timeout = analysis_params.get("timeout", 600)  # 默认10分钟
        base_url = ai_config.get("base_url", default_base_url)
        
        logger.info(f"🔄 准备调用{self.provider.upper()} API")
        logger.info(f"   模型: {model}")
        logger.info(f"   基础URL: {base_url}")
        logger.info(f"   最大令牌: {max_tokens}")
        logger.info(f"   温度: {temperature}")
        logger.info(f"   超时: {timeout}秒")
        logger.info(f"   提示词长度: {len(prompt)} 字符")

        try:
            start_time = time.time()
            
            logger.info(f"📤 开始API请求...")
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[
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
            
            logger.error(f"❌ {self.provider.upper()} API调用失败")
            logger.error(f"   错误类型: {type(e).__name__}")
            logger.error(f"   错误信息: {str(e)}")
            logger.error(f"   失败时间: {response_time:.2f}秒")
            
            # 记录更详细的错误信息
            if hasattr(e, 'response'):
                logger.error(f"   HTTP状态码: {getattr(e.response, 'status_code', 'N/A')}")
                logger.error(f"   响应头: {getattr(e.response, 'headers', 'N/A')}")
                try:
                    logger.error(f"   响应内容: {e.response.text[:500]}...")
                except (AttributeError, UnicodeDecodeError):
                    logger.error(f"   无法读取响应内容")
            
            if hasattr(e, 'code'):
                logger.error(f"   错误代码: {e.code}")
                
            raise
    
    def _call_ai_api_with_fallback(self, prompt: str) -> str:
        """
        使用备用客户端调用AI API

        Args:
            prompt: 提示词

        Returns:
            str: API响应内容
        """
        if not self.fallback_client:
            raise RuntimeError("备用客户端未初始化")
        
        # 根据provider获取对应的备用配置
        if self.provider == "openrouter":
            ai_config = self.config.get("ai_analysis", {}).get("openrouter", {})
            fallback_model = ai_config.get("fallback_model", "deepseek/deepseek-chat-v3.1")
        else:  # deepseek
            ai_config = self.config.get("ai_analysis", {}).get("deepseek", {})
            fallback_model = ai_config.get("fallback_model", "deepseek-chat")
        
        analysis_params = self.config.get("ai_analysis", {}).get("analysis_params", {})

        # 记录备用API请求详情
        max_tokens = ai_config.get("max_tokens", 10000)
        temperature = ai_config.get("temperature", 0.1)
        timeout = analysis_params.get("fallback_timeout", 600)  # 使用备用超时时间
        
        logger.info(f"🔄 使用备用客户端调用API")
        logger.info(f"   备用模型: {fallback_model}")
        logger.info(f"   最大令牌: {max_tokens}")
        logger.info(f"   温度: {temperature}")
        logger.info(f"   超时: {timeout}秒")
        logger.info(f"   提示词长度: {len(prompt)} 字符")

        try:
            start_time = time.time()
            
            logger.info(f"📤 开始备用API请求...")
            
            response = self.fallback_client.chat.completions.create(
                model=fallback_model,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            )

            end_time = time.time()
            response_time = end_time - start_time
            
            logger.info(f"📥 备用API响应成功")
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
            logger.info(f"📄 完整备用API响应内容:")
            logger.info(f"   {response_content}")

            return response_content

        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time
            
            logger.error(f"❌ 备用API调用失败")
            logger.error(f"   错误类型: {type(e).__name__}")
            logger.error(f"   错误信息: {str(e)}")
            logger.error(f"   失败时间: {response_time:.2f}秒")
            
            # 记录更详细的错误信息
            if hasattr(e, 'response'):
                logger.error(f"   HTTP状态码: {getattr(e.response, 'status_code', 'N/A')}")
                logger.error(f"   响应头: {getattr(e.response, 'headers', 'N/A')}")
                try:
                    logger.error(f"   响应内容: {e.response.text[:500]}...")
                except (AttributeError, UnicodeDecodeError):
                    logger.error(f"   无法读取响应内容")
            
            if hasattr(e, 'code'):
                logger.error(f"   错误代码: {e.code}")
                
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
            raise ValueError(f"AI响应解析失败: {e}")





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

    def analyze_news_batch(self, news_items: List[NewsItem], max_workers: Optional[int] = None) -> List[AnalysisResult]:
        """
        并行分析多条新闻
        
        Args:
            news_items: 新闻列表
            max_workers: 最大工作线程数，默认从配置获取
            
        Returns:
            List[AnalysisResult]: 分析结果列表
        """
        if not news_items:
            return []
            
        # 获取并发配置
        if max_workers is None:
            analysis_params = self.config.get("ai_analysis", {}).get("analysis_params", {})
            max_workers = analysis_params.get("max_concurrent", 5)
        
        logger.info(f"开始并行分析 {len(news_items)} 条新闻，最大并发数: {max_workers}")
        
        results = []
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_news = {
                executor.submit(self.analyze_news, news_item): news_item 
                for news_item in news_items
            }
            
            # 收集结果
            for future in as_completed(future_to_news):
                news_item = future_to_news[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.debug(f"完成分析: {news_item.title[:50]}...")
                except Exception as e:
                    logger.error(f"并行分析失败 [{news_item.title[:50]}...]: {e}")
                    # 跳过失败的新闻，不添加到结果中
                    continue
        
        logger.info(f"并行分析完成，成功处理 {len(results)} 条新闻")
        return results


if __name__ == "__main__":
    # 测试分析功能
    import sys
    
    # 可以通过命令行参数选择API提供商: python ai_analyzer.py [openrouter|deepseek]
    provider = sys.argv[1] if len(sys.argv) > 1 else "openrouter"
    
    if provider not in ["deepseek", "openrouter"]:
        print("支持的API提供商: deepseek, openrouter")
        sys.exit(1)
    
    print(f"使用API提供商: {provider}")
    analyzer = AIAnalyzer(provider=provider)
    news_list = db_manager.get_news_items(limit=5)
    
    if not news_list:
        print("没有找到待分析的新闻")
    else:
        # 使用并行分析
        print(f"开始分析 {len(news_list)} 条新闻")
        results = analyzer.analyze_news_batch(news_list)
        print(f"分析了 {len(results)} 条新闻")

        if results:
            report = analyzer.format_analysis_report(results)
            print(report)
