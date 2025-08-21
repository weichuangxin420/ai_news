"""
邮件发送模块
支持发送HTML格式的分析报告邮件
"""

import smtplib
import ssl
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
import yaml

from .utils.logger import get_logger
from .ai.ai_analyzer import AnalysisResult

logger = get_logger('email_sender')


class EmailSender:
    """邮件发送器"""
    
    def __init__(self, config_path: str = None):
        """
        初始化邮件发送器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.smtp_config = self.config.get('email', {}).get('smtp', {})
        self.template_config = self.config.get('email', {}).get('template', {})
        
        # 统计信息
        self.stats = {
            'sent': 0,
            'failed': 0,
            'last_send_time': None
        }
    
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
    
    def send_analysis_report(self, 
                           analysis_results: List[AnalysisResult],
                           recipients: List[str] = None,
                           subject: str = None) -> bool:
        """
        发送分析报告邮件
        
        Args:
            analysis_results: 分析结果列表
            recipients: 收件人列表
            subject: 邮件主题
            
        Returns:
            bool: 发送是否成功
        """
        try:
            if not analysis_results:
                logger.warning("没有分析结果，跳过邮件发送")
                return False
            
            # 生成HTML报告
            html_content = self._generate_html_report(analysis_results)
            
            # 设置收件人和主题
            recipients = recipients or self.config.get('email', {}).get('recipients', [])
            if not recipients:
                logger.error("未配置收件人")
                return False
            
            subject = subject or self._generate_subject()
            
            # 发送邮件
            success = self._send_email(
                recipients=recipients,
                subject=subject,
                html_content=html_content
            )
            
            if success:
                self.stats['sent'] += 1
                self.stats['last_send_time'] = datetime.now().isoformat()
                logger.info(f"分析报告邮件发送成功，收件人: {len(recipients)} 人")
            else:
                self.stats['failed'] += 1
                
            return success
            
        except Exception as e:
            logger.error(f"发送分析报告失败: {e}")
            self.stats['failed'] += 1
            return False
    
    def send_simple_email(self,
                         recipients: List[str],
                         subject: str,
                         content: str,
                         is_html: bool = False) -> bool:
        """
        发送简单邮件
        
        Args:
            recipients: 收件人列表
            subject: 邮件主题
            content: 邮件内容
            is_html: 是否为HTML格式
            
        Returns:
            bool: 发送是否成功
        """
        try:
            success = self._send_email(
                recipients=recipients,
                subject=subject,
                html_content=content if is_html else None,
                text_content=content if not is_html else None
            )
            
            if success:
                self.stats['sent'] += 1
                self.stats['last_send_time'] = datetime.now().isoformat()
                logger.info(f"邮件发送成功: {subject}")
            else:
                self.stats['failed'] += 1
                
            return success
            
        except Exception as e:
            logger.error(f"发送邮件失败: {e}")
            self.stats['failed'] += 1
            return False
    
    def _send_email(self,
                   recipients: List[str],
                   subject: str,
                   html_content: str = None,
                   text_content: str = None,
                   attachments: List[str] = None) -> bool:
        """
        发送邮件的核心方法
        
        Args:
            recipients: 收件人列表
            subject: 邮件主题
            html_content: HTML内容
            text_content: 纯文本内容
            attachments: 附件路径列表
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 验证配置
            if not self._validate_smtp_config():
                return False
            
            # 创建邮件消息
            msg = MIMEMultipart('alternative')
            msg['From'] = self._get_from_address()
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            
            # 添加文本内容
            if text_content:
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(text_part)
            
            # 添加HTML内容
            if html_content:
                html_part = MIMEText(html_content, 'html', 'utf-8')
                msg.attach(html_part)
            
            # 添加附件
            if attachments:
                for file_path in attachments:
                    self._add_attachment(msg, file_path)
            
            # 发送邮件
            with self._create_smtp_connection() as server:
                server.sendmail(
                    self._get_from_address(),
                    recipients,
                    msg.as_string()
                )
            
            return True
            
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False
    
    def _validate_smtp_config(self) -> bool:
        """验证SMTP配置"""
        required_fields = ['server', 'port', 'username', 'password']
        
        for field in required_fields:
            if not self.smtp_config.get(field):
                logger.error(f"SMTP配置缺少必要字段: {field}")
                return False
        
        return True
    
    def _create_smtp_connection(self):
        """创建SMTP连接"""
        server = self.smtp_config['server']
        port = self.smtp_config['port']
        username = self.smtp_config['username']
        password = self.smtp_config['password']
        use_tls = self.smtp_config.get('use_tls', True)
        use_ssl = self.smtp_config.get('use_ssl', False)
        
        logger.debug(f"连接SMTP服务器: {server}:{port}")
        
        # 创建SSL上下文
        context = ssl.create_default_context()
        
        if use_ssl or port == 465:
            # 使用SSL连接（适用于163邮箱的465端口）
            smtp_server = smtplib.SMTP_SSL(server, port, context=context)
            logger.debug("使用SSL连接")
        elif use_tls or port == 587:
            # 使用TLS连接（适用于587端口）
            smtp_server = smtplib.SMTP(server, port)
            smtp_server.starttls(context=context)
            logger.debug("使用TLS连接")
        else:
            # 不加密连接（不推荐）
            smtp_server = smtplib.SMTP(server, port)
            logger.debug("使用不加密连接")
        
        # 登录
        smtp_server.login(username, password)
        logger.debug("SMTP登录成功")
        
        return smtp_server
    
    def _get_from_address(self) -> str:
        """获取发件人地址"""
        username = self.smtp_config.get('username', '')
        from_name = self.template_config.get('from_name', 'AI新闻助手')
        
        if from_name:
            return f"{from_name} <{username}>"
        return username
    
    def _generate_subject(self) -> str:
        """生成邮件主题"""
        template = self.template_config.get('subject', 'AI新闻分析报告 - {date}')
        return template.format(
            date=datetime.now().strftime('%Y-%m-%d %H:%M'),
            datetime=datetime.now()
        )
    
    def _generate_html_report(self, analysis_results: List[AnalysisResult]) -> str:
        """
        生成HTML格式的分析报告
        
        Args:
            analysis_results: 分析结果列表
            
        Returns:
            str: HTML内容
        """
        # 导入数据库管理器获取完整新闻信息
        from .utils.database import DatabaseManager
        
        # 获取新闻详细信息
        db_manager = DatabaseManager()
        news_details = {}
        for result in analysis_results:
            news_item = db_manager.get_news_item_by_id(result.news_id)
            if news_item:
                news_details[result.news_id] = news_item
        
        # 统计信息
        total_news = len(analysis_results)
        # 根据影响分数判断情感倾向
        positive_count = sum(1 for r in analysis_results if r.impact_score > 5)
        negative_count = sum(1 for r in analysis_results if r.impact_score < -5)
        neutral_count = total_news - positive_count - negative_count
        
        # 按影响分数排序新闻
        sorted_results = sorted(analysis_results, key=lambda x: abs(x.impact_score), reverse=True)
        
        # 高影响新闻（影响分数绝对值大于10的）
        high_impact_results = [r for r in analysis_results if abs(r.impact_score) > 10]
        
        # 重要性等级统计
        high_importance = sum(1 for r in analysis_results 
                            if news_details.get(r.news_id) and news_details[r.news_id].importance_score >= 80)
        medium_importance = sum(1 for r in analysis_results 
                              if news_details.get(r.news_id) and 50 <= news_details[r.news_id].importance_score < 80)
        low_importance = total_news - high_importance - medium_importance
        
        # 生成HTML
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>AI新闻影响分析报告</title>
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif;
            line-height: 1.4;
            margin: 0;
            padding: 10px;
            background-color: #f8f9fa;
            font-size: 13px;
        }}
        .container {{
            max-width: 100%;
            margin: 0 auto;
            background-color: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #007acc;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            color: #2c3e50;
            margin: 0;
            font-size: 18px;
            font-weight: 600;
        }}
        .header .datetime {{
            color: #6c757d;
            font-size: 11px;
            margin-top: 8px;
        }}
        .summary {{
            background: linear-gradient(135deg, #007acc 0%, #0056b3 100%);
            color: white;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
        }}
        .summary h2 {{
            margin: 0 0 10px 0;
            font-size: 16px;
            font-weight: 600;
        }}
        .summary p {{
            margin: 0 0 12px 0;
            font-size: 12px;
        }}
        .stats {{
            display: flex;
            justify-content: space-around;
            margin-top: 12px;
        }}
        .stat-item {{
            text-align: center;
            flex: 1;
        }}
        .stat-number {{
            font-size: 18px;
            font-weight: bold;
            display: block;
        }}
        .stat-label {{
            font-size: 10px;
            opacity: 0.9;
        }}
        .section {{
            margin-bottom: 20px;
        }}
        .section h3 {{
            color: #2c3e50;
            border-left: 3px solid #007acc;
            padding-left: 10px;
            margin: 0 0 15px 0;
            font-size: 14px;
            font-weight: 600;
        }}
        .importance-stats {{
            display: flex;
            gap: 8px;
            margin-bottom: 15px;
        }}
        .importance-item {{
            flex: 1;
            background: #f8f9fa;
            padding: 8px;
            border-radius: 4px;
            text-align: center;
            border: 1px solid #e9ecef;
        }}
        .importance-high {{ border-color: #dc3545; color: #dc3545; }}
        .importance-medium {{ border-color: #ffc107; color: #856404; }}
        .importance-low {{ border-color: #28a745; color: #28a745; }}
        .news-item {{
            background: #fff;
            border: 1px solid #e9ecef;
            border-radius: 6px;
            padding: 12px;
            margin: 10px 0;
            border-left: 4px solid #dee2e6;
        }}
        .news-item.high-impact {{
            border-left-color: #dc3545;
            background: #fef8f8;
        }}
        .news-item.positive {{
            border-left-color: #28a745;
        }}
        .news-item.negative {{
            border-left-color: #dc3545;
        }}
        .news-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 8px;
            flex-wrap: wrap;
            gap: 5px;
        }}
        .news-title {{
            font-weight: 600;
            color: #2c3e50;
            font-size: 13px;
            line-height: 1.3;
            margin: 0;
            flex: 1;
        }}
        .news-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: center;
            margin: 8px 0;
        }}
        .impact-score {{
            background: #6c757d;
            color: white;
            padding: 2px 6px;
            border-radius: 10px;
            font-weight: bold;
            font-size: 10px;
            white-space: nowrap;
        }}
        .impact-score.positive {{ background: #28a745; }}
        .impact-score.negative {{ background: #dc3545; }}
        .importance-badge {{
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: 500;
            white-space: nowrap;
        }}
        .importance-badge.high {{ background: #f8d7da; color: #721c24; }}
        .importance-badge.medium {{ background: #fff3cd; color: #856404; }}
        .importance-badge.low {{ background: #d4edda; color: #155724; }}
        .news-source {{
            color: #6c757d;
            font-size: 10px;
        }}
        .news-time {{
            color: #6c757d;
            font-size: 10px;
        }}
        .news-summary {{
            color: #495057;
            font-size: 12px;
            line-height: 1.4;
            margin: 8px 0 0 0;
        }}
        .news-content {{
            font-size: 11px;
            color: #6c757d;
            margin-top: 5px;
            line-height: 1.3;
            max-height: 60px;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .footer {{
            text-align: center;
            color: #6c757d;
            font-size: 10px;
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid #e9ecef;
        }}
        .all-news {{
            margin-top: 10px;
        }}
        /* 移动端优化 */
        @media (max-width: 480px) {{
            body {{ padding: 5px; font-size: 12px; }}
            .container {{ padding: 10px; }}
            .header h1 {{ font-size: 16px; }}
            .summary h2 {{ font-size: 14px; }}
            .section h3 {{ font-size: 13px; }}
            .news-title {{ font-size: 12px; }}
            .news-summary {{ font-size: 11px; }}
            .stats {{ flex-wrap: wrap; }}
            .stat-item {{ margin: 5px 0; }}
            .importance-stats {{ flex-direction: column; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AI新闻影响分析报告</h1>
            <div class="datetime">报告生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</div>
        </div>
        
        <div class="summary">
            <h2>📊 分析概况</h2>
            <p>本次共分析 <strong>{total_news}</strong> 条新闻，基于DeepSeek AI技术进行A股市场影响评估</p>
            <div class="stats">
                <div class="stat-item">
                    <span class="stat-number">{positive_count}</span>
                    <span class="stat-label">正面影响</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">{negative_count}</span>
                    <span class="stat-label">负面影响</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">{neutral_count}</span>
                    <span class="stat-label">中性影响</span>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h3>📊 重要性等级分布</h3>
            <div class="importance-stats">
                <div class="importance-item importance-high">
                    <div style="font-weight: bold; font-size: 14px;">{high_importance}</div>
                    <div style="font-size: 10px;">高重要性</div>
                </div>
                <div class="importance-item importance-medium">
                    <div style="font-weight: bold; font-size: 14px;">{medium_importance}</div>
                    <div style="font-size: 10px;">中重要性</div>
                </div>
                <div class="importance-item importance-low">
                    <div style="font-weight: bold; font-size: 14px;">{low_importance}</div>
                    <div style="font-size: 10px;">低重要性</div>
                </div>
            </div>
        </div>
"""

        # 添加高影响新闻部分
        if high_impact_results:
            html_content += f"""
        <div class="section">
            <h3>🔥 高影响新闻 ({len(high_impact_results)}条)</h3>
"""
            for result in high_impact_results[:5]:  # 只显示前5条
                news_item = news_details.get(result.news_id)
                if not news_item:
                    continue
                    
                # 确定样式类
                impact_class = 'positive' if result.impact_score > 0 else 'negative' if result.impact_score < 0 else ''
                score_class = 'positive' if result.impact_score > 0 else 'negative' if result.impact_score < 0 else ''
                
                # 重要性等级
                importance_level = 'high' if news_item.importance_score >= 80 else 'medium' if news_item.importance_score >= 50 else 'low'
                importance_text = '高' if importance_level == 'high' else '中' if importance_level == 'medium' else '低'
                
                # 格式化时间
                time_str = news_item.publish_time.strftime('%m-%d %H:%M') if news_item.publish_time else ''
                
                html_content += f"""
            <div class="news-item high-impact {impact_class}">
                <div class="news-header">
                    <h4 class="news-title">{news_item.title}</h4>
                </div>
                <div class="news-meta">
                    <span class="impact-score {score_class}">影响: {result.impact_score:.1f}</span>
                    <span class="importance-badge {importance_level}">重要性: {importance_text}</span>
                    <span class="news-source">{news_item.source}</span>
                    <span class="news-time">{time_str}</span>
                </div>
                <div class="news-summary">
                    <strong>AI分析:</strong> {result.summary}
                </div>
                <div class="news-content">
                    {news_item.content[:200]}{'...' if len(news_item.content) > 200 else ''}
                </div>
            </div>
"""

            html_content += """
        </div>
"""

        # 添加所有新闻列表
        html_content += f"""
        <div class="section">
            <h3>📰 全部新闻分析 ({total_news}条)</h3>
            <div class="all-news">
"""

        for result in sorted_results:
            news_item = news_details.get(result.news_id)
            if not news_item:
                continue
                
            # 确定样式类
            impact_class = 'positive' if result.impact_score > 0 else 'negative' if result.impact_score < 0 else ''
            score_class = 'positive' if result.impact_score > 0 else 'negative' if result.impact_score < 0 else ''
            
            # 重要性等级
            importance_level = 'high' if news_item.importance_score >= 80 else 'medium' if news_item.importance_score >= 50 else 'low'
            importance_text = '高' if importance_level == 'high' else '中' if importance_level == 'medium' else '低'
            
            # 格式化时间
            time_str = news_item.publish_time.strftime('%m-%d %H:%M') if news_item.publish_time else ''
            
            html_content += f"""
                <div class="news-item {impact_class}">
                    <div class="news-header">
                        <h4 class="news-title">{news_item.title}</h4>
                    </div>
                    <div class="news-meta">
                        <span class="impact-score {score_class}">影响: {result.impact_score:.1f}</span>
                        <span class="importance-badge {importance_level}">重要性: {importance_text}</span>
                        <span class="news-source">{news_item.source}</span>
                        <span class="news-time">{time_str}</span>
                    </div>
                    <div class="news-summary">
                        <strong>AI分析:</strong> {result.summary}
                    </div>
                </div>
"""

        # 添加页脚
        html_content += f"""
            </div>
        </div>
        
        <div class="footer">
            <p>本报告由AI新闻收集与影响分析系统自动生成</p>
            <p>数据来源: 多渠道新闻源 | 分析引擎: DeepSeek AI</p>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p style="color: #dc3545; font-size: 9px;">⚠️ 免责声明: 本报告仅供参考，投资有风险，决策需谨慎</p>
        </div>
    </div>
</body>
</html>
"""
        
        return html_content
    
    def _add_attachment(self, msg: MIMEMultipart, file_path: str):
        """
        添加附件到邮件
        
        Args:
            msg: 邮件消息对象
            file_path: 附件文件路径
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"附件文件不存在: {file_path}")
                return
            
            with open(file_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {os.path.basename(file_path)}'
            )
            
            msg.attach(part)
            logger.debug(f"添加附件: {file_path}")
            
        except Exception as e:
            logger.error(f"添加附件失败: {e}")
    
    def test_connection(self) -> bool:
        """
        测试邮件服务器连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            if not self._validate_smtp_config():
                return False
            
            logger.info("测试SMTP连接...")
            with self._create_smtp_connection() as server:
                logger.info("SMTP连接测试成功")
                return True
                
        except Exception as e:
            logger.error(f"SMTP连接测试失败: {e}")
            return False
    
    def send_test_email(self, recipient: str = None) -> bool:
        """
        发送测试邮件
        
        Args:
            recipient: 收件人（可选，默认使用配置中的第一个收件人）
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 确定收件人
            if not recipient:
                recipients = self.config.get('email', {}).get('recipients', [])
                if not recipients:
                    logger.error("未配置收件人且未指定测试收件人")
                    return False
                recipient = recipients[0]
            
            # 测试邮件内容
            test_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            test_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; }}
        .header {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .content {{ margin: 20px 0; line-height: 1.6; }}
        .success {{ color: #27ae60; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>📧 邮件发送测试</h2>
    </div>
    <div class="content">
        <p>这是一封测试邮件，用于验证AI新闻收集与影响分析系统的邮件发送功能。</p>
        <p class="success">✅ 如果您收到这封邮件，说明邮件发送功能配置正确！</p>
        <p><strong>测试时间:</strong> {test_time}</p>
        <p><strong>发送系统:</strong> AI新闻收集与影响分析系统</p>
    </div>
</body>
</html>
            """
            
            success = self._send_email(
                recipients=[recipient],
                subject="📧 邮件发送功能测试",
                html_content=test_html
            )
            
            if success:
                logger.info(f"测试邮件发送成功: {recipient}")
                self.stats['sent'] += 1
                self.stats['last_send_time'] = datetime.now().isoformat()
            else:
                self.stats['failed'] += 1
            
            return success
            
        except Exception as e:
            logger.error(f"发送测试邮件失败: {e}")
            self.stats['failed'] += 1
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取邮件发送统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            **self.stats,
            'smtp_configured': self._validate_smtp_config(),
            'recipients_count': len(self.config.get('email', {}).get('recipients', []))
        }


# 便捷函数
def send_analysis_report_email(analysis_results: List[AnalysisResult],
                              recipients: List[str] = None) -> bool:
    """
    便捷函数：发送分析报告邮件
    
    Args:
        analysis_results: 分析结果列表
        recipients: 收件人列表
        
    Returns:
        bool: 发送是否成功
    """
    sender = EmailSender()
    return sender.send_analysis_report(analysis_results, recipients)


if __name__ == "__main__":
    # 测试邮件发送功能
    sender = EmailSender()
    
    # 测试连接
    if sender.test_connection():
        print("✅ SMTP连接测试成功")
        
        # 发送测试邮件
        if sender.send_test_email():
            print("✅ 测试邮件发送成功")
        else:
            print("❌ 测试邮件发送失败")
    else:
        print("❌ SMTP连接测试失败")
    
    # 显示统计信息
    stats = sender.get_stats()
    print(f"邮件统计: {stats}") 