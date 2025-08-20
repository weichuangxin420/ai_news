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

from .collectors.news_collector import NewsCollector
from .ai.ai_analyzer import AIAnalyzer, create_enhanced_analyzer, BatchAnalysisConfig
from .ai.importance_analyzer import ImportanceAnalyzer
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
        self.enhanced_ai_analyzer = None
        self.importance_analyzer = None
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
            
            # 初始化增强版AI分析器（支持并发）
            self.enhanced_ai_analyzer = create_enhanced_analyzer(
                max_concurrent=self.config.get('scheduler', {}).get('concurrent_requests', 10),
                use_async=True,
                timeout_seconds=30,
                rate_limit=self.config.get('scheduler', {}).get('rate_limit', 100)
            )
            
            self.importance_analyzer = ImportanceAnalyzer()
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
    
    def add_enhanced_strategy_jobs(self):
        """添加增强版调度策略任务"""
        strategy_config = self.config.get('scheduler', {}).get('strategy', {})
        
        # 1. 早上8点收集并发送邮件
        morning_config = strategy_config.get('morning_collection', {})
        if morning_config.get('enabled', True):
            job = self.scheduler.add_job(
                func=self._morning_collection_with_email,
                trigger=CronTrigger(
                    hour=morning_config.get('hour', 8), 
                    minute=morning_config.get('minute', 0)
                ),
                id='morning_collection',
                name='早上8点收集并发送邮件',
                max_instances=1,
                coalesce=True
            )
            self.jobs['morning_collection'] = job
            logger.info("早上8点收集任务已添加")
        
        # 2. 交易时间每3分钟收集
        trading_config = strategy_config.get('trading_hours', {})
        if trading_config.get('enabled', True):
            job = self.scheduler.add_job(
                func=self._trading_hours_collection,
                trigger=IntervalTrigger(minutes=trading_config.get('interval_minutes', 3)),
                id='trading_hours_collection',
                name='交易时间收集',
                max_instances=1,
                coalesce=True
            )
            self.jobs['trading_hours_collection'] = job
            logger.info(f"交易时间收集任务已添加，间隔: {trading_config.get('interval_minutes', 3)}分钟")
        
        # 3. 晚上10点收集
        evening_config = strategy_config.get('evening_collection', {})
        if evening_config.get('enabled', True):
            job = self.scheduler.add_job(
                func=self._evening_collection_no_email,
                trigger=CronTrigger(
                    hour=evening_config.get('hour', 22), 
                    minute=evening_config.get('minute', 0)
                ),
                id='evening_collection',
                name='晚上10点收集',
                max_instances=1,
                coalesce=True
            )
            self.jobs['evening_collection'] = job
            logger.info("晚上10点收集任务已添加")
        
        # 4. 每日汇总邮件
        summary_config = strategy_config.get('daily_summary', {})
        if summary_config.get('enabled', True):
            job = self.scheduler.add_job(
                func=self._daily_summary_email,
                trigger=CronTrigger(
                    hour=summary_config.get('hour', 23), 
                    minute=summary_config.get('minute', 30)
                ),
                id='daily_summary',
                name='每日汇总邮件',
                max_instances=1,
                coalesce=True
            )
            self.jobs['daily_summary'] = job
            logger.info("每日汇总邮件任务已添加")

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
        """AI分析任务（使用增强版并发分析）"""
        logger.info("=== 开始执行AI分析任务（并发模式）===")
        
        try:
            if not self.enhanced_ai_analyzer:
                self.enhanced_ai_analyzer = create_enhanced_analyzer(
                    max_concurrent=self.config.get('scheduler', {}).get('concurrent_requests', 10),
                    use_async=True,
                    timeout_seconds=30,
                    rate_limit=100
                )
            
            # 获取未分析的新闻
            news_list = db_manager.get_news_items(limit=50)  # 增加批量大小
            if not news_list:
                logger.info("没有待分析的新闻")
                return 0
            
            start_time = time.time()
            # 使用增强版分析器进行并发分析
            results = self.enhanced_ai_analyzer.enhanced_batch_analyze(news_list)
            end_time = time.time()
            
            duration = end_time - start_time
            avg_time = duration / len(results) if results else 0
            logger.info(f"AI并发分析完成: {len(results)} 条新闻，总耗时: {duration:.2f} 秒，平均: {avg_time:.2f} 秒/条")
            
            return len(results)
            
        except Exception as e:
            logger.error(f"AI分析任务失败: {e}")
            # 降级到标准分析器
            try:
                logger.info("尝试使用标准分析器")
                if not self.ai_analyzer:
                    self.ai_analyzer = AIAnalyzer()
                news_list = db_manager.get_news_items(limit=20)
                if news_list:
                    results = self.ai_analyzer.batch_analyze(news_list)
                    logger.info(f"标准分析器完成: {len(results)} 条新闻")
                    return len(results)
            except Exception as fallback_e:
                logger.error(f"标准分析器也失败: {fallback_e}")
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
            
            # 快速分析（如果没有缓存的分析结果） - 使用并发分析
            if not self.enhanced_ai_analyzer:
                self.enhanced_ai_analyzer = create_enhanced_analyzer(
                    max_concurrent=5,
                    use_async=True,
                    timeout_seconds=300,
                    rate_limit=50
                )
            
            results = self.enhanced_ai_analyzer.enhanced_batch_analyze(news_list[:5])
            
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
    
    def collect_and_analyze_news(self, save_to_db: bool = True) -> List:
        """
        收集新闻并分析重要性
        
        Args:
            save_to_db: 是否保存到数据库
            
        Returns:
            分析后的新闻列表
        """
        try:
            # 1. 收集新闻
            logger.info("开始收集新闻...")
            if not self.news_collector:
                self.news_collector = NewsCollector()
            
            news_list = self.news_collector.collect_all_news()
            
            if not news_list:
                logger.info("没有收集到新的新闻")
                return []
            
            logger.info(f"收集到 {len(news_list)} 条新闻")
            
            # 2. 分析重要性（ImportanceAnalyzer）
            logger.info("开始分析新闻重要性...")
            if not self.importance_analyzer:
                self.importance_analyzer = ImportanceAnalyzer()
            importance_results = self.importance_analyzer.batch_analyze_importance(news_list)
            for news_item, result in zip(news_list, importance_results):
                news_item.importance_score = result.importance_score
                news_item.importance_reasoning = result.reasoning
                news_item.importance_factors = result.key_factors

            # 3. 并发AI分析（EnhancedAIAnalyzer）以获取影响程度（impact_level）
            logger.info("开始AI影响分析（并发）...")
            if not self.enhanced_ai_analyzer:
                self.enhanced_ai_analyzer = create_enhanced_analyzer(
                    max_concurrent=self.config.get('scheduler', {}).get('concurrent_requests', 10),
                    use_async=True,
                    timeout_seconds=30,
                    rate_limit=self.config.get('scheduler', {}).get('rate_limit', 100)
                )
            ai_results = self.enhanced_ai_analyzer.enhanced_batch_analyze(news_list)

            # 4. 将AI分析的影响级别映射到NewsItem.impact_degree
            try:
                from .ai.ai_analyzer import AnalysisResult as _AR
                # ai_results 与 news_list 一一对应
                for news_item, ar in zip(news_list, ai_results):
                    if hasattr(ar, 'impact_level'):
                        news_item.impact_degree = ar.impact_level
            except Exception as _e:
                logger.warning(f"映射影响程度失败: {_e}")

            # 5. 保存到数据库（包含重要性与影响程度）
            if save_to_db:
                saved_count = db_manager.save_news_items_batch(news_list)
                logger.info(f"保存 {saved_count} 条新闻（含重要性与影响程度）到数据库")
            
            return news_list
            
        except Exception as e:
            logger.error(f"收集和分析新闻失败: {e}")
            return []
    
    def _morning_collection_with_email(self):
        """早上8点：收集、分析并发送邮件"""
        try:
            logger.info("=== 执行早上8点收集任务 ===")
            
            # 收集和分析新闻
            news_list = self.collect_and_analyze_news()
            
            if news_list:
                # 发送邮件
                self._send_instant_email(news_list, "早间新闻报告")
                logger.info(f"早间新闻报告发送完成，包含 {len(news_list)} 条新闻")
                
        except Exception as e:
            logger.error(f"早上8点任务执行失败: {e}")
            raise
    
    def _trading_hours_collection(self):
        """交易时间收集（8:00-16:00）"""
        try:
            from datetime import time
            current_time = datetime.now().time()
            
            # 只在交易时间执行
            if time(8, 0) <= current_time <= time(16, 0):
                logger.info("=== 执行交易时间收集任务 ===")
                
                # 收集和分析新闻，但不发送邮件
                news_list = self.collect_and_analyze_news()
                
                if news_list:
                    logger.info(f"交易时间收集到 {len(news_list)} 条新闻")
            else:
                logger.debug("当前不在交易时间，跳过收集")
                
        except Exception as e:
            logger.error(f"交易时间收集任务失败: {e}")
            raise
    
    def _evening_collection_no_email(self):
        """晚上10点：收集但不发送邮件"""
        try:
            logger.info("=== 执行晚上10点收集任务 ===")
            
            # 收集和分析新闻
            news_list = self.collect_and_analyze_news()
            
            if news_list:
                logger.info(f"晚上10点收集到 {len(news_list)} 条新闻，已保存但不发送邮件")
                
        except Exception as e:
            logger.error(f"晚上10点任务执行失败: {e}")
            raise
    
    def _daily_summary_email(self):
        """每日汇总邮件（晚上11:30）"""
        try:
            logger.info("=== 生成每日汇总邮件 ===")
            
            # 获取今天的所有新闻
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_news = db_manager.get_news_items_by_date_range(today_start, datetime.now())
            
            if not today_news:
                logger.info("今天没有新闻，跳过汇总邮件")
                return
            
            # 按重要性排序
            sorted_news = sorted(today_news, key=lambda x: x.importance_score, reverse=True)
            
            # 生成汇总报告
            report = self._generate_daily_summary_report(sorted_news)
            
            # 发送邮件
            self._send_summary_email(report)
            
            logger.info(f"每日汇总邮件发送成功，包含 {len(sorted_news)} 条新闻")
            
        except Exception as e:
            logger.error(f"每日汇总邮件发送失败: {e}")
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
    
    def _send_instant_email(self, news_list, title_prefix: str = ""):
        """发送即时新闻邮件"""
        try:
            if not self.email_sender:
                self.email_sender = EmailSender()
            
            # 按重要性排序
            sorted_news = sorted(news_list, key=lambda x: x.importance_score, reverse=True)
            
            # 生成报告
            report = self._generate_instant_report(sorted_news)
            
            # 获取配置的收件人
            recipients = self.config.get('email', {}).get('recipients', [])
            
            # 发送邮件
            subject = f"📰 {title_prefix} - {datetime.now().strftime('%H:%M')}"
            self.email_sender.send_simple_email(
                recipients=recipients,
                subject=subject,
                content=report,
                is_html=True
            )
            
            logger.info(f"即时邮件发送成功: {title_prefix}")
            
        except Exception as e:
            logger.error(f"发送即时邮件失败: {e}")
    
    def _send_summary_email(self, report: str):
        """发送汇总邮件"""
        try:
            if not self.email_sender:
                self.email_sender = EmailSender()
            
            # 获取配置的收件人
            recipients = self.config.get('email', {}).get('recipients', [])
            
            # 发送邮件
            subject = f"📊 每日新闻汇总 - {datetime.now().strftime('%Y年%m月%d日')}"
            self.email_sender.send_simple_email(
                recipients=recipients,
                subject=subject,
                content=report,
                is_html=True
            )
            
            logger.info("每日汇总邮件发送成功")
            
        except Exception as e:
            logger.error(f"发送汇总邮件失败: {e}")
    
    def _generate_instant_report(self, news_list) -> str:
        """生成即时新闻报告（HTML格式）"""
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; }}
                .news-item {{ margin: 20px 0; padding: 15px; border-left: 4px solid #667eea; background: #f8f9fa; }}
                .importance-high {{ border-left-color: #e74c3c; }}
                .importance-medium {{ border-left-color: #f39c12; }}
                .importance-low {{ border-left-color: #27ae60; }}
                .score {{ display: inline-block; padding: 3px 8px; border-radius: 3px; font-weight: bold; }}
                .score-high {{ background: #e74c3c; color: white; }}
                .score-medium {{ background: #f39c12; color: white; }}
                .score-low {{ background: #27ae60; color: white; }}
                .summary {{ margin: 10px 0; color: #555; }}
                .factors {{ font-size: 0.9em; color: #777; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📰 即时新闻报告</h1>
                <p>时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}</p>
                <p>新闻数量: {len(news_list)} 条</p>
            </div>
        """
        
        for news in news_list[:10]:  # 最多显示10条
            # 确定重要性等级
            if news.importance_score >= 70:
                importance_class = "importance-high"
                score_class = "score-high"
                importance_emoji = "🔴"
            elif news.importance_score >= 40:
                importance_class = "importance-medium"
                score_class = "score-medium"
                importance_emoji = "🟡"
            else:
                importance_class = "importance-low"
                score_class = "score-low"
                importance_emoji = "🟢"
            
            html += f"""
            <div class="news-item {importance_class}">
                <h3>{importance_emoji} {news.title}</h3>
                <p>
                    <span class="score {score_class}">重要性: {news.importance_score}分</span>
                    <span style="margin-left: 10px;">来源: {news.source}</span>
                </p>
                <div class="summary">
                    <strong>摘要:</strong> {news.content[:200]}...
                </div>
                <div class="factors">
                    <strong>关键因素:</strong> {news.importance_factors if hasattr(news, 'importance_factors') and news.importance_factors else '暂无'}
                </div>
            </div>
            """
        
        html += """
        </body>
        </html>
        """
        
        return html
    
    def _generate_daily_summary_report(self, news_list) -> str:
        """生成每日汇总报告（HTML格式）"""
        
        # 统计信息
        total_count = len(news_list)
        high_importance = len([n for n in news_list if n.importance_score >= 70])
        medium_importance = len([n for n in news_list if 40 <= n.importance_score < 70])
        low_importance = len([n for n in news_list if n.importance_score < 40])
        avg_score = sum(n.importance_score for n in news_list) / total_count if total_count > 0 else 0
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; }}
                .stats {{ display: flex; justify-content: space-around; margin: 30px 0; }}
                .stat-card {{ text-align: center; padding: 20px; background: #f8f9fa; border-radius: 8px; flex: 1; margin: 0 10px; }}
                .stat-number {{ font-size: 2em; font-weight: bold; color: #667eea; }}
                .news-section {{ margin: 30px 0; }}
                .section-title {{ font-size: 1.5em; color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px; margin-bottom: 20px; }}
                .news-item {{ margin: 15px 0; padding: 15px; border-radius: 8px; background: #f8f9fa; }}
                .news-title {{ font-weight: bold; color: #333; margin-bottom: 5px; }}
                .importance {{ display: inline-block; padding: 3px 10px; border-radius: 15px; font-size: 0.9em; font-weight: bold; }}
                .importance-high {{ background: #e74c3c; color: white; }}
                .importance-medium {{ background: #f39c12; color: white; }}
                .importance-low {{ background: #27ae60; color: white; }}
                .summary {{ color: #666; margin: 10px 0; }}
                .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #999; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 每日新闻汇总报告</h1>
                    <p style="font-size: 1.2em;">{datetime.now().strftime('%Y年%m月%d日')}</p>
                </div>
                
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-number">{total_count}</div>
                        <div>总新闻数</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{avg_score:.1f}</div>
                        <div>平均重要性</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{high_importance}</div>
                        <div>高重要性新闻</div>
                    </div>
                </div>
        """
        
        # 高重要性新闻
        high_news = [n for n in news_list if n.importance_score >= 70]
        if high_news:
            html += """
                <div class="news-section">
                    <h2 class="section-title">🔴 高重要性新闻</h2>
            """
            for news in high_news[:10]:
                html += f"""
                    <div class="news-item">
                        <div class="news-title">
                            {news.title}
                            <span class="importance importance-high">{news.importance_score}分</span>
                        </div>
                        <div class="summary">{news.content[:150]}...</div>
                    </div>
                """
            html += "</div>"
        
        # 中等重要性新闻
        medium_news = [n for n in news_list if 40 <= n.importance_score < 70]
        if medium_news:
            html += """
                <div class="news-section">
                    <h2 class="section-title">🟡 中等重要性新闻</h2>
            """
            for news in medium_news[:10]:
                html += f"""
                    <div class="news-item">
                        <div class="news-title">
                            {news.title}
                            <span class="importance importance-medium">{news.importance_score}分</span>
                        </div>
                        <div class="summary">{news.content[:150]}...</div>
                    </div>
                """
            html += "</div>"
        
        # 低重要性新闻摘要
        if low_importance > 0:
            html += f"""
                <div class="news-section">
                    <h2 class="section-title">🟢 其他新闻</h2>
                    <p>今日还有 {low_importance} 条低重要性新闻，主要涉及日常市场动态和公司公告。</p>
                </div>
            """
        
        html += f"""
                <div class="footer">
                    <p>本报告由AI新闻分析系统自动生成</p>
                    <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html

    def _health_check(self):
        """系统健康检查"""
        try:
            # 检查组件状态
            components_status = {
                'news_collector': self.news_collector is not None,
                'ai_analyzer': self.ai_analyzer is not None,
                'enhanced_ai_analyzer': self.enhanced_ai_analyzer is not None,
                'importance_analyzer': self.importance_analyzer is not None,
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
             enable_enhanced_strategy: bool = False,
             enable_maintenance: bool = True):
        """
        启动调度器
        
        Args:
            enable_news_collection: 是否启用新闻收集任务
            enable_analysis: 是否启用分析任务
            enable_email: 是否启用邮件任务
            enable_full_pipeline: 是否启用完整流程任务
            enable_enhanced_strategy: 是否启用增强版调度策略
            enable_maintenance: 是否启用维护任务
        """
        try:
            logger.info("正在启动任务调度器...")
            
            # 初始化组件
            if not self.initialize_components():
                logger.error("组件初始化失败，无法启动调度器")
                return False
            
            # 添加任务
            if enable_enhanced_strategy:
                # 使用增强版调度策略
                self.add_enhanced_strategy_jobs()
            elif enable_full_pipeline:
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