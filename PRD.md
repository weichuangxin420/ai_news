# AI新闻收集与影响分析系统 - 产品需求文档 (PRD)

## 1. 项目概述

### 1.1 项目名称
AI新闻收集与影响分析系统 (AI News Collector & Impact Analyzer)

### 1.2 项目背景
为了帮助投资者和分析师及时了解最新市场动态，需要一个自动化系统来收集最新新闻，利用AI分析其对不同板块的影响，并及时推送给相关人员。

### 1.3 项目目标
- 自动化收集最新新闻资讯
- 利用DeepSeek AI智能分析新闻对各板块的影响
- 定时发送分析报告到指定邮箱
- 提供可配置的新闻源和分析参数

## 2. 功能需求

### 2.1 新闻收集模块
**功能描述**: 从多个新闻源收集最新的财经和市场相关新闻

**具体需求**:
- 支持多种新闻源（RSS、API、网页爬虫）
- 新闻去重功能
- 新闻质量过滤（关键词匹配、长度筛选）
- 支持中英文新闻
- 新闻分类标记

**技术实现**:
- RSS解析器 (feedparser)
- 网页爬虫 (requests + BeautifulSoup)
- 新闻API集成 (如新浪财经API、腾讯新闻API)
- 数据存储 (SQLite/JSON)

### 2.2 AI分析模块
**功能描述**: 使用DeepSeek AI分析新闻内容，判断对各个行业板块的影响

**具体需求**:
- 调用DeepSeek API进行新闻内容分析
- 识别新闻涉及的行业板块
- 评估影响程度（正面/负面/中性，影响强度1-10）
- 生成分析摘要和投资建议
- 处理API调用异常和重试机制

**技术实现**:
- DeepSeek API客户端
- 提示词工程优化
- 结果解析和结构化
- 错误处理和降级方案

### 2.3 邮件发送模块
**功能描述**: 将分析结果格式化后发送到指定邮箱

**具体需求**:
- 支持HTML格式邮件
- 美观的邮件模板设计
- 支持多个收件人
- 邮件发送失败重试机制
- 发送日志记录

**技术实现**:
- SMTP客户端 (smtplib)
- HTML邮件模板 (Jinja2)
- 邮件内容格式化
- 附件支持（可选）

### 2.4 定时调度模块
**功能描述**: 每隔30分钟自动执行新闻收集和分析流程

**具体需求**:
- 精确的定时执行（每30分钟）
- 任务执行状态监控
- 异常处理和恢复机制
- 支持手动触发执行
- 执行日志记录

**技术实现**:
- APScheduler调度器
- 任务状态管理
- 日志系统集成
- 信号处理（优雅关闭）

### 2.5 配置管理模块
**功能描述**: 管理系统各项配置参数

**具体需求**:
- 新闻源配置
- AI分析参数配置
- 邮件服务器配置
- 调度时间配置
- 支持配置文件热重载

**技术实现**:
- YAML/JSON配置文件
- 配置验证机制
- 敏感信息加密存储
- 环境变量支持

## 3. 技术架构

### 3.1 系统架构图
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   新闻收集模块   │    │   AI分析模块    │    │   邮件发送模块   │
│                │    │                │    │                │
│ • RSS解析      │    │ • DeepSeek API │    │ • SMTP客户端   │
│ • 网页爬虫      │ -> │ • 提示词工程    │ -> │ • 模板渲染     │
│ • API集成      │    │ • 结果解析     │    │ • 发送管理     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                │
                ┌─────────────────┴─────────────────┐
                │           定时调度模块            │
                │                                  │
                │ • APScheduler                   │
                │ • 任务管理                       │
                │ • 异常处理                       │
                └──────────────────────────────────┘
                                │
                ┌─────────────────┴─────────────────┐
                │           配置管理模块            │
                │                                  │
                │ • 配置文件管理                    │
                │ • 参数验证                       │
                │ • 环境变量                       │
                └──────────────────────────────────┘
```

### 3.2 数据流图
```
新闻源 -> 新闻收集 -> 数据清洗 -> AI分析 -> 结果格式化 -> 邮件发送
   │         │         │         │         │           │
   │         │         │         │         │           │
  RSS     去重过滤   关键词筛选  DeepSeek   HTML模板   SMTP发送
 API      数据存储   质量检查    影响分析   内容生成   收件人列表
