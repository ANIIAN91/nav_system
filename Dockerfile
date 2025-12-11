FROM python:3.11-slim

LABEL maintainer="your-email@example.com"
LABEL description="个人主页导航系统 - 支持分类导航、文章展示、权限控制"
LABEL version="1.1.0"

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY main.py .
COPY templates/ templates/
COPY static/css/ static/css/
COPY static/js/ static/js/

# 创建目录
RUN mkdir -p /app/data /app/articles /app/static/icons /app/defaults

# 创建默认数据文件（放在 /app/defaults 不会被 volume 覆盖）
RUN echo '{"categories":[{"name":"常用","auth_required":false,"links":[]},{"name":"私密","auth_required":true,"links":[]}]}' > /app/defaults/links.json \
    && echo '{"icp":"","copyright":"","article_page_title":"文章"}' > /app/defaults/settings.json

# 复制启动脚本
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# 环境变量说明（运行时必须设置）
# SECRET_KEY - JWT 密钥
# ADMIN_USERNAME - 管理员用户名
# ADMIN_PASSWORD - 明文密码（启动时自动哈希）

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/settings || exit 1

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
