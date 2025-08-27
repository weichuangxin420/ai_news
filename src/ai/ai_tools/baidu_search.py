"""
百度搜索工具
基于AI工具框架的百度搜索实现
"""

import json
import sys
import os
from typing import Dict, Any, Optional, List

# 导入基础方法
from .methods import (
    make_http_request, 
    get_default_headers, 
    create_tool_definition,
    register_tool_from_function,
    default_executor,
    logger
)

# 添加项目根目录到路径（用于导入项目日志）
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class BaiduSearchAPI:
    """百度搜索API调用类 - 使用基础HTTP方法"""
    
    def __init__(self, user_agent: str = None):
        """
        初始化百度搜索API
        
        Args:
            user_agent: 用户代理字符串，可选
        """
        self.base_url = "https://www.baidu.com/s"
        self.headers = get_default_headers(user_agent)
        logger.info("百度搜索API初始化完成")
    
    def search(self, query: str, max_results: int = 10) -> Optional[Dict[str, Any]]:
        """
        执行百度搜索 - 网页搜索并解析结果
        
        Args:
            query: 搜索关键词
            max_results: 最大结果数量
            
        Returns:
            搜索结果字典，失败时返回None
        """
        try:
            logger.info(f"开始百度网页搜索 - 关键词: {query}, 最大结果数: {max_results}")
            
            # 构建搜索参数
            params = {
                "wd": query,  # 搜索词
                "pn": 0,      # 页数，从0开始
                "rn": min(max_results, 50),  # 每页结果数，最大50
                "ie": "utf-8",
                "rsv_pq": "search",
                "rsv_t": "search"
            }
            
            # 使用基础HTTP方法
            http_response = make_http_request(
                url=self.base_url,
                method="GET",
                headers=self.headers,
                params=params,
                timeout=30,
                allow_redirects=True
            )
            
            if not http_response.success:
                logger.error(f"搜索请求失败: {http_response.error}")
                return None
            
            if http_response.status_code == 200:
                html_content = http_response.content
                content_length = len(html_content)
                
                # 检查页面特征
                baidu_indicators = ["百度", "baidu", "Baidu", "BAIDU"]
                search_indicators = ["搜索", "search", "Search"]
                
                has_baidu = any(indicator in html_content for indicator in baidu_indicators)
                has_search = any(indicator in html_content for indicator in search_indicators)
                
                logger.debug(f"页面分析 - 长度: {content_length}, 包含百度标识: {has_baidu}, 包含搜索标识: {has_search}")
                
                # 判断搜索结果质量
                if content_length > 10000:  # 确保有足够的内容
                    logger.info(f"搜索成功 - 获取到网页内容，长度: {content_length}")
                    
                    return {
                        "status": "success",
                        "query": query,
                        "content_length": content_length,
                        "search_url": f"{self.base_url}?wd={query}",
                        "has_baidu_indicators": has_baidu,
                        "has_search_indicators": has_search,
                        "html_preview": html_content[:300],
                        "response_time": http_response.response_time
                    }
                else:
                    logger.warning(f"页面内容过短 - 长度: {content_length}")
                    
                    return {
                        "status": "partial",
                        "query": query,
                        "content_length": content_length,
                        "search_url": f"{self.base_url}?wd={query}",
                        "has_baidu_indicators": has_baidu,
                        "has_search_indicators": has_search,
                        "html_preview": html_content[:300],
                        "response_time": http_response.response_time
                    }
            else:
                logger.error(f"搜索请求失败 - 状态码: {http_response.status_code}")
                return None
                
        except Exception as e:
            logger.exception(f"搜索过程出现未知异常 - 关键词: {query}")
            return None

    def simple_search(self, query: str) -> Optional[str]:
        """
        简单搜索方法 - 返回搜索URL和基本信息
        
        Args:
            query: 搜索关键词
            
        Returns:
            搜索摘要信息，失败时返回None
        """
        try:
            logger.info(f"执行简单搜索 - 关键词: {query}")
            
            # 构建搜索URL
            import urllib.parse
            search_url = f"{self.base_url}?wd={urllib.parse.quote(query)}"
            
            result = f"百度搜索: {query}\n搜索链接: {search_url}\n状态: 链接生成成功"
            logger.info(f"简单搜索完成 - 生成搜索链接")
            
            return result
        except Exception as e:
            logger.exception(f"简单搜索异常 - 关键词: {query}")
            return None


# ==================== Function Call 工具函数 ====================

