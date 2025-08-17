#!/usr/bin/env python3
"""
AI新闻收集与影响分析系统 - 主程序入口
"""

import os
import sys
import time
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.news_collector import NewsCollector
from src.ai_analyzer import AIAnalyzer, analyze_latest_news
from src.email_sender import EmailSender
from src.scheduler import TaskScheduler
from src.scheduler_manager import SchedulerManager
from src.utils.logger import get_logger
from src.utils.database import db_manager

logger = get_logger('main')


def test_news_collection():
    """测试新闻收集功能"""
    logger.info("=== 开始测试新闻收集功能 ===")
    
    try:
        # 创建新闻收集器
        collector = NewsCollector()
        
        # 收集新闻
        start_time = time.time()
        news_list = collector.collect_all_news()
        end_time = time.time()
        
        # 显示结果
        logger.info(f"收集完成，耗时: {end_time - start_time:.2f} 秒")
        logger.info(f"收集到新闻数量: {len(news_list)}")
        
        # 显示前几条新闻
        if news_list:
            logger.info("=== 最新新闻预览 ===")
            for i, news in enumerate(news_list[:5], 1):
                logger.info(f"{i}. [{news.source}] {news.title[:100]}...")
                logger.info(f"   时间: {news.publish_time}")
                logger.info(f"   分类: {news.category}")
                logger.info(f"   关键词: {', '.join(news.keywords)}")
                logger.info("")
        
        # 显示统计信息
        stats = collector.get_stats()
        logger.info("=== 收集统计信息 ===")
        for key, value in stats.items():
            logger.info(f"{key}: {value}")
        
        # 显示数据库统计
        db_stats = db_manager.get_stats()
        logger.info("=== 数据库统计信息 ===")
        for key, value in db_stats.items():
            logger.info(f"{key}: {value}")
        
        return True
        
    except Exception as e:
        logger.error(f"新闻收集测试失败: {e}")
        logger.exception("详细错误信息:")
        return False


def test_ai_analysis():
    """测试AI分析功能"""
    logger.info("=== 开始测试AI分析功能 ===")
    
    try:
        # 创建AI分析器
        analyzer = AIAnalyzer()
        
        # 获取最新新闻进行分析
        news_list = db_manager.get_news_items(limit=5)
        
        if not news_list:
            logger.info("没有找到待分析的新闻，请先运行新闻收集")
            return False
        
        logger.info(f"准备分析 {len(news_list)} 条新闻")
        
        # 执行分析
        start_time = time.time()
        results = analyzer.batch_analyze(news_list)
        end_time = time.time()
        
        logger.info(f"分析完成，耗时: {end_time - start_time:.2f} 秒")
        logger.info(f"分析结果数量: {len(results)}")
        
        # 显示分析结果
        if results:
            logger.info("=== 分析结果预览 ===")
            for i, result in enumerate(results[:3], 1):
                logger.info(f"{i}. 影响评分: {result.impact_score:.1f} | {result.sentiment}")
                logger.info(f"   影响板块: {', '.join(result.affected_sectors)}")
                logger.info(f"   影响级别: {result.impact_level}")
                logger.info(f"   分析摘要: {result.summary[:100]}...")
                logger.info("")
        
        # 生成分析报告
        report = analyzer.format_analysis_report(results)
        logger.info("=== 分析报告 ===")
        logger.info(report[:500] + "...")
        
        # 显示AI分析器统计信息
        stats = analyzer.get_stats()
        logger.info("=== AI分析统计信息 ===")
        for key, value in stats.items():
            logger.info(f"{key}: {value}")
        
        return True
        
    except Exception as e:
        logger.error(f"AI分析测试失败: {e}")
        logger.exception("详细错误信息:")
        return False


