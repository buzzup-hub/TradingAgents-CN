# 使用官方Python镜像替代GitHub Container Registry
FROM python:3.10-slim-bookworm

# 安装uv包管理器，按照多个镜像源依次尝试
RUN set -e; \
    for src in \
        https://mirrors.aliyun.com/pypi/simple \
        https://pypi.tuna.tsinghua.edu.cn/simple \
        https://pypi.doubanio.com/simple \
        https://pypi.org/simple; do \
      echo "Try installing uv from $src"; \
      if pip install --no-cache-dir -i "$src" uv; then \
        echo "Installed uv from $src"; \
        break; \
      else \
        echo "Failed at $src, trying next mirror..."; \
      fi; \
    done

WORKDIR /app

RUN mkdir -p /app/data /app/logs

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 配置APT镜像源
RUN rm -f /etc/apt/sources.list.d/debian.sources && \
    cat <<'EOF' > /etc/apt/sources.list
deb https://mirrors.aliyun.com/debian/ bookworm main non-free non-free-firmware
deb https://mirrors.aliyun.com/debian/ bookworm-updates main non-free non-free-firmware
deb https://mirrors.aliyun.com/debian-security bookworm-security main non-free non-free-firmware
EOF

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wkhtmltopdf \
    xvfb \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    fonts-liberation \
    pandoc \
    procps \
    && rm -rf /var/lib/apt/lists/*

# 启动Xvfb虚拟显示器
RUN echo '#!/bin/bash\nXvfb :99 -screen 0 1024x768x24 -ac +extension GLX &\nexport DISPLAY=:99\nexec "$@"' > /usr/local/bin/start-xvfb.sh \
    && chmod +x /usr/local/bin/start-xvfb.sh

COPY requirements.txt .

#多源轮询安装依赖
RUN set -e; \
    for src in \
        https://mirrors.aliyun.com/pypi/simple \
        https://pypi.tuna.tsinghua.edu.cn/simple \
        https://pypi.doubanio.com/simple \
        https://pypi.org/simple; do \
      echo "Try installing from $src"; \
      pip install --no-cache-dir -r requirements.txt -i $src && break; \
      echo "Failed at $src, try next"; \
    done

# 复制日志配置文件
COPY config/ ./config/

COPY . .

EXPOSE 8501

CMD ["python", "-m", "streamlit", "run", "web/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
