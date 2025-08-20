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
        from src.scheduler import TaskScheduler
        
        logger.info("启动调度器守护进程...")
        
        manager = TaskScheduler()
        
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
        from src.scheduler import TaskScheduler
        
        logger.info("后台启动调度器...")
        
        manager = TaskScheduler()
        
        # 启用增强版调度策略
        manager.start(
            enable_enhanced_strategy=True,
            enable_full_pipeline=False,
            enable_analysis=False,
            enable_email=False
        )
        
        logger.info("调度器已在后台启动")
        
        # 保持进程运行
        try:
            manager.wait()
        except KeyboardInterrupt:
            logger.info("收到停止信号，正在关闭调度器...")
            manager.stop()
            logger.info("调度器已停止")
        
    except Exception as e:
        logger.error(f"后台启动调度器失败: {e}")


def scheduler_status():
    """查看调度器状态"""
    try:
        from src.scheduler import TaskScheduler
        import psutil
        import json
        import os
        
        # 创建临时实例来访问状态文件
        temp_manager = TaskScheduler()
        
        # 方法1：检查状态文件
        status_from_file = {}
        state_file = temp_manager.state_file
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                    status_from_file = {
                        'file_running': state_data.get('is_running', False),
                        'start_time': state_data.get('start_time', 'N/A'),
                        'error_count': state_data.get('error_count', 0),
                        'last_saved': state_data.get('saved_at', 'N/A'),
                        'process_id': state_data.get('process_id'),
                        'next_execution': state_data.get('stats', {}).get('next_execution_time', 'N/A')
                    }
                    
                    # 检查进程ID是否仍在运行
                    if status_from_file['process_id']:
                        try:
                            process = psutil.Process(status_from_file['process_id'])
                            if process.is_running():
                                status_from_file['pid_running'] = True
                                status_from_file['pid_cmdline'] = ' '.join(process.cmdline())
                            else:
                                status_from_file['pid_running'] = False
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            status_from_file['pid_running'] = False
                    else:
                        status_from_file['pid_running'] = False
                        
            except Exception as e:
                logger.warning(f"读取状态文件失败: {e}")
        
        # 方法2：检查运行中的进程
        python_processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if (cmdline and 
                        any('python' in str(cmd).lower() for cmd in cmdline) and
                        any('main.py' in str(cmd) for cmd in cmdline) and
                        any(cmd in ['start', 'daemon', 'background'] for cmd in cmdline)):
                        
                        python_processes.append({
                            'pid': proc.info['pid'],
                            'cmdline': ' '.join(cmdline),
                            'running_time': proc.info.get('create_time', 0)
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.warning(f"进程检查失败: {e}")
        
        # 显示状态信息
        print("📊 调度器状态检查:")
        print("=" * 50)
        
        # 状态文件信息
        if status_from_file:
            print("📁 状态文件信息:")
            print(f"   文件状态: {'🟢 运行中' if status_from_file['file_running'] else '🔴 已停止'}")
            print(f"   启动时间: {status_from_file['start_time']}")
            print(f"   进程ID: {status_from_file.get('process_id', 'N/A')}")
            
            # 进程ID检查结果
            if status_from_file.get('process_id'):
                if status_from_file.get('pid_running'):
                    print(f"   进程状态: 🟢 运行中")
                    print(f"   进程命令: {status_from_file.get('pid_cmdline', 'N/A')}")
                else:
                    print(f"   进程状态: 🔴 已退出")
            
            print(f"   错误计数: {status_from_file['error_count']}")
            print(f"   下次执行: {status_from_file.get('next_execution', 'N/A')}")
            print(f"   最后保存: {status_from_file['last_saved']}")
        else:
            print("📁 状态文件: ❌ 不存在或无法读取")
        
        print()
        
        # 进程信息
        if python_processes:
            print("🔄 运行中的调度器进程:")
            for proc in python_processes:
                import datetime
                create_time = datetime.datetime.fromtimestamp(proc['running_time'])
                print(f"   PID: {proc['pid']}")
                print(f"   命令: {proc['cmdline']}")
                print(f"   启动时间: {create_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print()
        else:
            print("🔄 进程检查: ❌ 未发现运行中的调度器进程")
        
        # 综合判断
        file_indicates_running = status_from_file.get('file_running', False) and status_from_file.get('pid_running', False)
        process_found = bool(python_processes)
        is_likely_running = file_indicates_running or process_found
        
        if file_indicates_running and process_found:
            overall_status = "🟢 确认运行中"
        elif file_indicates_running or process_found:
            overall_status = "🟡 可能运行中"
        else:
            overall_status = "🔴 未运行"
            
        print(f"🎯 综合状态: {overall_status}")
        
        # 获取任务信息（如果可能）
        if status_from_file.get('file_running'):
            try:
                # 尝试加载状态并获取任务信息
                temp_manager.load_state()
                recent_events = temp_manager.execution_history[-3:]
                if recent_events:
                    print("\n📝 最近事件:")
                    for event in recent_events:
                        timestamp = event['timestamp'][:19].replace('T', ' ')
                        status_icon = '✅' if event['success'] else '❌'
                        print(f"   {timestamp} {status_icon} {event['message']}")
            except Exception as e:
                logger.debug(f"获取历史事件失败: {e}")
        
        # 提供操作建议
        print("\n💡 操作建议:")
        if not is_likely_running:
            print("   启动调度器: python main.py start")
            print("   后台启动: python main.py background")
        else:
            print("   查看日志: tail -f data/logs/app.log")
            print("   停止进程: kill <PID>")
        
    except Exception as e:
        logger.error(f"获取调度器状态失败: {e}")
        print("❌ 状态检查失败，请检查系统配置")


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