def test_full_pipeline():
    """测试完整流程"""
    logger.info("=== 开始测试完整流程 ===")
    
    try:
        # 1. 收集新闻
        logger.info("步骤1: 收集新闻")
        collector = NewsCollector()
        news_list = collector.collect_all_news()
        logger.info(f"收集到 {len(news_list)} 条新闻")
        
        if not news_list:
            logger.info("没有收集到新闻，跳过分析步骤")
            return False
        
        # 2. AI分析
        logger.info("步骤2: AI分析")
        analyzer = AIAnalyzer()
        results = analyzer.batch_analyze(news_list[:3])  # 分析前3条
        logger.info(f"分析了 {len(results)} 条新闻")
        
        # 3. 生成报告
        logger.info("步骤3: 生成报告")
        if results:
            report = analyzer.format_analysis_report(results)
            
            # 保存报告到文件
            report_file = f"data/analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            os.makedirs(os.path.dirname(report_file), exist_ok=True)
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            logger.info(f"分析报告已保存到: {report_file}")
        
        logger.info("=== 完整流程测试成功 ===")
        return True
        
    except Exception as e:
        logger.error(f"完整流程测试失败: {e}")
        logger.exception("详细错误信息:")
        return False


def test_email_connection():
    """测试邮件连接"""
    logger.info("=== 开始测试邮件连接 ===")
    
    try:
        sender = EmailSender()
        
        # 测试连接
        if sender.test_connection():
            logger.info("✅ SMTP连接测试成功")
            
            # 显示配置信息
            stats = sender.get_stats()
            logger.info("=== 邮件配置信息 ===")
            for key, value in stats.items():
                logger.info(f"{key}: {value}")
            
            return True
        else:
            logger.error("❌ SMTP连接测试失败")
            return False
            
    except Exception as e:
        logger.error(f"邮件连接测试失败: {e}")
        logger.exception("详细错误信息:")
        return False


def test_send_email():
    """测试发送邮件"""
    logger.info("=== 开始测试邮件发送 ===")
    
    try:
        sender = EmailSender()
        
        # 发送测试邮件
        if sender.send_test_email():
            logger.info("✅ 测试邮件发送成功")
            
            # 显示统计信息
            stats = sender.get_stats()
            logger.info("=== 邮件发送统计 ===")
            for key, value in stats.items():
                logger.info(f"{key}: {value}")
            
            return True
        else:
            logger.error("❌ 测试邮件发送失败")
            return False
            
    except Exception as e:
        logger.error(f"测试邮件发送失败: {e}")
        logger.exception("详细错误信息:")
        return False


def test_pipeline_with_email():
    """测试完整流程（包含邮件发送）"""
    logger.info("=== 开始测试完整流程（含邮件）===")
    
    try:
        # 1. 收集新闻
        logger.info("步骤1: 收集新闻")
        collector = NewsCollector()
        news_list = collector.collect_all_news()
        logger.info(f"收集到 {len(news_list)} 条新闻")
        
        if not news_list:
            # 如果没有新闻，从数据库获取
            news_list = db_manager.get_news_items(limit=3)
            logger.info(f"从数据库获取 {len(news_list)} 条新闻进行测试")
        
        if not news_list:
            logger.info("没有新闻数据，跳过后续步骤")
            return False
        
        # 2. AI分析
        logger.info("步骤2: AI分析")
        analyzer = AIAnalyzer()
        results = analyzer.batch_analyze(news_list[:3])  # 分析前3条
        logger.info(f"分析了 {len(results)} 条新闻")
        
        # 3. 发送邮件
        logger.info("步骤3: 发送分析报告邮件")
        sender = EmailSender()
        
        if sender.send_analysis_report(results):
            logger.info("✅ 分析报告邮件发送成功")
        else:
            logger.error("❌ 分析报告邮件发送失败")
            return False
        
        # 4. 生成本地报告
        logger.info("步骤4: 生成本地报告")
        report = analyzer.format_analysis_report(results)
        
        report_file = f"data/full_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"完整报告已保存到: {report_file}")
        logger.info("=== 完整流程（含邮件）测试成功 ===")
        return True
        
    except Exception as e:
        logger.error(f"完整流程（含邮件）测试失败: {e}")
        logger.exception("详细错误信息:")
        return False


