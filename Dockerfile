# AI新闻收集系统 - 多源优化Dockerfile
# 支持多架构: linux/amd64, linux/arm64
# 智能选择最优软件源，提高构建成功率
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

# 智能选择最优APT源
RUN set -e; \
    echo "Building for platform: $BUILDPLATFORM -> $TARGETPLATFORM" && \
    echo "Target architecture: $TARGETARCH" && \
    \
    # 检测网络环境并选择最优APT源
    if command -v curl >/dev/null 2>&1; then \
        # 尝试检测网络环境选择最优源
        if timeout 10 curl -s --connect-timeout 5 https://mirrors.tuna.tsinghua.edu.cn >/dev/null 2>&1; then \
            echo "检测到国内网络环境，使用清华镜像源"; \
            echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye main" > /etc/apt/sources.list; \
            echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye-updates main" >> /etc/apt/sources.list; \
            echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bullseye-security main" >> /etc/apt/sources.list; \
        elif timeout 10 curl -s --connect-timeout 5 http://deb.debian.org >/dev/null 2>&1; then \
            echo "使用官方Debian源"; \
            echo "deb http://deb.debian.org/debian bullseye main" > /etc/apt/sources.list; \
            echo "deb http://deb.debian.org/debian-security bullseye-security main" >> /etc/apt/sources.list; \
            echo "deb http://deb.debian.org/debian bullseye-updates main" >> /etc/apt/sources.list; \
        else \
            echo "网络检测失败，使用默认源配置"; \
        fi; \
    fi

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

# 智能配置PyPI源
RUN set -e; \
    mkdir -p /root/.pip && \
    \
    # 检测网络环境并配置最优PyPI源
    if timeout 10 curl -s --connect-timeout 5 https://pypi.tuna.tsinghua.edu.cn >/dev/null 2>&1; then \
        echo "配置国内PyPI镜像源..."; \
        echo "[global]" > /root/.pip/pip.conf; \
        echo "index-url = https://pypi.tuna.tsinghua.edu.cn/simple/" >> /root/.pip/pip.conf; \
        echo "extra-index-url = https://mirrors.aliyun.com/pypi/simple/" >> /root/.pip/pip.conf; \
        echo "                  https://pypi.douban.com/simple/" >> /root/.pip/pip.conf; \
        echo "                  https://pypi.org/simple/" >> /root/.pip/pip.conf; \
        echo "trusted-host = pypi.tuna.tsinghua.edu.cn" >> /root/.pip/pip.conf; \
        echo "               mirrors.aliyun.com" >> /root/.pip/pip.conf; \
        echo "               pypi.douban.com" >> /root/.pip/pip.conf; \
        echo "               pypi.org" >> /root/.pip/pip.conf; \
        echo "timeout = 60" >> /root/.pip/pip.conf; \
        echo "retries = 5" >> /root/.pip/pip.conf; \
    else \
        echo "配置国际PyPI源..."; \
        echo "[global]" > /root/.pip/pip.conf; \
        echo "index-url = https://pypi.org/simple/" >> /root/.pip/pip.conf; \
        echo "extra-index-url = https://pypi.tuna.tsinghua.edu.cn/simple/" >> /root/.pip/pip.conf; \
        echo "                  https://mirrors.aliyun.com/pypi/simple/" >> /root/.pip/pip.conf; \
        echo "trusted-host = pypi.org" >> /root/.pip/pip.conf; \
        echo "               pypi.tuna.tsinghua.edu.cn" >> /root/.pip/pip.conf; \
        echo "               mirrors.aliyun.com" >> /root/.pip/pip.conf; \
        echo "timeout = 60" >> /root/.pip/pip.conf; \
        echo "retries = 5" >> /root/.pip/pip.conf; \
    fi

# 复制requirements文件
COPY requirements.txt .

# 智能安装Python依赖（多源重试策略）
RUN set -e; \
    echo "开始安装Python依赖包..."; \
    \
    # 定义多个PyPI源
    PYPI_SOURCES=( \
        "https://pypi.org/simple/" \
        "https://pypi.tuna.tsinghua.edu.cn/simple/" \
        "https://mirrors.aliyun.com/pypi/simple/" \
        "https://pypi.douban.com/simple/" \
    ); \
    \
    # 尝试不同的源直到成功
    for i in "${!PYPI_SOURCES[@]}"; do \
        source="${PYPI_SOURCES[$i]}"; \
        echo "尝试第$((i+1))个源: $source"; \
        if pip install --no-cache-dir -i "$source" -r requirements.txt; then \
            echo "✅ 使用源 $source 安装成功"; \
            break; \
        else \
            echo "❌ 源 $source 安装失败"; \
            if [ $i -eq $((${#PYPI_SOURCES[@]}-1)) ]; then \
                echo "🚨 所有PyPI源都失败了"; \
                exit 1; \
            fi; \
        fi; \
    done

# 复制项目文件
COPY . .

# 创建必要的目录并设置权限
RUN mkdir -p data/logs data/database data/reports && \
    chmod +x main.py && \
    chown -R root:root /app

# 暴露端口
EXPOSE 8080

# 增强的健康检查
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
CMD ["python", "main.py", "scheduler-run"] 