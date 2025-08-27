"""
AI工具包
提供Function Call相关的基础方法和工具执行器
"""

from .methods import (
    ToolResult,
    ToolExecutor,
    HttpResponse,
    execute_function_call,
    execute_multiple_function_calls,
    format_tool_response,
    format_multiple_tool_responses,
    create_tool_definition,
    validate_tool_arguments,
    make_http_request,
    get_default_headers,
    register_tool_from_function,
    call_openai_with_tools,
    execute_tool_call_by_name,
    default_executor
)

from .baidu_search import (
    BaiduSearchAPI,
    baidu_search_tool,
    get_baidu_search_tool_definition,
    register_baidu_search_tool,
    create_search_tools_list
)

__all__ = [
    # 基础方法
    'ToolResult',
    'ToolExecutor',
    'HttpResponse',
    'execute_function_call',
    'execute_multiple_function_calls',
    'format_tool_response',
    'format_multiple_tool_responses',
    'create_tool_definition',
    'validate_tool_arguments',
    'make_http_request',
    'get_default_headers',
    'register_tool_from_function',
    'call_openai_with_tools',
    'execute_tool_call_by_name',
    'default_executor',
    
    # 百度搜索工具
    'BaiduSearchAPI',
    'baidu_search_tool',
    'get_baidu_search_tool_definition',
    'register_baidu_search_tool',
    'create_search_tools_list'
] 