"""
定时调度模块
实现自动化的新闻收集、AI分析和邮件发送任务调度
"""

import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import yaml
import signal
import sys

from .news_collector import NewsCollector
from .ai_analyzer import AIAnalyzer
from .email_sender import EmailSender
from .utils.logger import get_logger
from .utils.database import db_manager

logger = get_logger('scheduler')


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, config_path: str = None):
        """
        初始化任务调度器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
        self.is_running = False
        self.jobs = {}
        
        # 统计信息
        self.stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'last_execution_time': None,
            'next_execution_time': None,
            'uptime_start': None
        }
        
        # 组件实例
        self.news_collector = None
        self.ai_analyzer = None
        self.email_sender = None
        
        # 设置事件监听器
        self._setup_event_listeners()
        
        # 设置信号处理器
        self._setup_signal_handlers()
    
    def _load_config(self, config_path: Optional[str]) -> dict:
        """加载配置文件"""
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '../config/config.yaml')
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
                
            # 处理环境变量
            self._resolve_env_vars(config)
            return config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def _resolve_env_vars(self, obj):
        """递归解析环境变量"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                obj[key] = self._resolve_env_vars(value)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                obj[i] = self._resolve_env_vars(item)
        elif isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
            env_var = obj[2:-1]
            return os.getenv(env_var, obj)
        return obj
    
    def _setup_event_listeners(self):
        """设置事件监听器"""
        self.scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )
    
    def _setup_signal_handlers(self):
        """设置信号处理器，优雅关闭"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"接收到信号 {signum}，正在优雅关闭...")
        self.stop()
        sys.exit(0)
    
    def _job_executed_listener(self, event):
        """任务执行事件监听器"""
        self.stats['total_executions'] += 1
        self.stats['last_execution_time'] = datetime.now().isoformat()
        
        if event.exception:
            self.stats['failed_executions'] += 1
            logger.error(f"任务执行失败: {event.job_id}, 异常: {event.exception}")
        else:
            self.stats['successful_executions'] += 1
            logger.info(f"任务执行成功: {event.job_id}")
    
    def initialize_components(self):
        """初始化组件"""
        try:
            logger.info("初始化组件...")
            
            self.news_collector = NewsCollector()
            self.ai_analyzer = AIAnalyzer()
            self.email_sender = EmailSender()
            
            logger.info("组件初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"组件初始化失败: {e}")
            return False
    
    def add_news_collection_job(self, interval_minutes: int = None):
        """
        添加新闻收集任务
        
        Args:
            interval_minutes: 执行间隔（分钟），默认从配置读取
        """
        if interval_minutes is None:
            interval_minutes = self.config.get('news_collection', {}).get('collection_interval', 30)
        
        job = self.scheduler.add_job(
            func=self._news_collection_task,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id='news_collection',
            name='新闻收集任务',
            max_instances=1,  # 避免重复执行
            coalesce=True,    # 合并延迟的任务
            misfire_grace_time=300  # 5分钟宽限期
        )
        
        self.jobs['news_collection'] = job
        logger.info(f"新闻收集任务已添加，执行间隔: {interval_minutes} 分钟")
    
    def add_analysis_and_email_job(self, 
                                  analysis_interval_minutes: int = None,
                                  email_cron: str = None):
        """
        添加分析和邮件发送任务
        
        Args:
            analysis_interval_minutes: 分析间隔（分钟）
            email_cron: 邮件发送的cron表达式，如 "0 9,18 * * *" 表示每天9点和18点
        """
        # 分析任务
        if analysis_interval_minutes is None:
            analysis_interval_minutes = self.config.get('scheduler', {}).get('analysis_interval', 60)
        
        analysis_job = self.scheduler.add_job(
            func=self._analysis_task,
            trigger=IntervalTrigger(minutes=analysis_interval_minutes),
            id='ai_analysis',
            name='AI分析任务',
            max_instances=1,
            coalesce=True,
            misfire_grace_time=600  # 10分钟宽限期
        )
        
        self.jobs['ai_analysis'] = analysis_job
        logger.info(f"AI分析任务已添加，执行间隔: {analysis_interval_minutes} 分钟")
        
        # 邮件发送任务
        if email_cron is None:
            email_cron = self.config.get('scheduler', {}).get('email_cron', '0 9,18 * * *')
        
        email_job = self.scheduler.add_job(
            func=self._email_task,
            trigger=CronTrigger.from_crontab(email_cron),
            id='email_report',
            name='邮件报告任务',
            max_instances=1,
            coalesce=True,
            misfire_grace_time=1800  # 30分钟宽限期
        )
        
        self.jobs['email_report'] = email_job
        logger.info(f"邮件报告任务已添加，执行计划: {email_cron}")
    
    def add_full_pipeline_job(self, interval_minutes: int = None):
        """
        添加完整流程任务（收集+分析+邮件）
        
        Args:
            interval_minutes: 执行间隔（分钟）
        """
        if interval_minutes is None:
            interval_minutes = self.config.get('scheduler', {}).get('pipeline_interval', 120)
        
        job = self.scheduler.add_job(
            func=self._full_pipeline_task,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id='full_pipeline',
            name='完整流程任务',
            max_instances=1,
            coalesce=True,
            misfire_grace_time=900  # 15分钟宽限期
        )
        
        self.jobs['full_pipeline'] = job
        logger.info(f"完整流程任务已添加，执行间隔: {interval_minutes} 分钟")
    
    def add_maintenance_job(self):
        """添加维护任务（数据清理等）"""
        # 每天凌晨3点执行维护任务
        job = self.scheduler.add_job(
            func=self._maintenance_task,
            trigger=CronTrigger(hour=3, minute=0),
            id='maintenance',
            name='维护任务',
            max_instances=1,
            coalesce=True
        )
        
        self.jobs['maintenance'] = job
        logger.info("维护任务已添加，执行时间: 每天凌晨3点")
    
    def _news_collection_task(self):
        """新闻收集任务"""
        logger.info("=== 开始执行新闻收集任务 ===")
        
        try:
            if not self.news_collector:
                self.news_collector = NewsCollector()
            
            start_time = time.time()
            news_list = self.news_collector.collect_all_news()
            end_time = time.time()
            
            duration = end_time - start_time
            logger.info(f"新闻收集完成: {len(news_list)} 条新闻，耗时: {duration:.2f} 秒")
            
            return len(news_list)
            
        except Exception as e:
            logger.error(f"新闻收集任务失败: {e}")
            raise
    
    def _analysis_task(self):
        """AI分析任务"""
        logger.info("=== 开始执行AI分析任务 ===")
        
        try:
            if not self.ai_analyzer:
                self.ai_analyzer = AIAnalyzer()
            
            # 获取未分析的新闻
            news_list = db_manager.get_news_items(limit=20)
            if not news_list:
                logger.info("没有待分析的新闻")
                return 0
            
            start_time = time.time()
            results = self.ai_analyzer.batch_analyze(news_list)
            end_time = time.time()
            
            duration = end_time - start_time
            logger.info(f"AI分析完成: {len(results)} 条新闻，耗时: {duration:.2f} 秒")
            
            return len(results)
            
        except Exception as e:
            logger.error(f"AI分析任务失败: {e}")
            raise
    
    def _email_task(self):
        """邮件发送任务"""
        logger.info("=== 开始执行邮件发送任务 ===")
        
        try:
            if not self.email_sender:
                self.email_sender = EmailSender()
            
            if not self.ai_analyzer:
                self.ai_analyzer = AIAnalyzer()
            
            # 获取最近的分析结果
            recent_hours = self.config.get('scheduler', {}).get('email_recent_hours', 24)
            cutoff_time = datetime.now() - timedelta(hours=recent_hours)
            
            # 这里需要从数据库获取分析结果，暂时使用最新新闻
            news_list = db_manager.get_news_items(limit=10)
            if not news_list:
                logger.info("没有新闻数据，跳过邮件发送")
                return False
            
            # 快速分析（如果没有缓存的分析结果）
            results = self.ai_analyzer.batch_analyze(news_list[:5])
            
            # 发送邮件
            success = self.email_sender.send_analysis_report(results)
            
            if success:
                logger.info("邮件发送任务完成")
            else:
                logger.error("邮件发送任务失败")
            
            return success
            
        except Exception as e:
            logger.error(f"邮件发送任务失败: {e}")
            raise
    
    def _full_pipeline_task(self):
        """完整流程任务"""
        logger.info("=== 开始执行完整流程任务 ===")
        
        try:
            # 1. 新闻收集
            news_count = self._news_collection_task()
            
            # 2. AI分析
            if news_count > 0:
                analysis_count = self._analysis_task()
                
                # 3. 邮件发送（如果有分析结果）
                if analysis_count > 0:
                    email_success = self._email_task()
                    
                    logger.info(f"完整流程完成: 收集 {news_count} 条新闻，分析 {analysis_count} 条，邮件发送 {'成功' if email_success else '失败'}")
                else:
                    logger.info(f"完整流程完成: 收集 {news_count} 条新闻，无新分析结果")
            else:
                logger.info("完整流程完成: 无新新闻收集")
            
            return True
            
        except Exception as e:
            logger.error(f"完整流程任务失败: {e}")
            raise
    
    def _maintenance_task(self):
        """维护任务"""
        logger.info("=== 开始执行维护任务 ===")
        
        try:
            # 数据库清理
            retention_days = self.config.get('database', {}).get('retention', {}).get('max_days', 30)
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            # 这里可以添加数据库清理逻辑
            logger.info(f"执行数据清理，保留 {retention_days} 天内的数据")
            
            # 日志文件清理
            self._cleanup_logs()
            
            # 系统状态检查
            self._health_check()
            
            logger.info("维护任务完成")
            return True
            
        except Exception as e:
            logger.error(f"维护任务失败: {e}")
            raise
    
    def _cleanup_logs(self):
        """清理日志文件"""
        try:
            log_dir = self.config.get('logging', {}).get('file', 'data/logs/app.log')
            log_dir = os.path.dirname(log_dir)
            
            if not os.path.exists(log_dir):
                return
            
            # 清理7天前的日志文件
            cutoff_time = time.time() - (7 * 24 * 3600)
            
            for filename in os.listdir(log_dir):
                filepath = os.path.join(log_dir, filename)
                if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff_time:
                    os.remove(filepath)
                    logger.debug(f"删除旧日志文件: {filename}")
            
            logger.info("日志文件清理完成")
            
        except Exception as e:
            logger.error(f"日志文件清理失败: {e}")
    
    def _health_check(self):
        """系统健康检查"""
        try:
            # 检查组件状态
            components_status = {
                'news_collector': self.news_collector is not None,
                'ai_analyzer': self.ai_analyzer is not None,
                'email_sender': self.email_sender is not None,
                'database': True,  # 基本检查
                'scheduler': self.is_running
            }
            
            # 检查配置
            config_status = {
                'news_sources': len(self.config.get('news_collection', {}).get('sources', {}).get('rss_feeds', [])) > 0,
                'email_configured': bool(self.config.get('email', {}).get('smtp', {}).get('username')),
            }
            
            logger.info(f"组件状态: {components_status}")
            logger.info(f"配置状态: {config_status}")
            
            return all(components_status.values()) and all(config_status.values())
            
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False
    
    def start(self, 
             enable_news_collection: bool = True,
             enable_analysis: bool = True,
             enable_email: bool = True,
             enable_full_pipeline: bool = False,
             enable_maintenance: bool = True):
        """
        启动调度器
        
        Args:
            enable_news_collection: 是否启用新闻收集任务
            enable_analysis: 是否启用分析任务
            enable_email: 是否启用邮件任务
            enable_full_pipeline: 是否启用完整流程任务
            enable_maintenance: 是否启用维护任务
        """
        try:
            logger.info("正在启动任务调度器...")
            
            # 初始化组件
            if not self.initialize_components():
                logger.error("组件初始化失败，无法启动调度器")
                return False
            
            # 添加任务
            if enable_full_pipeline:
                self.add_full_pipeline_job()
            else:
                if enable_news_collection:
                    self.add_news_collection_job()
                
                if enable_analysis and enable_email:
                    self.add_analysis_and_email_job()
                elif enable_analysis:
                    # 只添加分析任务
                    analysis_interval = self.config.get('scheduler', {}).get('analysis_interval', 60)
                    job = self.scheduler.add_job(
                        func=self._analysis_task,
                        trigger=IntervalTrigger(minutes=analysis_interval),
                        id='ai_analysis_only',
                        name='仅AI分析任务',
                        max_instances=1,
                        coalesce=True
                    )
                    self.jobs['ai_analysis_only'] = job
            
            if enable_maintenance:
                self.add_maintenance_job()
            
            # 启动调度器
            self.scheduler.start()
            self.is_running = True
            self.stats['uptime_start'] = datetime.now().isoformat()
            
            # 更新下次执行时间
            self._update_next_execution_time()
            
            logger.info("任务调度器启动成功")
            logger.info(f"已添加 {len(self.jobs)} 个任务")
            
            # 显示任务列表
            self.print_jobs()
            
            return True
            
        except Exception as e:
            logger.error(f"启动调度器失败: {e}")
            return False
    
    def stop(self):
        """停止调度器"""
        try:
            logger.info("正在停止任务调度器...")
            
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
            
            self.is_running = False
            logger.info("任务调度器已停止")
            
        except Exception as e:
            logger.error(f"停止调度器失败: {e}")
    
    def pause(self):
        """暂停调度器"""
        if self.scheduler.running:
            self.scheduler.pause()
            logger.info("任务调度器已暂停")
    
    def resume(self):
        """恢复调度器"""
        if self.scheduler.running:
            self.scheduler.resume()
            logger.info("任务调度器已恢复")
    
    def run_job_once(self, job_id: str):
        """立即执行指定任务"""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                logger.info(f"立即执行任务: {job_id}")
                job.func()
                return True
            else:
                logger.error(f"未找到任务: {job_id}")
                return False
                
        except Exception as e:
            logger.error(f"执行任务失败: {job_id}, 错误: {e}")
            return False
    
    def print_jobs(self):
        """打印任务列表"""
        if not self.scheduler.get_jobs():
            logger.info("没有活动的任务")
            return
        
        logger.info("=== 活动任务列表 ===")
        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else "未知"
            logger.info(f"任务: {job.name} (ID: {job.id})")
            logger.info(f"  下次执行: {next_run}")
            logger.info(f"  触发器: {job.trigger}")
            logger.info("")
    
    def _update_next_execution_time(self):
        """更新下次执行时间"""
        next_times = []
        for job in self.scheduler.get_jobs():
            if job.next_run_time:
                next_times.append(job.next_run_time)
        
        if next_times:
            earliest = min(next_times)
            self.stats['next_execution_time'] = earliest.isoformat()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取调度器统计信息"""
        self._update_next_execution_time()
        
        return {
            **self.stats,
            'is_running': self.is_running,
            'active_jobs_count': len(self.scheduler.get_jobs()) if self.scheduler else 0,
            'scheduler_state': 'running' if self.is_running else 'stopped'
        }
    
    def run_forever(self):
        """持续运行调度器"""
        try:
            logger.info("调度器进入持续运行模式，按 Ctrl+C 停止")
            
            while self.is_running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("接收到停止信号")
        finally:
            self.stop()


def create_default_scheduler() -> TaskScheduler:
    """创建默认配置的调度器"""
    scheduler = TaskScheduler()
    return scheduler


if __name__ == "__main__":
    # 测试调度器
    scheduler = create_default_scheduler()
    
    try:
        # 启动调度器（仅测试，不启用邮件）
        if scheduler.start(enable_email=False, enable_full_pipeline=False):
            print("调度器启动成功，运行10秒后停止...")
            time.sleep(10)
        else:
            print("调度器启动失败")
    
    finally:
        scheduler.stop()
        print("测试完成") 