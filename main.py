#!/usr/bin/env python3
"""
AI新闻收集与影响分析系统 - 主程序入口
提供调度器管理功能
"""

import argparse
import sys
import os

# 添加src路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.logger import get_logger

logger = get_logger("main")


def start_scheduler_daemon():
    """启动调度器守护进程"""
    try:
        from src.scheduler_manager import SchedulerManager
        
        logger.info("启动调度器守护进程...")
        
        manager = SchedulerManager()
        
        # 启用完整流程，禁用独立任务
        manager.start(
            enable_full_pipeline=True,
            enable_analysis=False,
            enable_email=False
        )
        
        logger.info("调度器已启动，按Ctrl+C停止")
        
        try:
            manager.wait()
        except KeyboardInterrupt:
            logger.info("收到停止信号，正在关闭调度器...")
            manager.stop()
            logger.info("调度器已停止")
            
    except Exception as e:
        logger.error(f"启动调度器失败: {e}")


def start_scheduler_background():
    """后台启动调度器"""
    try:
        from src.scheduler_manager import SchedulerManager
        
        logger.info("后台启动调度器...")
        
        manager = SchedulerManager()
        
        # 启用完整流程，禁用独立任务
        manager.start(
            enable_full_pipeline=True,
            enable_analysis=False,
            enable_email=False,
            daemon=True
        )
        
        logger.info("调度器已在后台启动")
        
    except Exception as e:
        logger.error(f"后台启动调度器失败: {e}")


def scheduler_status():
    """查看调度器状态"""
    try:
        from src.scheduler_manager import SchedulerManager
        
        manager = SchedulerManager()
        status = manager.get_status()
        
        print("📊 调度器状态:")
        print(f"   运行状态: {status.get('running', 'Unknown')}")
        print(f"   启动时间: {status.get('start_time', 'N/A')}")
        print(f"   任务数量: {status.get('job_count', 0)}")
        
        jobs = status.get('jobs', [])
        if jobs:
            print("   活动任务:")
            for job in jobs:
                print(f"     - {job}")
        
    except Exception as e:
        logger.error(f"获取调度器状态失败: {e}")


def run_single_pipeline():
    """手动运行一次完整流程"""
    try:
        from src.news_collector import NewsCollector
        from src.ai_analyzer import AIAnalyzer
        from src.email_sender import EmailSender
        from src.utils.database import db_manager
        
        logger.info("开始手动执行完整流程...")
        
        # 1. 新闻收集
        logger.info("1️⃣ 执行新闻收集...")
        collector = NewsCollector()
        news_list = collector.collect_all_news()
        logger.info(f"收集到 {len(news_list)} 条新闻")
        
        if not news_list:
            logger.warning("没有收集到新新闻，流程结束")
            return
        
        # 2. AI分析
        logger.info("2️⃣ 执行AI分析...")
        analyzer = AIAnalyzer()
        analysis_results = analyzer.analyze_news_batch(news_list)
        logger.info(f"分析了 {len(analysis_results)} 条新闻")
        
        # 3. 发送邮件
        if analysis_results:
            logger.info("3️⃣ 发送分析报告...")
            sender = EmailSender()
            success = sender.send_analysis_report(analysis_results)
            
            if success:
                logger.info("✅ 完整流程执行成功")
            else:
                logger.warning("⚠️  邮件发送失败，但分析已完成")
        else:
            logger.warning("没有分析结果，跳过邮件发送")
            
    except Exception as e:
        logger.error(f"执行完整流程失败: {e}")


def show_help():
    """显示帮助信息"""
    print("""
🤖 AI新闻收集与影响分析系统

📋 可用命令:
   start        - 启动调度器守护进程（前台运行）
   background   - 后台启动调度器
   status       - 查看调度器状态
   run-once     - 手动执行一次完整流程
   help         - 显示此帮助信息

📁 测试功能:
   请使用 main_test.py 运行系统测试
   
   python main_test.py --help           # 查看测试帮助
   python main_test.py                  # 运行所有测试
   python main_test.py --module api     # 只测试API

📊 使用示例:
   python main.py start                 # 启动定时收集（前台）
   python main.py background            # 启动定时收集（后台）
   python main.py run-once              # 手动执行一次
   python main.py status                # 查看状态
    """)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="AI新闻收集与影响分析系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py start       # 启动调度器（前台运行）
  python main.py background  # 后台启动调度器
  python main.py status      # 查看调度器状态
  python main.py run-once    # 手动执行一次完整流程
  
测试功能请使用:
  python main_test.py        # 运行系统测试
        """
    )
    
    parser.add_argument(
        "command", 
        choices=["start", "background", "status", "run-once", "help"],
        help="要执行的命令"
    )
    
    args = parser.parse_args()
    
    if args.command == "start":
        start_scheduler_daemon()
    elif args.command == "background":
        start_scheduler_background()
    elif args.command == "status":
        scheduler_status()
    elif args.command == "run-once":
        run_single_pipeline()
    elif args.command == "help":
        show_help()


if __name__ == "__main__":
    main() 