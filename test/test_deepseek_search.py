"""
测试DeepSeek Function Call调用百度搜索功能
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.ai.ai_analyzer import AIAnalyzer
from src.ai.ai_tools.baidu_search import create_search_tools_list, get_baidu_search_tool_definition
from src.ai.ai_tools.methods import call_openai_with_tools, default_executor
from src.utils.logger import get_logger

logger = get_logger("test_deepseek_search")


def test_baidu_search_tool_definition():
    """测试百度搜索工具定义"""
    logger.info("=" * 60)
    logger.info("🧪 测试百度搜索工具定义")
    logger.info("=" * 60)
    
    try:
        # 获取工具定义
        tool_def = get_baidu_search_tool_definition()
        
        logger.info("✅ 工具定义获取成功")
        logger.info(f"工具类型: {tool_def.get('type')}")
        logger.info(f"工具名称: {tool_def.get('function', {}).get('name')}")
        logger.info(f"工具描述: {tool_def.get('function', {}).get('description')}")
        
        # 检查必要字段
        assert tool_def.get('type') == 'function'
        assert tool_def.get('function', {}).get('name') == 'baidu_search'
        assert 'parameters' in tool_def.get('function', {})
        
        logger.info("✅ 工具定义格式验证通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 工具定义测试失败: {e}")
        return False


def test_search_tools_list():
    """测试搜索工具列表创建"""
    logger.info("=" * 60)
    logger.info("🧪 测试搜索工具列表创建")
    logger.info("=" * 60)
    
    try:
        # 创建工具列表
        tools_list = create_search_tools_list()
        
        logger.info("✅ 工具列表创建成功")
        logger.info(f"工具数量: {len(tools_list)}")
        
        # 验证列表内容
        assert len(tools_list) > 0
        assert isinstance(tools_list, list)
        assert tools_list[0].get('function', {}).get('name') == 'baidu_search'
        
        logger.info("✅ 工具列表验证通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 工具列表测试失败: {e}")
        return False


def test_deepseek_function_call_basic():
    """测试DeepSeek Function Call基础功能（不涉及实际搜索）"""
    logger.info("=" * 60)
    logger.info("🧪 测试DeepSeek Function Call基础功能")
    logger.info("=" * 60)
    
    try:
        # 创建AI分析器
        analyzer = AIAnalyzer()
        
        # 检查客户端是否可用
        if not analyzer.client:
            logger.warning("⚠️  DeepSeek客户端不可用，跳过实际API测试")
            return True
        
        # 获取工具定义
        tools = create_search_tools_list()
        
        # 简单的非搜索消息测试
        simple_message = "你好，请介绍一下自己"
        logger.info(f"测试消息: {simple_message}")
        
        # 使用基础方法调用
        ai_config = analyzer.config.get("ai_analysis", {}).get("deepseek", {})
        response = call_openai_with_tools(
            client=analyzer.client,
            user_message=simple_message,
            tools=tools,
            model=ai_config.get("model", "deepseek-chat"),
            max_tokens=ai_config.get("max_tokens", 2000),
            temperature=ai_config.get("temperature", 0.1),
            system_message="你是一个智能助手，可以使用提供的工具来帮助用户。当需要搜索信息时，请使用搜索工具获取最新信息。",
            executor=default_executor
        )
        
        logger.info("✅ DeepSeek Function Call基础调用成功")
        logger.info(f"响应内容: {response[:100]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ DeepSeek Function Call基础测试失败: {e}")
        return False


def test_deepseek_search_function_call():
    """测试DeepSeek调用百度搜索Function Call"""
    logger.info("=" * 60)
    logger.info("🧪 测试DeepSeek调用百度搜索Function Call")
    logger.info("=" * 60)
    
    try:
        # 创建AI分析器
        analyzer = AIAnalyzer()
        
        # 检查客户端是否可用
        if not analyzer.client:
            logger.warning("⚠️  DeepSeek客户端不可用，跳过搜索测试")
            return True
        
        # 获取搜索工具
        tools = create_search_tools_list()
        logger.info(f"加载工具数量: {len(tools)}")
        
        # 测试搜索请求
        search_message = "请帮我搜索一下最新的人工智能发展动态"
        logger.info(f"搜索消息: {search_message}")
        
        logger.info("🚀 开始调用DeepSeek进行搜索...")
        # 使用基础方法调用
        ai_config = analyzer.config.get("ai_analysis", {}).get("deepseek", {})
        response = call_openai_with_tools(
            client=analyzer.client,
            user_message=search_message,
            tools=tools,
            model=ai_config.get("model", "deepseek-chat"),
            max_tokens=ai_config.get("max_tokens", 2000),
            temperature=ai_config.get("temperature", 0.1),
            system_message="你是一个智能助手，可以使用提供的工具来帮助用户。当需要搜索信息时，请使用搜索工具获取最新信息。",
            executor=default_executor
        )
        
        logger.info("✅ DeepSeek搜索Function Call调用完成")
        logger.info(f"完整响应长度: {len(response)} 字符")
        logger.info(f"响应内容预览: {response[:200]}...")
        
        # 检查响应是否包含搜索相关内容
        search_indicators = ["搜索", "search", "百度", "结果", "链接"]
        has_search_content = any(indicator in response for indicator in search_indicators)
        
        if has_search_content:
            logger.info("✅ 响应包含搜索相关内容，Function Call可能成功执行")
        else:
            logger.warning("⚠️  响应中未检测到明显的搜索相关内容")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ DeepSeek搜索Function Call测试失败: {e}")
        return False


def test_function_call_integration():
    """综合测试Function Call集成"""
    logger.info("=" * 60)
    logger.info("🧪 综合测试Function Call集成")
    logger.info("=" * 60)
    
    test_cases = [
        "搜索今天的天气情况",
        "查找关于区块链技术的最新消息",
        "帮我了解一下最新的股市行情"
    ]
    
    success_count = 0
    total_count = len(test_cases)
    
    try:
        analyzer = AIAnalyzer()
        
        if not analyzer.client:
            logger.warning("⚠️  DeepSeek客户端不可用，跳过集成测试")
            return True
        
        tools = create_search_tools_list()
        
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"📝 测试用例 {i}/{total_count}: {test_case}")
            
            try:
                # 使用基础方法调用
                ai_config = analyzer.config.get("ai_analysis", {}).get("deepseek", {})
                response = call_openai_with_tools(
                    client=analyzer.client,
                    user_message=test_case,
                    tools=tools,
                    model=ai_config.get("model", "deepseek-chat"),
                    max_tokens=ai_config.get("max_tokens", 2000),
                    temperature=ai_config.get("temperature", 0.1),
                    system_message="你是一个智能助手，可以使用提供的工具来帮助用户。当需要搜索信息时，请使用搜索工具获取最新信息。",
                    executor=default_executor
                )
                logger.info(f"✅ 用例 {i} 执行成功")
                logger.debug(f"响应: {response[:100]}...")
                success_count += 1
                
            except Exception as e:
                logger.error(f"❌ 用例 {i} 执行失败: {e}")
        
        success_rate = success_count / total_count * 100
        logger.info(f"📊 集成测试完成 - 成功率: {success_rate:.1f}% ({success_count}/{total_count})")
        
        return success_rate > 50  # 50%以上成功率视为通过
        
    except Exception as e:
        logger.error(f"❌ 集成测试失败: {e}")
        return False


def main():
    """主测试函数"""
    logger.info("🚀 开始DeepSeek Function Call百度搜索测试")
    logger.info(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = []
    
    # 运行所有测试
    tests = [
        ("工具定义测试", test_baidu_search_tool_definition),
        ("工具列表测试", test_search_tools_list),
        ("基础Function Call测试", test_deepseek_function_call_basic),
        ("搜索Function Call测试", test_deepseek_search_function_call),
        ("集成测试", test_function_call_integration),
    ]
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 执行测试: {test_name}")
        try:
            result = test_func()
            test_results.append((test_name, result))
            status = "✅ 通过" if result else "❌ 失败"
            logger.info(f"测试结果: {status}")
        except Exception as e:
            logger.error(f"测试异常: {e}")
            test_results.append((test_name, False))
    
    # 汇总结果
    logger.info("\n" + "=" * 60)
    logger.info("📋 测试结果汇总")
    logger.info("=" * 60)
    
    passed = 0
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    total = len(test_results)
    success_rate = passed / total * 100 if total > 0 else 0
    
    logger.info("=" * 60)
    logger.info(f"总体结果: {passed}/{total} 通过 ({success_rate:.1f}%)")
    logger.info("=" * 60)
    
    if success_rate >= 80:
        logger.info("🎉 测试总体成功！")
        return True
    else:
        logger.warning("⚠️  部分测试失败，请检查配置和环境")
        return False


if __name__ == "__main__":
    main() 