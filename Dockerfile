FROM python:3.11-slim

LABEL maintainer="your-email@example.com"
LABEL description="个人主页导航系统 - 支持分类导航、文章展示、权限控制"
LABEL version="2.0.0"

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ app/
COPY templates/ templates/
COPY static/css/ static/css/
COPY static/js/ static/js/
COPY alembic/ alembic/
COPY alembic.ini .
COPY scripts/ scripts/

# 创建目录
RUN mkdir -p /app/data /app/articles /app/static/icons /app/data/backups

# 环境变量说明（运行时必须设置）
# DATABASE_URL - PostgreSQL 连接字符串
# SECRET_KEY - JWT 密钥
# ADMIN_USERNAME - 管理员用户名
# ADMIN_PASSWORD - 明文密码（启动时自动哈希）

# Copy entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
