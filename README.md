# Nav System - 个人导航与文章系统

[Demo](https://navsystem-navsystem.up.railway.app/) | 预览账号: `admin` / `admin123`

基于 FastAPI + PostgreSQL 的个人主页系统，集成导航站和 Markdown 文章展示功能。采用 **Zen-iOS Hybrid** 设计语言，提供极致的毛玻璃效果和物理触感。

## ✨ 功能特性

### 导航站
- 🔖 分类展示常用链接，支持权限控制
- 🎨 自动获取网站 favicon
- 📏 链接大小可调（小/中/大）
- ⏰ 实时时钟显示

### 文章系统
- 📝 Markdown 文章在线展示与编辑
- 📂 目录结构浏览（可折叠）
- 🔒 目录权限控制
- 🔄 Obsidian 插件同步支持

### 管理功能
- ⚙️ 站点设置（标题、备案信息、受保护目录等）
- 📊 访问记录与更新记录
- 🌓 深色/浅色主题切换
- 🛡️ 暴力破解防护（5次失败锁定15分钟）

## 🚀 快速开始

### 方式一：Docker Compose（推荐）

**1. 配置环境变量**

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，配置数据库和管理员信息
nano .env
```

`.env` 配置示例：
```env
# 数据库配置
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=your_remote_db_host  # 远程数据库地址
DB_PORT=5432
DB_NAME=nav_system

# 安全配置
SECRET_KEY=your-random-32-character-secret-key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_admin_password
```

**2. 启动应用**

```bash
# 构建并启动容器
docker compose up -d --build

# 查看日志
docker compose logs -f

# 停止容器
docker compose down
```

访问 `http://localhost:8001`

### 方式二：Docker Run（使用预构建镜像）

**1. 拉取镜像**

```bash
docker pull aniian/nav-system:latest
```

**2. 运行容器**

```bash
docker run -d \
  --name nav-system \
  -p 8001:8000 \
  --env-file .env \
  -v $(pwd)/articles:/app/articles \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/static/icons:/app/static/icons \
  --restart unless-stopped \
  aniian/nav-system:latest
```

**3. 管理容器**

```bash
# 查看日志
docker logs -f nav-system

# 停止容器
docker stop nav-system

# 启动容器
docker start nav-system

# 删除容器
docker rm -f nav-system
```

### 方式三：本地开发

**1. 环境准备**

```bash
# 创建 Python 环境
conda create -n homepage python=3.9
conda activate homepage

# 安装依赖
pip install -r requirements.txt
```

**2. 配置环境变量**

创建 `.env` 文件（参考上面的配置示例）

**3. 启动服务**

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

访问 `http://localhost:8001`

## 📦 Docker 配置说明

### 端口映射
- `-p 8001:8000`：将容器的 8000 端口映射到主机的 8001 端口

### 数据持久化（Volume 挂载）
- `./articles:/app/articles`：Markdown 文章目录
- `./data:/app/data`：数据文件目录
- `./static/icons:/app/static/icons`：网站图标目录

### 环境变量
使用 `--env-file .env` 加载环境变量，或使用 `-e` 单独指定：

```bash
docker run -d \
  -e DB_HOST=your_db_host \
  -e DB_PASSWORD=your_password \
  -e SECRET_KEY=your_secret \
  -e ADMIN_USERNAME=admin \
  -e ADMIN_PASSWORD=admin123 \
  ...
```

## 🗄️ 数据库配置

### PostgreSQL（推荐）

**使用远程数据库：**
```env
DB_HOST=your_remote_db_host
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=nav_system
```

**使用本地 PostgreSQL：**
```bash
# 安装 PostgreSQL
sudo apt install postgresql postgresql-contrib

# 创建数据库
sudo -u postgres psql -c "CREATE DATABASE nav_system;"
sudo -u postgres psql -c "CREATE USER postgres WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE nav_system TO postgres;"
```

### 数据迁移

如果有旧版 JSON 数据需要迁移到 PostgreSQL：

```bash
python scripts/migrate_data.py
```

## 🌐 生产部署

### Railway 一键部署

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/MxkRwo?referralCode=TEG7-_)

### Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🔌 Obsidian 插件

**安装：**
1. 将 `obsidian-plugin/` 复制到 `.obsidian/plugins/nav-system-sync/`
2. 在 Obsidian 设置中启用插件
3. 配置 API 地址和 JWT Token

**使用：**
- 右键文件 → "上传到 Nav System"
- 右键文件夹 → "上传文件夹到 Nav System"

**批量同步脚本：**
```bash
python scripts/sync_articles.py \
  --vault /path/to/obsidian/vault \
  --api https://your-domain.com \
  --token YOUR_JWT_TOKEN
```

## 📡 API 接口

### 认证
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/logout` | 登出 |
| GET | `/api/auth/me` | 当前用户信息 |

### 导航链接
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/links` | 获取链接列表 | 否 |
| POST | `/api/links` | 添加链接 | 是 |
| PUT | `/api/links/{id}` | 修改链接 | 是 |
| DELETE | `/api/links/{id}` | 删除链接 | 是 |

### 分类
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/categories` | 添加分类 | 是 |
| PUT | `/api/categories/{name}` | 修改分类 | 是 |
| DELETE | `/api/categories/{name}` | 删除分类 | 是 |

### 文章
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/articles` | 文章列表 | 否 |
| GET | `/api/articles/{path}` | 文章内容 | 否* |
| POST | `/api/articles/sync` | 同步文章 | 是 |
| PUT | `/api/articles/{path}` | 编辑文章 | 是 |
| DELETE | `/api/articles/{path}` | 删除文章 | 是 |

> *受保护目录下的文章需要登录

### 目录管理
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/folders` | 目录列表 | 是 |
| POST | `/api/folders?name={name}` | 创建目录 | 是 |
| PUT | `/api/folders/{name}` | 重命名目录 | 是 |
| DELETE | `/api/folders/{name}` | 删除目录 | 是 |

### 设置与日志
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/settings` | 获取设置 | 否 |
| PUT | `/api/settings` | 更新设置 | 是 |
| GET | `/api/visits` | 访问记录 | 是 |
| GET | `/api/updates` | 更新记录 | 是 |

## 🛠️ 技术栈

- **后端**: Python FastAPI
- **数据库**: PostgreSQL + SQLAlchemy (async)
- **认证**: JWT Token
- **前端**: HTML + CSS + JavaScript + Jinja2
- **设计**: Zen-iOS Hybrid（毛玻璃效果 + 物理触感）

## 📁 项目结构

```
nav_system/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置管理
│   ├── database.py          # 数据库连接
│   ├── models/              # SQLAlchemy 模型
│   ├── schemas/             # Pydantic 模型
│   ├── routers/             # API 路由
│   ├── services/            # 业务逻辑
│   └── utils/               # 工具函数
├── templates/               # HTML 模板
├── static/                  # 静态资源
│   ├── css/style.css        # Zen-iOS Hybrid 样式
│   ├── js/main.js           # 前端逻辑
│   └── icons/               # 网站图标
├── articles/                # Markdown 文章
├── data/                    # JSON 数据（旧版兼容）
├── scripts/                 # 工具脚本
├── alembic/                 # 数据库迁移
├── tests/                   # 测试
├── obsidian-plugin/         # Obsidian 同步插件
├── docker-compose.yml       # Docker Compose 配置
├── Dockerfile               # Docker 镜像构建
├── requirements.txt         # Python 依赖
└── .env                     # 环境变量配置
```

## ⚠️ 注意事项

- 数据库密码中的特殊字符需要 URL 编码（如 `@` → `%40`）
- 生产环境建议使用 Nginx 反向代理并启用 HTTPS
- 定期备份数据库和 `articles/` 目录
- `SECRET_KEY` 必须是随机生成的 32 字符以上字符串
- 首次启动会自动创建数据库表结构

## 📄 License

MIT License