def test_scheduler():
    """测试调度器功能"""
    logger.info("=== 开始测试调度器功能 ===")
    
    try:
        scheduler = TaskScheduler()
        
        # 初始化组件
        if not scheduler.initialize_components():
            logger.error("调度器组件初始化失败")
            return False
        
        logger.info("✅ 调度器组件初始化成功")
        
        # 显示配置信息
        stats = scheduler.get_stats()
        logger.info("=== 调度器状态 ===")
        for key, value in stats.items():
            logger.info(f"{key}: {value}")
        
        # 测试单个任务执行
        logger.info("测试单个任务执行...")
        
        # 测试新闻收集任务
        logger.info("测试新闻收集任务...")
        news_count = scheduler._news_collection_task()
        logger.info(f"新闻收集任务完成: {news_count} 条新闻")
        
        # 测试AI分析任务
        logger.info("测试AI分析任务...")
        analysis_count = scheduler._analysis_task()
        logger.info(f"AI分析任务完成: {analysis_count} 条分析")
        
        logger.info("✅ 调度器功能测试成功")
        return True
        
    except Exception as e:
        logger.error(f"调度器功能测试失败: {e}")
        logger.exception("详细错误信息:")
        return False


def start_scheduler_daemon():
    """启动调度器守护进程"""
    logger.info("=== 启动调度器守护进程 ===")
    
    try:
        manager = SchedulerManager()
        
        logger.info("正在启动调度器...")
        
        # 启动调度器（使用完整流程：收集+分析+立即发送邮件）
        if manager.start_with_recovery(
            enable_news_collection=False,  # 关闭独立的新闻收集任务
            enable_analysis=False,         # 关闭独立的分析任务
            enable_email=False,            # 关闭独立的邮件任务
            enable_full_pipeline=True,     # 启用完整流程（每30分钟执行）
            enable_maintenance=True
        ):
            logger.info("✅ 调度器启动成功")
            
            # 显示任务列表
            manager.scheduler.print_jobs()
            
            # 运行监控界面
            logger.info("启动监控界面...")
            manager.run_with_ui()
            
        else:
            logger.error("❌ 调度器启动失败")
            return False
            
    except KeyboardInterrupt:
        logger.info("接收到停止信号")
    except Exception as e:
        logger.error(f"调度器守护进程运行失败: {e}")
        logger.exception("详细错误信息:")
        return False
    finally:
        logger.info("调度器守护进程已停止")


def start_scheduler_background():
    """启动调度器后台运行"""
    logger.info("=== 启动调度器后台运行 ===")
    
    try:
        scheduler = TaskScheduler()
        
        # 启动调度器（使用完整流程：收集+分析+立即发送邮件）
        if scheduler.start(
            enable_news_collection=False,  # 关闭独立的新闻收集任务
            enable_analysis=False,         # 关闭独立的分析任务
            enable_email=False,            # 关闭独立的邮件任务
            enable_full_pipeline=True,     # 启用完整流程（每30分钟执行）
            enable_maintenance=True
        ):
            logger.info("✅ 调度器启动成功，进入后台运行模式")
            
            # 显示任务列表
            scheduler.print_jobs()
            
            # 持续运行
            scheduler.run_forever()
            
        else:
            logger.error("❌ 调度器启动失败")
            return False
            
    except Exception as e:
        logger.error(f"调度器后台运行失败: {e}")
        logger.exception("详细错误信息:")
        return False


