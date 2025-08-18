# AI新闻收集与影响分析系统

一个智能的新闻收集和A股影响分析系统，能够自动从多个数据源收集财经新闻，使用DeepSeek AI分析对股市板块的影响，并通过邮件发送分析报告。

## 🌟 主要功能

- 🔍 **多源新闻收集**: 支持RSS订阅、API调用和网页爬虫
- 🤖 **AI智能分析**: 使用DeepSeek分析新闻对A股板块的影响
- 📧 **自动邮件推送**: 定时发送分析报告到指定邮箱
- ⏱️ **定时自动执行**: 每30分钟自动收集和分析最新新闻
- 🎯 **关键词过滤**: 智能过滤与A股相关的重要新闻
- 📊 **数据统计**: 提供详细的收集和分析统计信息

## 🏗️ 项目结构

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
└── README.md               # 项目说明文档
```

## 🚀 快速开始

### 方式1: Docker部署（推荐）

如果你有Docker环境，可以使用Docker一键部署：

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/ai_news.git
cd ai_news

# 2. 配置应用
cp config/config.yaml.template config/config.yaml
# 编辑config/config.yaml，填入你的API密钥和邮箱信息

# 3. 一键部署
docker-compose build
docker-compose up -d

# 4. 查看状态
docker-compose ps
docker-compose logs -f
```

> 📖 **详细的Docker部署说明请参考**: [DOCKER_DEPLOY.md](./DOCKER_DEPLOY.md)

### 方式2: 传统部署

### 1. 环境准备

确保你的系统已安装 Python 3.8+：

```bash
python --version
```

### 2. 克隆项目

```bash
git clone <repository_url>
cd ai_news
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置设置

**所有配置都在 `config/config.yaml` 文件中**，请直接编辑此文件：

- **邮箱配置**: 修改 `email.smtp.username` 和 `password`，以及 `recipients` 收件人列表
- **DeepSeek API密钥**: 在 `ai_analysis.deepseek.api_key` 中设置（可选，有模拟模式）
- **调度配置**: 调整 `scheduler.pipeline_interval` 执行间隔
- **新闻源**: 根据需要启用/禁用不同的新闻源

### 5. 邮件配置（163邮箱）

**配置步骤**:
1. **开启163邮箱SMTP服务**
   - 登录163邮箱 → 设置 → POP3/SMTP/IMAP
   - 开启"IMAP/SMTP服务"和"客户端授权密码"
   - 生成授权密码（**重要：不是登录密码**）

2. **修改配置文件**
   编辑 `config/config.yaml` 中的邮箱配置：
   ```yaml
   email:
     smtp:
       username: "your_email@163.com"
       password: "your_authorization_password"
     recipients:
       - "recipient@163.com"
   ```

3. **测试邮件功能**
   ```bash
   python main.py email-test   # 测试连接
   python main.py email-send   # 发送测试邮件
   ```

### 6. 测试运行

```bash
# 测试新闻收集功能
python main.py test

# 查看帮助信息
python main.py help
```

## 📖 使用说明

### 命令行界面

```bash
# 🔍 新闻收集
python main.py test         # 测试新闻收集功能
python main.py collect      # 执行新闻收集

# 🤖 AI分析
python main.py analyze      # 测试AI分析功能

# 📧 邮件功能
python main.py email-test   # 测试SMTP连接
python main.py email-send   # 发送测试邮件

# 🔄 完整流程
python main.py pipeline     # 基础流程（收集+分析）
python main.py pipeline-email  # 完整流程（收集+分析+邮件）

# ⏰ 定时调度
python main.py scheduler-test   # 测试调度器功能
python main.py scheduler-start  # 启动调度器（带监控界面）
python main.py scheduler-run    # 启动调度器后台运行
python main.py scheduler-status # 查看调度器状态