网页爬虫   状态记录   分类标记    板块识别   邮件样式   发送状态
```

### 3.3 核心技术栈
- **Python 3.8+**: 主要开发语言
- **APScheduler**: 定时任务调度
- **requests**: HTTP请求库
- **BeautifulSoup4**: HTML解析
- **feedparser**: RSS解析
- **openai**: DeepSeek API客户端
- **smtplib**: 邮件发送
- **Jinja2**: 邮件模板引擎
- **PyYAML**: 配置文件解析
- **logging**: 日志管理
- **sqlite3**: 轻量级数据存储

## 4. 项目结构设计

```
ai_news/
├── config/
│   ├── config.yaml           # 主配置文件
│   ├── news_sources.yaml     # 新闻源配置
│   └── email_template.html   # 邮件模板
├── src/
│   ├── __init__.py
│   ├── news_collector.py     # 新闻收集模块
│   ├── ai_analyzer.py        # AI分析模块
│   ├── email_sender.py       # 邮件发送模块
│   ├── scheduler.py          # 定时调度模块
│   ├── config_manager.py     # 配置管理模块
│   └── utils/
│       ├── __init__.py
│       ├── logger.py         # 日志工具
│       ├── database.py       # 数据库操作
│       └── helpers.py        # 辅助函数
├── data/
│   ├── news.db              # SQLite数据库
│   └── logs/                # 日志文件目录
├── tests/
│   ├── __init__.py
│   ├── test_news_collector.py
│   ├── test_ai_analyzer.py
│   └── test_email_sender.py
├── requirements.txt         # 依赖包列表
├── main.py                 # 主程序入口
├── setup.py                # 安装脚本
└── README.md               # 项目说明文档
```

## 5. 接口设计

### 5.1 新闻收集模块接口
```python
class NewsCollector:
    def collect_news(self) -> List[NewsItem]
    def filter_news(self, news_list: List[NewsItem]) -> List[NewsItem]
    def deduplicate_news(self, news_list: List[NewsItem]) -> List[NewsItem]
    def save_news(self, news_list: List[NewsItem]) -> bool
```

### 5.2 AI分析模块接口
```python
class AIAnalyzer:
    def analyze_news(self, news_item: NewsItem) -> AnalysisResult
    def batch_analyze(self, news_list: List[NewsItem]) -> List[AnalysisResult]
    def format_analysis_report(self, results: List[AnalysisResult]) -> str
```

### 5.3 邮件发送模块接口
```python
class EmailSender:
    def send_report(self, content: str, recipients: List[str]) -> bool
    def generate_email_html(self, analysis_results: List[AnalysisResult]) -> str
    def validate_email_config(self) -> bool
```

## 6. 数据模型

### 6.1 新闻数据模型
```python
@dataclass
class NewsItem:
    id: str
    title: str
    content: str
    source: str
    publish_time: datetime
    url: str
    category: str
    keywords: List[str]
```

### 6.2 分析结果模型
```python
@dataclass
class AnalysisResult:
    news_id: str
    affected_sectors: List[str]
    impact_score: float  # -10到10，负数表示负面影响
    impact_level: str    # 高/中/低
    sentiment: str       # 正面/负面/中性
    summary: str
    recommendation: str
    analysis_time: datetime
```

## 7. 部署和运维

### 7.1 部署方式
- **开发环境**: 本地Python环境直接运行
- **生产环境**: Docker容器化部署
- **云服务**: 支持部署到阿里云、腾讯云等云平台

### 7.2 监控和日志
- 完整的执行日志记录
- 错误告警机制
- 性能监控指标
- 定期健康检查

### 7.3 数据备份
- 新闻数据定期备份
- 配置文件版本控制
- 分析结果历史记录

## 8. 风险评估

### 8.1 技术风险
- **API限流**: DeepSeek API调用频率限制
- **网络异常**: 新闻源访问失败
- **数据质量**: 新闻内容质量参差不齐

### 8.2 缓解措施
- 实现API调用限流和重试机制
- 多新闻源冗余，提高可用性
- 新闻质量过滤和人工审核机制

## 9. 成功指标

### 9.1 功能指标
- 新闻收集成功率 > 95%
- AI分析准确率 > 85%
- 邮件发送成功率 > 99%
- 系统可用性 > 99%

### 9.2 性能指标
- 单次执行时间 < 5分钟
- 内存使用 < 500MB
- CPU使用率 < 50%

## 10. 开发计划

### 阶段一：基础框架搭建 (1-2天)
- 项目结构创建
- 配置管理模块开发
- 日志系统搭建

### 阶段二：核心功能开发 (3-5天)
- 新闻收集模块开发
- AI分析模块开发
- 邮件发送模块开发

### 阶段三：调度和集成 (1-2天)
- 定时调度模块开发
- 各模块集成测试
- 错误处理完善

### 阶段四：测试和优化 (1-2天)
- 单元测试编写
- 集成测试
- 性能优化

### 阶段五：部署和文档 (1天)
- 部署脚本编写
- 用户文档完善
- 上线测试 