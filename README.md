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

## 📦 完整部署指南

### 📋 部署方式选择

| 部署方式 | 适用场景 | 难度 | 推荐指数 |
|---------|---------|------|---------|
| 🐳 Docker部署 | 开发、生产环境 | ⭐ | ⭐⭐⭐⭐⭐ |
| 🖥️ 传统部署 | 特殊环境需求 | ⭐⭐⭐ | ⭐⭐⭐ |

### 🐳 Docker部署（推荐）

#### 系统要求
- **最低配置**: 1核CPU + 1GB内存 + 5GB存储
- **推荐配置**: 2核CPU + 2GB内存 + 10GB存储
- **环境要求**: Docker 20.10+ 和 Docker Compose 1.29+

#### 快速开始
```bash
# 1. 克隆项目
git clone https://github.com/yourusername/ai_news.git
cd ai_news

# 2. 检查系统兼容性
./deploy.sh check

# 3. 安装Docker环境（首次部署）
sudo ./deploy.sh install

# 4. 配置应用
cp config/config.yaml.template config/config.yaml
# 编辑config/config.yaml，填入API密钥和邮箱信息

# 5. 构建和启动
./deploy.sh build
./deploy.sh start
```

#### 服务管理命令
```bash
# 🔧 环境管理
./deploy.sh check          # 检查系统兼容性
sudo ./deploy.sh install   # 安装Docker环境

# 🚀 服务管理
./deploy.sh build          # 构建镜像
./deploy.sh start          # 启动服务
./deploy.sh stop           # 停止服务
./deploy.sh restart        # 重启服务
./deploy.sh status         # 查看状态
./deploy.sh logs           # 查看日志

# 🛠️ 维护操作
./deploy.sh update         # 更新服务
./deploy.sh backup         # 备份数据
./deploy.sh clean          # 清理资源

# 📊 监控命令
docker stats ai_news_app   # 查看资源使用
docker-compose ps          # 查看容器状态
```

#### Docker环境安装
如果系统没有Docker，脚本会自动安装：

**Ubuntu/Debian**:
```bash
sudo ./deploy.sh install
```

**手动安装Docker**:
```bash
# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

**Windows用户**:
1. 下载并安装 [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. 启动Docker Desktop，确保WSL2后端已启用
3. 使用PowerShell运行：`docker-compose build && docker-compose up -d`

### 🖥️ 传统部署

#### 环境准备
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv git

# CentOS/RHEL
# CentOS 8+/RHEL 8+ 使用 dnf
sudo dnf install python3 python3-pip git
# CentOS 7/RHEL 7 使用 yum
# sudo yum install python3 python3-pip git

# 检查Python版本（需要3.8+）
python3 --version
```

#### 安装步骤
```bash
# 1. 克隆项目
git clone https://github.com/yourusername/ai_news.git
cd ai_news

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置应用
cp config/config.yaml.template config/config.yaml
# 编辑config/config.yaml文件

# 5. 创建数据目录
mkdir -p data/logs data/database data/reports

# 6. 测试运行
python main.py test
python main.py collect
python main.py analyze

# 7. 启动服务
python main.py scheduler-run
```

#### 系统服务配置（生产环境）
```bash
# 创建systemd服务文件
sudo vim /etc/systemd/system/ai-news.service
```

```ini
[Unit]
Description=AI News Collection and Analysis Service
After=network.target

[Service]
Type=simple
User=your_user
Group=your_group
WorkingDirectory=/path/to/ai_news
Environment=PATH=/path/to/ai_news/venv/bin
ExecStart=/path/to/ai_news/venv/bin/python main.py scheduler-run
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 启用服务
sudo systemctl daemon-reload
sudo systemctl enable ai-news.service
sudo systemctl start ai-news.service
```

### ⚙️ 配置说明

#### 必需配置项
在 `config/config.yaml` 中需要配置：

```yaml
# DeepSeek API配置
ai_analysis:
  deepseek:
    api_key: "your_deepseek_api_key"

# 邮箱配置
email:
  smtp:
    username: "your_email@163.com"
    password: "your_auth_password"
  recipients:
    - "recipient@example.com"
```

#### 性能优化配置
```yaml
# 并发设置
news_collection:
  concurrent_limit: 10      # 并发请求数
  request_timeout: 30       # 请求超时时间

# 调度设置
scheduler:
  pipeline_interval: 30     # 执行间隔（分钟）
  email_recent_hours: 1     # 邮件包含最近几小时的分析

# 数据管理
database:
  retention:
    max_days: 7             # 数据保留天数
```

### 🔍 故障排除

#### 常见问题解决

**1. Docker容器启动失败**
```bash
# 检查日志
docker-compose logs ai-news

# 重新构建
docker-compose build --no-cache
docker-compose up -d
```

**2. 网络连接问题**
```bash
# 测试API连接
curl -I https://api.deepseek.com
curl -I https://smtp.163.com:465

# 检查防火墙
sudo ufw status
```

**3. 邮件发送失败**
```bash
# 测试SMTP连接
python main.py email-test

# 163邮箱设置检查
# 1. 开启SMTP服务
# 2. 获取授权密码（不是登录密码）
# 3. 确认端口设置正确
```

**4. 权限问题**
```bash
# 检查文件权限
ls -la config/config.yaml
ls -la data/

# 修复权限
chmod 644 config/config.yaml
sudo chown -R $USER:$USER data/
```

### 📊 监控与维护

#### 性能监控
```bash
# 系统资源
htop
df -h
free -h

# Docker资源
docker stats
docker system df

# 应用日志
tail -f data/logs/app.log
```

#### 数据备份
```bash
# 使用脚本备份
./deploy.sh backup

# 手动备份
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz data/ config/config.yaml
```

#### 定期维护
```bash
# 更新系统
./deploy.sh update

# 清理资源
docker system prune -f

# 检查磁盘空间
df -h
```

### 🔒 安全建议

1. **网络安全**
   - 配置防火墙，只开放必要端口
   - 使用SSH密钥认证
   - 禁用root直接登录

2. **应用安全**
   - 定期更新系统和依赖包
   - 使用强密码和API密钥
   - 限制配置文件权限：`chmod 600 config/config.yaml`

3. **数据安全**
   - 定期备份配置和数据
   - 监控异常访问
   - 使用HTTPS连接

### 🚀 生产环境部署

#### 推荐架构
- **Docker部署**: 便于管理和扩展
- **反向代理**: 使用Nginx处理外部访问
- **监控系统**: 配置日志聚合和告警
- **备份策略**: 自动化数据备份

#### 容器资源限制
```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 512M
```

#### 更新策略
```bash
# Docker部署更新
git pull
./deploy.sh update

# 传统部署更新
git pull
source venv/bin/activate
pip install -r requirements.txt
systemctl restart ai-news
```

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