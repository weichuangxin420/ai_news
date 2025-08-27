"""
AI Function Call 基础方法
提供工具调用的基础功能和管理
"""

import json
import logging
import time
import requests
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass

# 尝试导入项目日志器
try:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from src.utils.logger import get_logger
    logger = get_logger("ai_tools")
except ImportError:
    # 如果无法导入项目日志，使用标准日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("ai_tools")


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time
        }


@dataclass
class HttpResponse:
    """HTTP响应结果"""
    success: bool
    status_code: Optional[int] = None
    content: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    error: Optional[str] = None
    response_time: Optional[float] = None


class ToolExecutor:
    """工具执行器 - 管理和执行Function Call工具"""
    
    def __init__(self):
        """初始化工具执行器"""
        self.tools = {}
        self.execution_history = []
        
    def register_tool(self, name: str, func: Callable, description: str, parameters: Dict[str, Any]):
        """
        注册工具
        
        Args:
            name: 工具名称
            func: 执行函数
            description: 工具描述
            parameters: 参数定义（JSON Schema格式）
        """
        self.tools[name] = {
            "function": func,
            "description": description,
            "parameters": parameters
        }
        logger.info(f"已注册工具: {name}")
    
    def unregister_tool(self, name: str) -> bool:
        """
        取消注册工具
        
        Args:
            name: 工具名称
            
        Returns:
            bool: 是否成功取消注册
        """
        if name in self.tools:
            del self.tools[name]
            logger.info(f"已取消注册工具: {name}")
            return True
        return False
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        获取所有工具的定义（用于API调用）
        
        Returns:
            List[Dict]: 工具定义列表
        """
        definitions = []
        for name, tool in self.tools.items():
            definitions.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }
            })
        return definitions
    
    def get_tool_names(self) -> List[str]:
        """
        获取所有已注册的工具名称
        
        Returns:
            List[str]: 工具名称列表
        """
        return list(self.tools.keys())
    
    def has_tool(self, name: str) -> bool:
        """
        检查是否存在指定工具
        
        Args:
            name: 工具名称
            
        Returns:
            bool: 是否存在
        """
        return name in self.tools
    
    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        """
        执行工具
        
        Args:
            name: 工具名称
            arguments: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        start_time = time.time()
        
        try:
            if name not in self.tools:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"未知工具: {name}",
                    execution_time=time.time() - start_time
                )
            
            tool = self.tools[name]
            func = tool["function"]
            
            logger.info(f"执行工具: {name}, 参数: {arguments}")
            
            # 执行工具函数
            result = func(**arguments)
            
            execution_time = time.time() - start_time
            
            # 记录执行历史
            self.execution_history.append({
                "timestamp": datetime.now().isoformat(),
                "tool_name": name,
                "arguments": arguments,
                "success": True,
                "execution_time": execution_time
            })
            
            logger.info(f"工具执行成功: {name}, 耗时: {execution_time:.2f}秒")
            
            return ToolResult(
                success=True,
                result=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"工具执行失败: {str(e)}"
            
            # 记录执行历史
            self.execution_history.append({
                "timestamp": datetime.now().isoformat(),
                "tool_name": name,
                "arguments": arguments,
                "success": False,
                "error": error_msg,
                "execution_time": execution_time
            })
            
            logger.error(f"{error_msg}, 耗时: {execution_time:.2f}秒")
            
            return ToolResult(
                success=False,
                result=None,
                error=error_msg,
                execution_time=execution_time
            )
    
    def execute_multiple_tools(self, tool_calls: List[Dict[str, Any]]) -> List[ToolResult]:
        """
        批量执行多个工具
        
        Args:
            tool_calls: 工具调用列表，格式: [{"name": "tool_name", "arguments": {...}}, ...]
            
        Returns:
            List[ToolResult]: 执行结果列表
        """
        results = []
        for call in tool_calls:
            name = call.get("name")
            arguments = call.get("arguments", {})
            result = self.execute_tool(name, arguments)
            results.append(result)
        return results
    
    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取执行历史
        
        Args:
            limit: 返回记录数量限制
            
        Returns:
            List[Dict]: 执行历史记录
        """
        return self.execution_history[-limit:]
    
    def clear_history(self):
        """清空执行历史"""
        self.execution_history.clear()
        logger.info("已清空执行历史")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取执行统计信息
        
        Returns:
            Dict: 统计信息
        """
        total_executions = len(self.execution_history)
        successful_executions = sum(1 for h in self.execution_history if h.get("success", False))
        failed_executions = total_executions - successful_executions
        
        avg_execution_time = 0
        if self.execution_history:
            total_time = sum(h.get("execution_time", 0) for h in self.execution_history)
            avg_execution_time = total_time / total_executions
        
        return {
            "total_tools": len(self.tools),
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "success_rate": successful_executions / max(total_executions, 1),
            "avg_execution_time": avg_execution_time
        }


# 全局工具执行器实例
default_executor = ToolExecutor()


def execute_function_call(tool_name: str, arguments: Dict[str, Any], 
                         executor: Optional[ToolExecutor] = None) -> ToolResult:
    """
    执行Function Call
    
    Args:
        tool_name: 工具名称
        arguments: 工具参数
        executor: 工具执行器，默认使用全局实例
        
    Returns:
        ToolResult: 执行结果
    """
    if executor is None:
        executor = default_executor
    
    return executor.execute_tool(tool_name, arguments)


def execute_multiple_function_calls(tool_calls: List[Dict[str, Any]], 
                                   executor: Optional[ToolExecutor] = None) -> List[ToolResult]:
    """
    批量执行多个Function Call
    
    Args:
        tool_calls: 工具调用列表
        executor: 工具执行器，默认使用全局实例
        
    Returns:
        List[ToolResult]: 执行结果列表
    """
    if executor is None:
        executor = default_executor
    
    return executor.execute_multiple_tools(tool_calls)


def format_tool_response(result: ToolResult, include_metadata: bool = True) -> str:
    """
    格式化工具响应结果
    
    Args:
        result: 工具执行结果
        include_metadata: 是否包含元数据（执行时间等）
        
    Returns:
        str: 格式化后的响应字符串
    """
    if include_metadata:
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    else:
        if result.success:
            return json.dumps(result.result, ensure_ascii=False, indent=2)
        else:
            return json.dumps({"error": result.error}, ensure_ascii=False, indent=2)


def format_multiple_tool_responses(results: List[ToolResult], include_metadata: bool = True) -> str:
    """
    格式化多个工具响应结果
    
    Args:
        results: 工具执行结果列表
        include_metadata: 是否包含元数据
        
    Returns:
        str: 格式化后的响应字符串
    """
    formatted_results = []
    for i, result in enumerate(results):
        formatted_results.append({
            "index": i,
            "result": result.to_dict() if include_metadata else (result.result if result.success else {"error": result.error})
        })
    
    return json.dumps(formatted_results, ensure_ascii=False, indent=2)


def create_tool_definition(name: str, description: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    创建工具定义
    
    Args:
        name: 工具名称
        description: 工具描述
        parameters: 参数定义（JSON Schema格式）
        
    Returns:
        Dict: 工具定义
    """
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters
        }
    }


def validate_tool_arguments(parameters: Dict[str, Any], arguments: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    验证工具参数
    
    Args:
        parameters: 工具参数定义
        arguments: 实际参数
        
    Returns:
        tuple: (是否有效, 错误信息)
    """
    try:
        # 检查必需参数
        required = parameters.get("required", [])
        for param in required:
            if param not in arguments:
                return False, f"缺少必需参数: {param}"
        
        # 检查参数类型（简单验证）
        properties = parameters.get("properties", {})
        for param, value in arguments.items():
            if param in properties:
                expected_type = properties[param].get("type")
                if expected_type == "string" and not isinstance(value, str):
                    return False, f"参数 {param} 应为字符串类型"
                elif expected_type == "integer" and not isinstance(value, int):
                    return False, f"参数 {param} 应为整数类型"
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    return False, f"参数 {param} 应为数字类型"
                elif expected_type == "boolean" and not isinstance(value, bool):
                    return False, f"参数 {param} 应为布尔类型"
        
        return True, None
        
    except Exception as e:
        return False, f"参数验证失败: {str(e)}"


# ==================== HTTP请求基础方法 ====================

def make_http_request(url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None,
                     params: Optional[Dict[str, Any]] = None, data: Optional[Any] = None,
                     timeout: int = 30, allow_redirects: bool = True) -> HttpResponse:
    """
    执行HTTP请求的基础方法
    
    Args:
        url: 请求URL
        method: HTTP方法
        headers: 请求头
        params: URL参数
        data: 请求数据
        timeout: 超时时间
        allow_redirects: 是否允许重定向
        
    Returns:
        HttpResponse: HTTP响应结果
    """
    start_time = time.time()
    
    try:
        logger.info(f"发起HTTP请求: {method} {url}")
        
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            data=data,
            timeout=timeout,
            allow_redirects=allow_redirects
        )
        
        response_time = time.time() - start_time
        
        logger.info(f"HTTP请求完成: 状态码={response.status_code}, 耗时={response_time:.2f}秒")
        
        return HttpResponse(
            success=True,
            status_code=response.status_code,
            content=response.text,
            headers=dict(response.headers),
            response_time=response_time
        )
        
    except requests.exceptions.Timeout:
        error_msg = f"HTTP请求超时: {url}"
        logger.error(error_msg)
        return HttpResponse(
            success=False,
            error=error_msg,
            response_time=time.time() - start_time
        )
    except requests.exceptions.ConnectionError:
        error_msg = f"HTTP连接错误: {url}"
        logger.error(error_msg)
        return HttpResponse(
            success=False,
            error=error_msg,
            response_time=time.time() - start_time
        )
    except requests.exceptions.RequestException as e:
        error_msg = f"HTTP请求异常: {str(e)}"
        logger.error(error_msg)
        return HttpResponse(
            success=False,
            error=error_msg,
            response_time=time.time() - start_time
        )
    except Exception as e:
        error_msg = f"HTTP请求未知异常: {str(e)}"
        logger.exception(error_msg)
        return HttpResponse(
            success=False,
            error=error_msg,
            response_time=time.time() - start_time
        )


def get_default_headers(user_agent: Optional[str] = None) -> Dict[str, str]:
    """
    获取默认HTTP请求头
    
    Args:
        user_agent: 用户代理字符串
        
    Returns:
        Dict[str, str]: 默认请求头
    """
    return {
        "User-Agent": user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }


def register_tool_from_function(func: Callable, name: Optional[str] = None,
                               description: Optional[str] = None,
                               parameters: Optional[Dict[str, Any]] = None,
                               executor: Optional[ToolExecutor] = None):
    """
    从函数自动注册工具
    
    Args:
        func: 工具函数
        name: 工具名称，默认使用函数名
        description: 工具描述，默认使用函数文档字符串
        parameters: 参数定义，需要手动提供
        executor: 工具执行器，默认使用全局实例
    """
    if executor is None:
        executor = default_executor
    
    tool_name = name or func.__name__
    tool_description = description or func.__doc__ or f"工具: {tool_name}"
    
    if parameters is None:
        # 如果没有提供参数定义，创建一个基本的定义
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }
        logger.warning(f"工具 {tool_name} 没有提供参数定义，使用默认定义")
    
    executor.register_tool(tool_name, func, tool_description, parameters)