# 📊 查看状态
python main.py recent       # 显示最近新闻
python main.py stats        # 显示统计信息
python main.py help         # 显示帮助信息
```

### 定时调度器

系统提供强大的定时调度功能，可以自动化执行新闻收集、AI分析和邮件发送任务。

#### 🔧 调度器特性

- **一体化流程** - 每30分钟执行：新闻收集→AI分析→立即发送邮件
- **错误恢复** - 自动重试和故障恢复机制
- **健康监控** - 实时监控系统健康状态
- **可视化界面** - 实时状态监控和任务管理
- **数据管理** - 自动清理过期数据（保留7天）

#### ⏰ 调度配置

在 `config/config.yaml` 中配置调度参数：

```yaml
scheduler:
  pipeline_interval: 30        # 完整流程间隔（分钟）- 收集+分析+邮件
  email_recent_hours: 1        # 邮件包含最新的分析结果
  retention:
    max_days: 7                # 数据保留7天
```

#### 🚀 启动调度器

```bash
# 测试调度器功能
python main.py scheduler-test

# 启动调度器（带实时监控界面）
python main.py scheduler-start

# 后台运行调度器
python main.py scheduler-run

# 查看调度器状态
python main.py scheduler-status
```

#### 📊 监控界面

调度器提供实时监控界面，显示：
- 运行状态和健康状况
- 任务执行统计
- 下次执行时间
- 最近事件日志
- 组件状态监控

### 新闻源配置

系统支持多种新闻源：

#### RSS源
- 东方财富RSS
- 财联社RSS  
- 格隆汇RSS
- 雪球RSS

#### API源
- 东方财富免费API
- 其他财经API（可扩展）

#### 网页爬虫
- 新浪财经（默认关闭）
- 其他财经网站（可配置）

### 关键词过滤

系统会根据配置的关键词自动过滤相关新闻：

**包含关键词**: A股、股市、上证、深证、创业板、科创板等
**排除关键词**: 广告、推广、招聘、培训等

## 🔧 配置说明

### 主配置文件 (config/config.yaml)

```yaml
# 新闻收集配置
news_collection:
  collection_interval: 30  # 收集间隔（分钟）
  sources:
    rss_feeds: [...]       # RSS源列表
    api_sources: {...}     # API源配置
    web_scraping: [...]    # 爬虫源配置
  keywords:
    include: [...]         # 包含关键词
    exclude: [...]         # 排除关键词

# AI分析配置
ai_analysis:
  deepseek:
    api_key: "${DEEPSEEK_API_KEY}"
    model: "deepseek-chat"
    max_tokens: 2000
    temperature: 0.1

# 邮件配置
email:
  smtp:
    server: "smtp.qq.com"
    port: 587
    use_tls: true
  recipients: [...]

# 数据库配置
database:
  sqlite:
    db_path: "data/news.db"
  retention:
    max_days: 30
```

## 🧩 核心模块

### 1. 新闻收集模块 (news_collector.py)

负责从多个数据源收集新闻：

- **RSS解析**: 使用feedparser解析RSS订阅源
- **API调用**: 调用财经网站API获取结构化数据  
- **网页爬虫**: 使用BeautifulSoup爬取网页内容
- **并发处理**: 支持多线程并发收集提高效率
- **去重过滤**: 基于标题和URL的智能去重
- **关键词匹配**: 自动筛选A股相关新闻

### 2. 数据库模块 (database.py)

提供完整的数据管理功能：

- **SQLite存储**: 轻量级本地数据库
- **数据模型**: 新闻项和分析结果的完整建模
- **CRUD操作**: 增删改查的完整支持
- **批量操作**: 高效的批量插入和更新
- **数据清理**: 自动清理过期数据
- **统计查询**: 丰富的统计信息查询

### 3. 日志模块 (logger.py)

统一的日志管理系统：

- **多级日志**: 支持DEBUG、INFO、WARNING、ERROR、CRITICAL
- **文件轮转**: 自动管理日志文件大小和数量
- **格式化输出**: 结构化的日志格式
- **单例模式**: 确保日志配置一致性
- **配置驱动**: 通过配置文件控制日志行为

## 📊 数据模型

### 新闻项 (NewsItem)

```python
class NewsItem:
    id: str              # 唯一标识
    title: str           # 新闻标题
    content: str         # 新闻内容
    source: str          # 新闻来源
    publish_time: datetime  # 发布时间
    url: str             # 原始链接
    category: str        # 新闻分类
    keywords: List[str]  # 关键词列表
    created_at: datetime # 创建时间
    updated_at: datetime # 更新时间
