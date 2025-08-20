# AI新闻收集系统 - 优化Dockerfile
# 支持多架构: linux/amd64, linux/arm64
FROM --platform=$BUILDPLATFORM python:3.11-slim

# 设置构建参数
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG TARGETOS
ARG TARGETARCH

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    ca-certificates \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖（依赖Docker daemon的镜像源配置）
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建必要的目录并设置权限
RUN mkdir -p data/logs data/database data/reports && \
    chmod +x main.py && \
    chown -R root:root /app

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=5 \
    CMD python -c "import sys, os; \
        from src.config_manager import ConfigManager; \
        from src.utils.database import DatabaseManager; \
        try: \
            config = ConfigManager(); \
            db = DatabaseManager(config.get('database.path')); \
            print('✅ 健康检查通过'); \
            sys.exit(0); \
        except Exception as e: \
            print(f'❌ 健康检查失败: {e}'); \
            sys.exit(1)"

# 设置启动命令
CMD ["python", "main.py", "daemon"] 