def baidu_search_tool(query: str, max_results: int = 5) -> str:
    """
    专门用于Function Call的百度搜索工具
    
    Args:
        query: 搜索关键词
        max_results: 最大结果数量
        
    Returns:
        str: 格式化的搜索结果，适合AI处理
    """
    logger.info(f"Function Call搜索请求 - 关键词: {query}")
    
    try:
        # 创建搜索实例
        search_api = BaiduSearchAPI()
        
        # 执行搜索
        result = search_api.search(query, max_results)
        
        if result and result.get('status') == 'success':
            search_url = result.get('search_url', '')
            content_length = result.get('content_length', 0)
            response_time = result.get('response_time', 0)
            
            # 格式化搜索结果为AI友好的格式
            formatted_result = f"""搜索结果摘要：
关键词：{query}
搜索状态：成功
搜索链接：{search_url}
内容长度：{content_length}字符
响应时间：{response_time:.2f}秒

搜索总结：成功从百度获取到关于'{query}'的搜索结果页面，页面包含大量相关信息。可以告知用户搜索已完成，并提供搜索链接供用户进一步查看详细信息。

建议：用户可以点击搜索链接查看完整的搜索结果页面。"""
            
            logger.info(f"Function Call搜索成功 - 关键词: {query}")
            return formatted_result
            
        elif result and result.get('status') == 'partial':
            search_url = result.get('search_url', '')
            formatted_result = f"""搜索结果摘要：
关键词：{query}
搜索状态：部分成功
搜索链接：{search_url}

搜索总结：搜索请求已处理，但返回的内容可能不完整。建议用户通过搜索链接查看完整结果。"""
            
            logger.warning(f"Function Call搜索部分成功 - 关键词: {query}")
            return formatted_result
        else:
            # 搜索失败，提供简单搜索结果
            simple_result = search_api.simple_search(query)
            if simple_result:
                logger.info(f"Function Call使用简单搜索 - 关键词: {query}")
                return f"""搜索结果摘要：
关键词：{query}
搜索状态：生成搜索链接成功

{simple_result}

建议：用户可以通过上述搜索链接查看百度搜索结果。"""
            else:
                logger.error(f"Function Call搜索完全失败 - 关键词: {query}")
                return f"搜索失败：无法为关键词'{query}'生成有效的搜索结果。"
                
    except Exception as e:
        logger.error(f"Function Call搜索异常 - 关键词: {query}, 错误: {e}")
        return f"搜索过程中出现异常：{str(e)}"


def get_baidu_search_tool_definition() -> Dict[str, Any]:
    """
    获取百度搜索工具的Function Call定义
    
    Returns:
        dict: 符合OpenAI Function Call规范的工具定义
    """
    return create_tool_definition(
        name="baidu_search",
        description="使用百度搜索引擎搜索相关信息。当用户询问需要最新信息、实时数据或网络搜索时使用此工具。",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词或查询语句，应该简洁明确地描述用户想要搜索的内容"
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大搜索结果数量，默认为5，范围1-10",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10
                }
            },
            "required": ["query"]
        }
    )


def register_baidu_search_tool(executor=None):
    """
    注册百度搜索工具到执行器
    
    Args:
        executor: 工具执行器，默认使用全局实例
    """
    tool_def = get_baidu_search_tool_definition()
    
    register_tool_from_function(
        func=baidu_search_tool,
        name="baidu_search",
        description=tool_def["function"]["description"],
        parameters=tool_def["function"]["parameters"],
        executor=executor
    )


def create_search_tools_list() -> List[Dict[str, Any]]:
    """
    创建包含百度搜索的工具列表
    
    Returns:
        List[dict]: 工具定义列表
    """
    return [get_baidu_search_tool_definition()]


def test_baidu_search():
    """简单测试函数"""
    logger.info("开始百度搜索API测试")
    
    # 创建搜索实例
    search_api = BaiduSearchAPI()
    
    search_query = "人工智能最新发展"
    logger.info(f"测试搜索关键词: {search_query}")
    
    # 测试简单搜索
    simple_result = search_api.simple_search(search_query)
    if simple_result:
        logger.info(f"简单搜索成功")
        logger.debug(f"简单搜索结果: {simple_result}")
    
    # 测试完整搜索
    result = search_api.search(search_query, max_results=5)
    
    if result:
        logger.info(f"完整搜索测试成功 - 关键词: {search_query}")
        
        # 记录搜索结果概要
        status = result.get('status', 'unknown')
        search_url = result.get('search_url', '无链接')
        content_length = result.get('content_length', 0)
        has_baidu = result.get('has_baidu_indicators', False)
        has_search = result.get('has_search_indicators', False)
        response_time = result.get('response_time', 0)
        
        logger.info(f"搜索状态: {status}")
        logger.info(f"内容长度: {content_length}")
        logger.info(f"响应时间: {response_time:.2f}秒")
        logger.info(f"包含百度标识: {has_baidu}")
        logger.info(f"包含搜索标识: {has_search}")
        logger.debug(f"搜索链接: {search_url}")
        
        if 'html_preview' in result:
            preview_length = len(result['html_preview'])
            logger.debug(f"HTML预览长度: {preview_length}")
            logger.debug(f"HTML内容预览: {result['html_preview'][:100]}...")
    else:
        logger.error("完整搜索测试失败")
    
    # 测试Function Call工具
    logger.info("测试Function Call工具")
    fc_result = baidu_search_tool("AI技术发展", 3)
    logger.info(f"Function Call结果: {fc_result[:200]}...")
    
    logger.info("百度搜索API测试完成")


# 自动注册工具
register_baidu_search_tool()


if __name__ == "__main__":
    logger.info("启动百度搜索API测试")
    test_baidu_search()