```

### 分析结果 (AnalysisResult)

```python
class AnalysisResult:
    news_id: str          # 新闻ID
    affected_sectors: List[str]  # 影响板块
    impact_score: float   # 影响评分(-10到10)
    impact_level: str     # 影响级别(高/中/低)
    sentiment: str        # 情感倾向(正面/负面/中性)
    summary: str          # 分析摘要
    recommendation: str   # 投资建议
    analysis_time: datetime  # 分析时间
```

## 🔍 新闻源说明

### RSS源优势
- **实时性强**: RSS源更新及时
- **结构化数据**: 标准化的数据格式
- **稳定可靠**: 官方提供的数据源
- **免费使用**: 大多数RSS源免费开放

### 支持的RSS源

1. **东方财富**: 综合财经资讯
2. **财联社**: 实时财经快讯
3. **格隆汇**: 港股和A股资讯
4. **雪球**: 投资社区热门讨论

### API源特点
- **数据准确**: 直接来自官方接口
- **更新及时**: 实时或准实时数据
- **结构完整**: 包含完整的元数据
- **批量获取**: 支持批量数据获取

## 🚨 注意事项

### 使用限制
- 请遵守各新闻源的使用条款和频率限制
- 网页爬虫功能请谨慎使用，避免对目标网站造成压力
- DeepSeek API调用需要API密钥，请合理控制使用频率

### 数据隐私
- 本系统仅收集公开的新闻信息
- 不存储任何个人隐私数据
- 邮件配置信息请妥善保管

### 性能优化
- 数据库会自动清理30天前的旧数据
- 日志文件会自动轮转，避免占用过多磁盘空间
- 并发数量可通过配置文件调整

## 📦 部署说明

### 🐳 Docker部署（推荐）

Docker部署是最简单和最可靠的部署方式：

```bash
# 快速启动
docker-compose up -d

# 查看状态
./deploy.sh status    # Linux/macOS
docker-compose ps     # Windows

# 管理服务
./deploy.sh start|stop|restart|logs    # Linux/macOS
docker-compose start|stop|restart      # Windows
```

**优势**:
- ✅ 环境隔离，避免依赖冲突
- ✅ 一键部署，简化运维
- ✅ 自动重启，故障恢复
- ✅ 资源限制，防止系统过载
- ✅ 数据持久化，安全可靠

> 📖 **完整的Docker部署指南**: [DOCKER_DEPLOY.md](./DOCKER_DEPLOY.md)

### 🖥️ 传统部署

对于不使用Docker的环境，可以使用传统方式部署：

```bash
# 1. 安装Python依赖
pip install -r requirements.txt

# 2. 配置应用
cp config/config.yaml.template config/config.yaml
# 编辑配置文件

# 3. 启动服务
python main.py scheduler-run
```

### 🚀 生产环境建议

- **Docker部署**: 推荐用于生产环境，便于管理和扩展
- **资源监控**: 使用 `docker stats` 监控资源使用情况
- **日志管理**: 配置日志轮转，避免磁盘空间不足
- **备份策略**: 定期备份配置文件和数据库
- **安全考虑**: 使用防火墙限制不必要的端口访问

## 🛠️ 开发和扩展

### 添加新的新闻源

1. 在 `config/config.yaml` 中添加新闻源配置
2. 如需要特殊处理逻辑，在 `news_collector.py` 中添加对应方法
3. 测试新闻源的数据格式和访问频率

### 自定义分析逻辑

1. 修改 `ai_analyzer.py` 中的提示词模板
2. 调整 `config.yaml` 中的AI分析参数
3. 扩展 `AnalysisResult` 数据模型以支持更多字段

### 添加新的通知方式

1. 创建新的通知模块（如微信、钉钉等）
2. 在主流程中集成新的通知方式
3. 在配置文件中添加相应的配置选项

## 📝 许可证

本项目采用 MIT 许可证。详情请参阅 [LICENSE](LICENSE) 文件。

## 🤝 贡献指南

欢迎提交问题报告和功能建议！如果你想要贡献代码：

1. Fork 本仓库
2. 创建你的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的修改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

## 📞 支持与反馈

如果你在使用过程中遇到问题，请：

1. 查看日志文件 `data/logs/app.log` 获取详细错误信息
2. 检查配置文件是否正确设置
3. 确认网络连接和API密钥有效性
4. 在 Issues 中提交问题报告

---

**祝您使用愉快！** 🎉 