def scheduler_status():
    """显示调度器状态"""
    logger.info("=== 调度器状态查询 ===")
    
    try:
        # 尝试从状态文件读取
        state_file = 'data/scheduler_state.json'
        
        if os.path.exists(state_file):
            import json
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            logger.info("=== 调度器状态信息 ===")
            logger.info(f"运行状态: {'运行中' if state.get('is_running') else '已停止'}")
            logger.info(f"启动时间: {state.get('start_time', '未知')}")
            logger.info(f"错误次数: {state.get('error_count', 0)}")
            logger.info(f"健康状态: {state.get('health_status', {}).get('overall', '未知')}")
            
            # 显示最近事件
            events = state.get('execution_history', [])
            if events:
                logger.info("=== 最近事件 ===")
                for event in events[-5:]:
                    timestamp = event.get('timestamp', '')
                    event_type = event.get('type', '')
                    success = '✅' if event.get('success') else '❌'
                    message = event.get('message', '')
                    logger.info(f"{timestamp[:19]} {success} {event_type}: {message}")
        else:
            logger.info("未找到调度器状态文件，调度器可能未运行")
            
    except Exception as e:
        logger.error(f"查询调度器状态失败: {e}")
        return False


def show_recent_news(limit: int = 10):
    """显示最近的新闻"""
    logger.info(f"=== 最近 {limit} 条新闻 ===")
    
    try:
        news_list = db_manager.get_news_items(limit=limit)
        
        if not news_list:
            logger.info("数据库中暂无新闻")
            return
        
        for i, news in enumerate(news_list, 1):
            logger.info(f"{i}. [{news.source}] {news.title}")
            logger.info(f"   时间: {news.publish_time}")
            logger.info(f"   分类: {news.category}")
            if news.keywords:
                logger.info(f"   关键词: {', '.join(news.keywords)}")
            if news.url:
                logger.info(f"   链接: {news.url}")
            logger.info("")
            
    except Exception as e:
        logger.error(f"获取最近新闻失败: {e}")


def show_help():
    """显示帮助信息"""
    help_text = """
AI新闻收集与影响分析系统

用法:
    python main.py [命令]

命令:
    test         - 测试新闻收集功能
    collect      - 执行新闻收集
    analyze      - 测试AI分析功能
    pipeline     - 测试完整流程（收集+分析+报告）
    email-test   - 测试邮件连接
    email-send   - 发送测试邮件
    pipeline-email - 完整流程测试（包含邮件发送）
    scheduler-test - 测试调度器功能
    scheduler-start - 启动调度器守护进程（带监控界面）
    scheduler-run  - 启动调度器后台运行
    scheduler-status - 查看调度器状态
    recent       - 显示最近的新闻
    stats        - 显示统计信息
    help         - 显示此帮助信息

示例:
    python main.py test        # 测试新闻收集
    python main.py collect     # 收集新闻
    python main.py analyze     # 测试AI分析
    python main.py pipeline    # 完整流程测试
    python main.py email-test  # 测试邮件连接
    python main.py email-send  # 发送测试邮件
    python main.py pipeline-email # 完整流程+邮件
    python main.py recent      # 查看最近新闻
"""
    print(help_text)


def main():
    """主函数"""
    # 获取命令行参数
    command = sys.argv[1] if len(sys.argv) > 1 else 'test'
    
    if command == 'help':
        show_help()
    elif command == 'test':
        test_news_collection()
    elif command == 'collect':
        logger.info("执行新闻收集...")
        collector = NewsCollector()
        news_list = collector.collect_all_news()
        logger.info(f"收集完成，共 {len(news_list)} 条新闻")
    elif command == 'analyze':
        test_ai_analysis()
    elif command == 'pipeline':
        test_full_pipeline()
    elif command == 'email-test':
        test_email_connection()
    elif command == 'email-send':
        test_send_email()
    elif command == 'pipeline-email':
        test_pipeline_with_email()
    elif command == 'scheduler-test':
        test_scheduler()
    elif command == 'scheduler-start':
        start_scheduler_daemon()
    elif command == 'scheduler-run':
        start_scheduler_background()
    elif command == 'scheduler-status':
        scheduler_status()
    elif command == 'recent':
        show_recent_news()
    elif command == 'stats':
        db_stats = db_manager.get_stats()
        logger.info("=== 数据库统计信息 ===")
        for key, value in db_stats.items():
            logger.info(f"{key}: {value}")
    else:
        logger.error(f"未知命令: {command}")
        show_help()


if __name__ == "__main__":
    main() 