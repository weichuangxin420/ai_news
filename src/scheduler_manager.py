"""
调度器管理器
提供高级的调度器管理、监控和错误恢复功能
"""

import os
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
import pickle
import yaml

from .scheduler import TaskScheduler
from .utils.logger import get_logger

logger = get_logger('scheduler_manager')


class SchedulerManager:
    """调度器管理器"""
    
    def __init__(self, config_path: str = None, state_file: str = None):
        """
        初始化调度器管理器
        
        Args:
            config_path: 配置文件路径
            state_file: 状态保存文件路径
        """
        self.config_path = config_path
        self.state_file = state_file or 'data/scheduler_state.json'
        self.scheduler = TaskScheduler(config_path)
        
        # 运行状态
        self.is_running = False
        self.start_time = None
        self.error_count = 0
        self.last_error_time = None
        
        # 任务执行历史
        self.execution_history = []
        self.max_history_size = 100
        
        # 健康监控
        self.health_status = {
            'overall': 'unknown',
            'components': {},
            'last_check': None
        }
        
        # 监控线程
        self.monitor_thread = None
        self.monitor_interval = 60  # 监控间隔（秒）
        
    def save_state(self):
        """保存调度器状态"""
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            
            state = {
                'is_running': self.is_running,
                'start_time': self.start_time,
                'error_count': self.error_count,
                'last_error_time': self.last_error_time,
                'execution_history': self.execution_history[-50:],  # 只保存最近50条
                'health_status': self.health_status,
                'saved_at': datetime.now().isoformat()
            }
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
                
            logger.debug("调度器状态已保存")
            
        except Exception as e:
            logger.error(f"保存状态失败: {e}")
    
    def load_state(self):
        """加载调度器状态"""
        try:
            if not os.path.exists(self.state_file):
                logger.info("状态文件不存在，使用默认状态")
                return
            
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            self.error_count = state.get('error_count', 0)
            self.last_error_time = state.get('last_error_time')
            self.execution_history = state.get('execution_history', [])
            self.health_status = state.get('health_status', {
                'overall': 'unknown',
                'components': {},
                'last_check': None
            })
            
            logger.info("调度器状态已加载")
            
        except Exception as e:
            logger.error(f"加载状态失败: {e}")
    
    def start_with_recovery(self, **kwargs):
        """
        启动调度器（包含错误恢复）
        
        Args:
            **kwargs: 传递给scheduler.start()的参数
        """
        try:
            logger.info("启动调度器管理器...")
            
            # 加载状态
            self.load_state()
            
            # 启动调度器
            success = self.scheduler.start(**kwargs)
            
            if success:
                self.is_running = True
                self.start_time = datetime.now().isoformat()
                
                # 启动监控线程
                self.start_monitoring()
                
                # 记录启动事件
                self.record_event('scheduler_started', True, "调度器启动成功")
                
                logger.info("调度器管理器启动成功")
                return True
            else:
                logger.error("调度器启动失败")
                return False
                
        except Exception as e:
            logger.error(f"启动调度器管理器失败: {e}")
            self.error_count += 1
            self.last_error_time = datetime.now().isoformat()
            self.record_event('scheduler_start_failed', False, f"启动失败: {e}")
            return False
    
    def stop_gracefully(self):
        """优雅停止调度器"""
        try:
            logger.info("正在优雅停止调度器...")
            
            # 停止监控
            self.stop_monitoring()
            
            # 停止调度器
            self.scheduler.stop()
            
            self.is_running = False
            
            # 记录停止事件
            self.record_event('scheduler_stopped', True, "调度器正常停止")
            
            # 保存状态
            self.save_state()
            
            logger.info("调度器已优雅停止")
            
        except Exception as e:
            logger.error(f"停止调度器失败: {e}")
    
    def restart_scheduler(self, **kwargs):
        """重启调度器"""
        logger.info("重启调度器...")
        
        self.stop_gracefully()
        time.sleep(2)  # 等待完全停止
        
        return self.start_with_recovery(**kwargs)
    
    def record_event(self, event_type: str, success: bool, message: str):
        """记录事件"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'success': success,
            'message': message
        }
        
        self.execution_history.append(event)
        
        # 限制历史记录数量
        if len(self.execution_history) > self.max_history_size:
            self.execution_history = self.execution_history[-self.max_history_size:]
        
        logger.debug(f"记录事件: {event_type} - {message}")
    
    def start_monitoring(self):
        """启动监控线程"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            return
        
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="SchedulerMonitor"
        )
        self.monitor_thread.start()
        
        logger.info("监控线程已启动")
    
    def stop_monitoring(self):
        """停止监控线程"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            # 监控线程会在下一个循环检查is_running状态
            logger.info("监控线程将在下次检查时停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.is_running:
            try:
                # 执行健康检查
                self.check_health()
                
                # 检查错误恢复
                self.check_error_recovery()
                
                # 保存状态
                self.save_state()
                
                # 等待下次检查
                time.sleep(self.monitor_interval)
                
            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                time.sleep(30)  # 出错时等待更长时间
    
    def check_health(self):
        """健康检查"""
        try:
            logger.debug("执行健康检查...")
            
            # 检查调度器状态
            scheduler_healthy = self.scheduler.is_running
            
            # 检查组件状态
            components_status = {
                'scheduler': scheduler_healthy,
                'news_collector': self.scheduler.news_collector is not None,
                'ai_analyzer': self.scheduler.ai_analyzer is not None,
                'email_sender': self.scheduler.email_sender is not None
            }
            
            # 检查任务执行状态
            scheduler_stats = self.scheduler.get_stats()
            recent_failures = scheduler_stats.get('failed_executions', 0)
            total_executions = scheduler_stats.get('total_executions', 0)
            
            # 计算健康分数
            failure_rate = recent_failures / max(total_executions, 1)
            
            if failure_rate > 0.5:
                overall_status = 'critical'
            elif failure_rate > 0.2:
                overall_status = 'warning'
            elif all(components_status.values()):
                overall_status = 'healthy'
            else:
                overall_status = 'degraded'
            
            self.health_status = {
                'overall': overall_status,
                'components': components_status,
                'last_check': datetime.now().isoformat(),
                'failure_rate': failure_rate,
                'stats': scheduler_stats
            }
            
            # 记录健康状态变化
            if overall_status != 'healthy':
                self.record_event(
                    'health_check',
                    overall_status == 'healthy',
                    f"健康状态: {overall_status}, 失败率: {failure_rate:.2%}"
                )
            
            logger.debug(f"健康检查完成: {overall_status}")
            
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            self.health_status['overall'] = 'error'
    
    def check_error_recovery(self):
        """检查是否需要错误恢复"""
        try:
            # 如果健康状态为critical，考虑重启
            if self.health_status.get('overall') == 'critical':
                logger.warning("检测到严重健康问题，考虑重启调度器")
                
                # 检查最近是否已经重启过
                recent_restarts = [
                    event for event in self.execution_history[-10:]
                    if event.get('type') == 'scheduler_restarted'
                    and datetime.fromisoformat(event['timestamp']) > datetime.now() - timedelta(hours=1)
                ]
                
                if len(recent_restarts) < 3:  # 1小时内最多重启3次
                    logger.info("执行自动恢复重启...")
                    self.restart_scheduler()
                    self.record_event('scheduler_restarted', True, "自动恢复重启")
                else:
                    logger.error("重启次数过多，停止自动恢复")
                    self.record_event('auto_recovery_disabled', False, "重启次数超限")
            
        except Exception as e:
            logger.error(f"错误恢复检查失败: {e}")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表板数据"""
        scheduler_stats = self.scheduler.get_stats()
        
        return {
            'manager_status': {
                'is_running': self.is_running,
                'start_time': self.start_time,
                'uptime': self._calculate_uptime(),
                'error_count': self.error_count,
                'last_error_time': self.last_error_time
            },
            'scheduler_stats': scheduler_stats,
            'health_status': self.health_status,
            'recent_events': self.execution_history[-10:],
            'jobs_info': self._get_jobs_info()
        }
    
    def _calculate_uptime(self) -> Optional[str]:
        """计算运行时间"""
        if not self.start_time:
            return None
        
        start_dt = datetime.fromisoformat(self.start_time)
        uptime = datetime.now() - start_dt
        
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        return f"{days}天 {hours}小时 {minutes}分钟"
    
    def _get_jobs_info(self) -> List[Dict[str, Any]]:
        """获取任务信息"""
        try:
            jobs_info = []
            
            for job in self.scheduler.scheduler.get_jobs():
                jobs_info.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                })
            
            return jobs_info
            
        except Exception as e:
            logger.error(f"获取任务信息失败: {e}")
            return []
    
    def run_with_ui(self):
        """运行调度器并显示状态信息"""
        import time
        
        try:
            logger.info("启动调度器监控模式...")
            
            while self.is_running:
                # 清屏并显示状态
                os.system('cls' if os.name == 'nt' else 'clear')
                
                print("=" * 80)
                print("📊 AI新闻收集与影响分析系统 - 调度器监控")
                print("=" * 80)
                
                dashboard = self.get_dashboard_data()
                
                # 显示管理器状态
                print(f"\n🔧 管理器状态:")
                print(f"  运行状态: {'🟢 运行中' if self.is_running else '🔴 已停止'}")
                print(f"  运行时间: {dashboard['manager_status']['uptime'] or '未知'}")
                print(f"  错误次数: {dashboard['manager_status']['error_count']}")
                
                # 显示健康状态
                health = dashboard['health_status']
                status_emoji = {
                    'healthy': '🟢',
                    'warning': '🟡',
                    'critical': '🔴',
                    'error': '⚫'
                }.get(health.get('overall', 'unknown'), '❓')
                
                print(f"\n💊 健康状态: {status_emoji} {health.get('overall', '未知')}")
                
                # 显示调度器统计
                stats = dashboard['scheduler_stats']
                print(f"\n📈 执行统计:")
                print(f"  总执行次数: {stats.get('total_executions', 0)}")
                print(f"  成功次数: {stats.get('successful_executions', 0)}")
                print(f"  失败次数: {stats.get('failed_executions', 0)}")
                print(f"  上次执行: {stats.get('last_execution_time', '未知')}")
                
                # 显示活动任务
                jobs = dashboard['jobs_info']
                print(f"\n⏰ 活动任务 ({len(jobs)}个):")
                for job in jobs:
                    next_run = job['next_run_time']
                    if next_run:
                        next_run = datetime.fromisoformat(next_run).strftime('%H:%M:%S')
                    print(f"  📋 {job['name']} - 下次执行: {next_run or '未知'}")
                
                # 显示最近事件
                events = dashboard['recent_events']
                print(f"\n📝 最近事件:")
                for event in events[-5:]:
                    timestamp = datetime.fromisoformat(event['timestamp']).strftime('%H:%M:%S')
                    status = '✅' if event['success'] else '❌'
                    print(f"  {timestamp} {status} {event['message']}")
                
                print(f"\n按 Ctrl+C 停止调度器")
                print("=" * 80)
                
                time.sleep(5)  # 每5秒刷新一次
                
        except KeyboardInterrupt:
            print("\n接收到停止信号...")
        finally:
            self.stop_gracefully()


# 便捷函数
def create_scheduler_manager(config_path: str = None) -> SchedulerManager:
    """创建调度器管理器实例"""
    return SchedulerManager(config_path)


if __name__ == "__main__":
    # 测试调度器管理器
    manager = create_scheduler_manager()
    
    try:
        # 启动调度器
        if manager.start_with_recovery(enable_email=False):
            print("调度器管理器启动成功")
            
            # 运行监控界面
            manager.run_with_ui()
        else:
            print("调度器管理器启动失败")
    
    except Exception as e:
        print(f"运行错误: {e}")
    finally:
        manager.stop_gracefully() 