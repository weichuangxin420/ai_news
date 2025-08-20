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
        
        # 启用增强版调度策略
        manager.start(
            enable_enhanced_strategy=True,
            enable_full_pipeline=False,
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
        
        # 启用增强版调度策略
        manager.start(
            enable_enhanced_strategy=True,
            enable_full_pipeline=False,
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
        from src.scheduler import TaskScheduler
        
        logger.info("开始手动执行增强版完整流程...")
        
        # 使用增强版调度器的收集和分析功能
        scheduler = TaskScheduler()
        scheduler.initialize_components()
        
        # 执行收集和分析
        news_list = scheduler.collect_and_analyze_news()
        
        if news_list:
            logger.info(f"✅ 增强版流程执行成功，处理了 {len(news_list)} 条新闻")
            # 显示一些统计信息
            high_importance = len([n for n in news_list if n.importance_score >= 70])
            medium_importance = len([n for n in news_list if 40 <= n.importance_score < 70])
            low_importance = len([n for n in news_list if n.importance_score < 40])
            
            print(f"📊 重要性分布:")
            print(f"  🔴 高重要性: {high_importance} 条")
            print(f"  🟡 中等重要性: {medium_importance} 条")
            print(f"  🟢 低重要性: {low_importance} 条")
        else:
            logger.warning("没有收集到新新闻")
            
    except Exception as e:
        logger.error(f"执行增强版流程失败: {e}")


def run_enhanced_pipeline():
    """运行增强版流程（带重要性分析）"""
    try:
        from src.scheduler import TaskScheduler
        
        logger.info("开始执行增强版新闻收集和分析...")
        
        scheduler = TaskScheduler()
        scheduler.initialize_components()
        
        # 收集并分析新闻
        news_list = scheduler.collect_and_analyze_news()
        
        if news_list:
            # 按重要性排序
            sorted_news = sorted(news_list, key=lambda x: x.importance_score, reverse=True)
            
            logger.info(f"✅ 处理了 {len(news_list)} 条新闻")
            
            # 显示前5条重要新闻
            print("\n📰 重要新闻预览:")
            for i, news in enumerate(sorted_news[:5], 1):
                print(f"{i}. [{news.importance_score}分] {news.title[:50]}...")
                
            # 发送测试邮件
            scheduler._send_instant_email(news_list[:5], "测试报告")
            
        else:
            logger.warning("没有收集到新新闻")
            
    except Exception as e:
        logger.error(f"执行增强版流程失败: {e}")


def send_daily_summary():
    """手动发送每日汇总"""
    try:
        from src.scheduler import TaskScheduler
        
        logger.info("开始生成每日汇总...")
        
        scheduler = TaskScheduler()
        scheduler.initialize_components()
        
        # 执行每日汇总任务
        scheduler._daily_summary_email()
        
    except Exception as e:
        logger.error(f"发送每日汇总失败: {e}")


def show_help():
    """显示帮助信息"""
    print("""
🤖 AI新闻收集与影响分析系统

📋 可用命令:
   start        - 启动增强版调度器守护进程（前台运行）
   background   - 后台启动增强版调度器
   status       - 查看调度器状态
   run-once     - 手动执行一次完整流程（带重要性分析）
   enhanced     - 运行增强版流程并发送测试邮件
   summary      - 手动发送今日汇总邮件
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
  python main.py daemon      # 守护进程模式（适合容器）
  python main.py status      # 查看调度器状态
  python main.py run-once    # 手动执行一次完整流程
  
测试功能请使用:
  python main_test.py        # 运行系统测试
        """
    )
    
    parser.add_argument(
        "command", 
        choices=["start", "background", "daemon", "status", "run-once", "enhanced", "summary", "help"],
        help="要执行的命令"
    )
    
    args = parser.parse_args()
    
    if args.command == "start":
        start_scheduler_daemon()
    elif args.command == "background":
        start_scheduler_background()
    elif args.command == "daemon":
        start_scheduler_daemon()  # daemon和start功能相同，适合容器环境
    elif args.command == "status":
        scheduler_status()
    elif args.command == "run-once":
        run_single_pipeline()
    elif args.command == "enhanced":
        run_enhanced_pipeline()
    elif args.command == "summary":
        send_daily_summary()
    elif args.command == "help":
        show_help()


if __name__ == "__main__":
    main() 