# ==================== OpenAI兼容的Function Call基础方法 ====================

def call_openai_with_tools(client, user_message: str, tools: List[Dict[str, Any]] = None,
                          model: str = "gpt-3.5-turbo", max_tokens: int = 2000,
                          temperature: float = 0.1, system_message: Optional[str] = None,
                          executor: Optional[ToolExecutor] = None) -> str:
    """
    调用OpenAI兼容API并支持Function Call工具调用
    
    Args:
        client: OpenAI客户端实例
        user_message: 用户消息
        tools: 可用的工具列表
        model: 使用的模型
        max_tokens: 最大令牌数
        temperature: 温度参数
        system_message: 系统消息
        executor: 工具执行器，默认使用全局实例
        
    Returns:
        str: API响应结果
    """
    if executor is None:
        executor = default_executor
    
    # 设置默认工具（如果没有提供）
    if tools is None:
        tools = []
        
    try:
        logger.info(f"🔧 准备调用OpenAI兼容API with Function Call")
        logger.info(f"   用户消息: {user_message}")
        logger.info(f"   可用工具数: {len(tools)}")
        logger.info(f"   模型: {model}")
        
        # 构建消息
        messages = []
        if system_message:
            messages.append({
                "role": "system",
                "content": system_message
            })
        else:
            messages.append({
                "role": "system",
                "content": "你是一个智能助手，可以使用提供的工具来帮助用户。当需要搜索信息时，请使用搜索工具获取最新信息。"
            })
        
        messages.append({
            "role": "user", 
            "content": user_message
        })
        
        # 构建API调用参数
        api_params = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        # 如果有工具，添加tools参数
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = "auto"
        
        logger.info(f"📤 开始Function Call API请求...")
        start_time = time.time()
        
        response = client.chat.completions.create(**api_params)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        logger.info(f"📥 Function Call API响应成功")
        logger.info(f"   响应时间: {response_time:.2f}秒")
        
        # 处理响应
        choice = response.choices[0]
        
        # 检查是否有工具调用
        if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
            logger.info(f"🔧 检测到工具调用: {len(choice.message.tool_calls)}个")
            
            # 执行工具调用
            tool_results = []
            for tool_call in choice.message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                logger.info(f"   调用工具: {tool_name}")
                logger.info(f"   工具参数: {tool_args}")
                
                # 使用工具执行器执行工具调用
                tool_result = execute_tool_call_by_name(tool_name, tool_args, executor)
                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": tool_name,
                    "content": str(tool_result)
                })
            
            # 如果有工具调用结果，进行第二次API调用获取最终回答
            if tool_results:
                logger.info(f"🔄 使用工具结果进行第二次API调用...")
                
                # 构建包含工具结果的消息历史
                extended_messages = messages + [choice.message] + tool_results
                
                # 移除tool_calls相关参数，只保留基本参数
                final_api_params = {
                    "model": model,
                    "messages": extended_messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
                
                final_response = client.chat.completions.create(**final_api_params)
                final_content = final_response.choices[0].message.content
                
                logger.info(f"📄 最终响应: {final_content}")
                return final_content
        
        # 没有工具调用，直接返回响应
        response_content = choice.message.content
        logger.info(f"📄 直接响应: {response_content}")
        return response_content
        
    except Exception as e:
        logger.error(f"❌ OpenAI Function Call调用失败: {e}")
        return f"调用失败: {str(e)}"


def execute_tool_call_by_name(tool_name: str, tool_args: Dict[str, Any], 
                             executor: Optional[ToolExecutor] = None) -> str:
    """
    根据工具名称执行工具调用
    
    Args:
        tool_name: 工具名称
        tool_args: 工具参数
        executor: 工具执行器，默认使用全局实例
        
    Returns:
        str: 工具执行结果
    """
    if executor is None:
        executor = default_executor
    
    logger.info(f"🔧 执行工具调用: {tool_name}")
    
    try:
        # 使用工具执行器执行工具
        result = executor.execute_tool(tool_name, tool_args)
        
        if result.success:
            logger.info(f"   工具执行成功: {tool_name}")
            return str(result.result)
        else:
            logger.error(f"   工具执行失败: {result.error}")
            return f"工具执行失败: {result.error}"
            
    except Exception as e:
        logger.error(f"工具执行异常 [{tool_name}]: {e}")
        return f"工具执行异常: {str(e)}"


if __name__ == "__main__":
    # 简单测试
    logger.info("🧪 测试AI工具基础方法")
    
    # 创建测试工具
    def test_tool(message: str) -> str:
        return f"测试工具收到消息: {message}"
    
    # 注册工具
    default_executor.register_tool(
        "test_tool",
        test_tool,
        "测试工具",
        {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "测试消息"}
            },
            "required": ["message"]
        }
    )
    
    # 执行工具
    result = execute_function_call("test_tool", {"message": "Hello World"})
    logger.info(f"执行结果: {format_tool_response(result)}")
    
    # 显示统计信息
    stats = default_executor.get_stats()
    logger.info(f"统计信息: {json.dumps(stats, ensure_ascii=False, indent=2)}")
    
    # 测试HTTP请求
    http_result = make_http_request("https://www.baidu.com", timeout=10)
    logger.info(f"HTTP测试结果: 成功={http_result.success}, 状态码={http_result.status_code}")
    
    # 测试工具调用
    tool_result = execute_tool_call_by_name("test_tool", {"message": "Function Call测试"})
    logger.info(f"工具调用测试结果: {tool_result}") 