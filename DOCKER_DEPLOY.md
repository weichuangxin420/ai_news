# 🐳 AI新闻收集系统 - Docker部署指南

## 📋 目录
- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [详细部署步骤](#详细部署步骤)
- [配置说明](#配置说明)
- [服务管理](#服务管理)
- [数据持久化](#数据持久化)
- [监控与日志](#监控与日志)
- [故障排除](#故障排除)
- [性能调优](#性能调优)
- [安全建议](#安全建议)

## 🔧 系统要求

### 最低配置
- **CPU**: 1核心
- **内存**: 1GB RAM
- **存储**: 5GB 可用空间
- **操作系统**: Linux/macOS/Windows
- **Docker**: 20.10+ 
- **Docker Compose**: 1.29+

### 推荐配置
- **CPU**: 2核心
- **内存**: 2GB RAM
- **存储**: 10GB 可用空间
- **网络**: 稳定的互联网连接

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/yourusername/ai_news.git
cd ai_news
```

### 2. 配置应用
```bash
# 复制配置模板
cp config/config.yaml.template config/config.yaml

# 编辑配置文件，填入你的API密钥和邮箱信息
vim config/config.yaml  # 或使用其他编辑器
```

### 3. 一键部署
```bash
# Linux/macOS
./deploy.sh build
./deploy.sh start

# Windows (PowerShell)
docker-compose build
docker-compose up -d
```

### 4. 验证部署
```bash
# 检查服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f
```

## 📖 详细部署步骤

### 步骤 1: 环境准备

#### 安装Docker（Ubuntu/Debian示例）
```bash
# 更新包索引
sudo apt update

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

#### Windows Docker Desktop
1. 下载并安装 [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. 启动Docker Desktop
3. 确保WSL2后端已启用

### 步骤 2: 项目配置

#### 配置文件说明
编辑 `config/config.yaml`，填入以下关键信息：

```yaml
# AI分析配置
ai_analysis:
  deepseek:
    api_key: "your_deepseek_api_key"  # DeepSeek API密钥

# 邮件配置
email:
  smtp:
    username: "your_email@163.com"    # 邮箱地址
    password: "your_auth_password"    # 授权密码
  recipients:
    - "recipient@example.com"         # 收件人列表
```

### 步骤 3: 构建和启动

#### 方式1: 使用部署脚本（推荐）
```bash
# 构建镜像
./deploy.sh build

# 启动服务
./deploy.sh start

# 查看状态
./deploy.sh status
```

#### 方式2: 直接使用Docker Compose
```bash
# 构建镜像
docker-compose build

# 启动服务（后台运行）
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 步骤 4: 验证部署

```bash
# 检查容器状态
docker-compose ps

# 检查健康状态
docker inspect --format='{{.State.Health.Status}}' ai_news_app

# 测试功能
docker-compose exec ai-news python main.py test
```

## ⚙️ 配置说明

### Docker Compose 配置

#### 端口映射
```yaml
ports:
  - "8080:8080"  # Web界面端口（如果需要）
```

#### 数据卷挂载
```yaml
volumes:
  - ./data:/app/data                          # 数据目录
  - ./config/config.yaml:/app/config/config.yaml:ro  # 配置文件（只读）
  - ./logs:/app/data/logs                     # 日志目录
```

#### 环境变量
```yaml
environment:
  - TZ=Asia/Shanghai      # 时区设置
  - PYTHONUNBUFFERED=1   # Python输出不缓冲
```

#### 资源限制
```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'      # CPU限制
      memory: 1G       # 内存限制
    reservations:
      cpus: '0.5'      # CPU预留
      memory: 512M     # 内存预留
```

## 🔧 服务管理

### 使用部署脚本管理
```bash
./deploy.sh start      # 启动服务
./deploy.sh stop       # 停止服务
./deploy.sh restart    # 重启服务
./deploy.sh status     # 查看状态
./deploy.sh logs       # 查看日志
./deploy.sh update     # 更新服务
./deploy.sh backup     # 备份数据
./deploy.sh clean      # 清理资源
```

### 使用Docker Compose管理
```bash
docker-compose up -d           # 启动服务
docker-compose down            # 停止服务
docker-compose restart        # 重启服务
docker-compose ps              # 查看状态
docker-compose logs -f         # 查看日志
docker-compose pull            # 拉取最新镜像
docker-compose build --no-cache  # 重新构建镜像
```

### 进入容器调试
```bash
# 进入运行中的容器
docker-compose exec ai-news bash

# 运行特定命令
docker-compose exec ai-news python main.py test
docker-compose exec ai-news python main.py collect
```

## 💾 数据持久化

### 数据目录结构
```
data/
├── logs/           # 应用日志
├── database/       # SQLite数据库
└── reports/        # 生成的报告
```

### 备份数据
```bash
# 使用部署脚本备份
./deploy.sh backup

# 手动备份
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz data/ config/config.yaml
```

### 恢复数据
```bash
# 停止服务
docker-compose down

# 恢复数据
tar -xzf backup_YYYYMMDD_HHMMSS.tar.gz

# 启动服务
docker-compose up -d
```

## 📊 监控与日志

### 查看实时日志
```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f ai-news

# 查看最近100行日志
docker-compose logs --tail=100 ai-news
```

### 容器监控
```bash
# 查看资源使用情况
docker stats ai_news_app

# 查看容器详细信息
docker inspect ai_news_app

# 查看健康检查状态
docker inspect --format='{{.State.Health.Status}}' ai_news_app
```

### 系统监控
```bash
# 查看磁盘使用
df -h

# 查看Docker磁盘使用
docker system df

# 清理未使用的资源
docker system prune
```

## 🔍 故障排除

### 常见问题

#### 1. 容器启动失败
```bash
# 检查容器日志
docker-compose logs ai-news

# 检查配置文件
cat config/config.yaml

# 重新构建镜像
docker-compose build --no-cache
```

#### 2. 网络连接问题
```bash
# 测试网络连接
docker-compose exec ai-news ping google.com

# 检查DNS
docker-compose exec ai-news nslookup api.deepseek.com

# 重启网络
docker-compose down && docker-compose up -d
```

#### 3. 邮件发送失败
```bash
# 测试邮件连接
docker-compose exec ai-news python main.py email-test

# 检查邮件配置
docker-compose exec ai-news python -c "
from src.config_manager import ConfigManager
config = ConfigManager()
print(config.get('email.smtp'))
"
```

#### 4. 数据库问题
```bash
# 检查数据库文件
ls -la data/database/

# 重建数据库
docker-compose exec ai-news python -c "
from src.utils.database import DatabaseManager
db = DatabaseManager()
db.init_database()
"
```

### 调试模式
```bash
# 启动调试容器
docker-compose run --rm ai-news bash

# 在容器中手动运行
python main.py test
python main.py collect
python main.py analyze
```

## 🚀 性能调优

### 资源优化
```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '2.0'      # 增加CPU限制
      memory: 2G       # 增加内存限制
```

### 并发优化
```yaml
# config/config.yaml
news_collection:
  concurrent_limit: 10  # 增加并发数
  request_timeout: 30   # 调整超时时间
```

### 存储优化
```bash
# 定期清理日志
find data/logs -name "*.log" -mtime +7 -delete

# 压缩旧日志
gzip data/logs/*.log

# 清理Docker缓存
docker system prune -f
```

## 🔒 安全建议

### 1. 配置文件安全
```bash
# 设置配置文件权限
chmod 600 config/config.yaml

# 使用环境变量（生产环境推荐）
export DEEPSEEK_API_KEY="your_api_key"
export EMAIL_PASSWORD="your_password"
```

### 2. 网络安全
```yaml
# docker-compose.yml - 限制网络访问
networks:
  ai_news_network:
    driver: bridge
    internal: true  # 内部网络
```

### 3. 容器安全
```dockerfile
# Dockerfile - 使用非root用户
RUN addgroup --system app && adduser --system --group app
USER app
```

### 4. 数据安全
```bash
# 加密敏感数据
gpg --symmetric config/config.yaml

# 定期备份
./deploy.sh backup
```

## 📝 更新部署

### 代码更新
```bash
# 拉取最新代码
git pull

# 重新构建和部署
./deploy.sh update
```

### 配置更新
```bash
# 修改配置
vim config/config.yaml

# 重启服务应用配置
docker-compose restart
```

### 依赖更新
```bash
# 更新requirements.txt后重新构建
docker-compose build --no-cache
docker-compose up -d
```

## 🆘 技术支持

如果遇到问题，请提供以下信息：

1. **系统信息**:
   ```bash
   uname -a
   docker --version
   docker-compose --version
   ```

2. **容器状态**:
   ```bash
   docker-compose ps
   docker-compose logs --tail=50
   ```

3. **配置信息** (脱敏后):
   ```bash
   cat config/config.yaml | grep -v "api_key\|password"
   ```

---

🎉 **部署完成！** 你的AI新闻收集系统现在应该正在Docker容器中运行。系统将每30分钟自动收集新闻、进行AI分析并发送邮件报告。 