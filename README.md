# Nav System - 个人导航与文章系统

[Demo](https://navsystem-navsystem.up.railway.app/) | 预览账号: `admin` / `admin123`

基于 FastAPI + SQLite 的个人主页系统，集成导航站和 Markdown 文章展示功能。采用 **Zen-iOS Hybrid** 设计语言，提供极致的毛玻璃效果和物理触感。

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
# 数据库配置（可选，默认使用 SQLite）
# DATABASE_URL=sqlite+aiosqlite:///./data/nav_system.db

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

### API 前缀

本项目 API 统一使用 `/api/v1` 前缀（例如：`/api/v1/links`、`/api/v1/auth/login`）。

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
  -e SECRET_KEY=your_secret \
  -e ADMIN_USERNAME=admin \
  -e ADMIN_PASSWORD=admin123 \
  ...
```

## 🗄️ 数据库说明

本项目使用 **SQLite** 作为数据库，具有以下优势：

- ✅ **零配置**：无需安装和配置外部数据库服务
- ✅ **单文件存储**：数据库文件位于 `data/nav_system.db`
- ✅ **易于备份**：直接复制 `.db` 文件即可完成备份
- ✅ **轻量高效**：适合个人使用场景，性能优异

### 数据持久化

确保挂载 `data` 目录以持久化数据库：

```bash
-v $(pwd)/data:/app/data
```

### 自定义数据库路径（可选）

如需使用其他数据库或自定义路径，可通过环境变量指定：

```env
# 使用自定义 SQLite 路径
DATABASE_URL=sqlite+aiosqlite:///./custom/path/database.db
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

Nav System 提供 Obsidian 插件，可以将 Obsidian 笔记同步到导航系统的文章模块。

### 安装步骤

1. **复制插件文件**
   ```bash
   # 在 Obsidian vault 目录下
   mkdir -p .obsidian/plugins/nav-system-sync
   cp -r /path/to/nav_system/obsidian-plugin/* .obsidian/plugins/nav-system-sync/
   ```

2. **启用插件**
   - 打开 Obsidian 设置
   - 进入"第三方插件"
   - 关闭"安全模式"
   - 在"已安装插件"中找到"Nav System Sync"
   - 点击启用

3. **配置插件**
   - 在插件设置中配置以下信息：
     - **API 地址**：你的 Nav System 地址（如 `https://your-domain.com` 或 `http://localhost:8001`）
     - **JWT Token**：从管理界面获取（见下方说明）
     - **默认路径**：文章保存的默认路径（默认 `notes`）
     - **自动同步**：保存时自动上传（可选）

### 获取 JWT Token

1. 登录 Nav System 管理界面
2. 进入"导入导出"标签页
3. 在"API Token"部分，复制显示的 Token
4. 将 Token 粘贴到 Obsidian 插件设置中

### 功能说明

**命令面板：**
- `上传当前文件到 Nav System`：上传当前打开的文件
- `上传当前文件（指定路径）`：上传并自定义保存路径

**右键菜单：**
- 右键 Markdown 文件 → "上传到 Nav System"
- 右键文件夹 → "上传文件夹到 Nav System"

**编辑器菜单：**
- 在编辑器中右键 → "上传到 Nav System"

**自动同步：**
- 启用后，保存文件时自动上传到 Nav System

**状态栏：**
- 显示"Nav Sync"图标，表示插件已启用

### 使用方法

**上传单个文件：**
1. 打开要上传的 Markdown 文件
2. 按 `Ctrl/Cmd + P` 打开命令面板
3. 输入"上传当前文件"并执行
4. 或者右键文件 → "上传到 Nav System"

**上传整个文件夹：**
1. 在文件列表中右键文件夹
2. 选择"上传文件夹到 Nav System"
3. 插件会递归上传所有 Markdown 文件

**批量同步脚本：**
```bash
python scripts/sync_articles.py \
  --vault /path/to/obsidian/vault \
  --api https://your-domain.com \
  --token YOUR_JWT_TOKEN
```

### 注意事项

- 上传的文件会保存到 `articles/` 目录
- 文件路径结构会保持与 Obsidian vault 中一致
- 支持中文文件名和路径
- 图片等附件需要单独处理（暂不支持自动上传）

## 📡 API 接口

### 认证
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/login` | 登录 |
| POST | `/api/v1/auth/logout` | 登出 |
| GET | `/api/v1/auth/me` | 当前用户信息 |

### 导航链接
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/v1/links` | 获取链接列表 | 否 |
| POST | `/api/v1/links` | 添加链接 | 是 |
| PUT | `/api/v1/links/{id}` | 修改链接 | 是 |
| DELETE | `/api/v1/links/{id}` | 删除链接 | 是 |

### 分类
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/v1/categories` | 添加分类 | 是 |
| PUT | `/api/v1/categories/{name}` | 修改分类 | 是 |
| DELETE | `/api/v1/categories/{name}` | 删除分类 | 是 |

### 文章
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/v1/articles` | 文章列表 | 否 |
| GET | `/api/v1/articles/{path}` | 文章内容 | 否* |
| POST | `/api/v1/articles/sync` | 同步文章 | 是 |
| PUT | `/api/v1/articles/{path}` | 编辑文章 | 是 |
| DELETE | `/api/v1/articles/{path}` | 删除文章 | 是 |

> *受保护目录下的文章需要登录

### 目录管理
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/v1/folders` | 目录列表 | 是 |
| POST | `/api/v1/folders?name={name}` | 创建目录 | 是 |
| PUT | `/api/v1/folders/{name}` | 重命名目录 | 是 |
| DELETE | `/api/v1/folders/{name}` | 删除目录 | 是 |

### 设置与日志
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/v1/settings` | 获取设置 | 否 |
| PUT | `/api/v1/settings` | 更新设置 | 是 |
| GET | `/api/v1/logs/visits` | 访问记录 | 是 |
| GET | `/api/v1/logs/updates` | 更新记录 | 是 |

## 🛠️ 技术栈

- **后端**: Python FastAPI
- **数据库**: SQLite + SQLAlchemy (async)
- **认证**: JWT Token
- **前端**: HTML + CSS + JavaScript + Jinja2
- **设计**: Zen-iOS Hybrid（毛玻璃效果 + 物理触感）
- **部署**: Docker + Docker Compose

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
├── data/                    # SQLite 数据库文件
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

- 生产环境建议使用 Nginx 反向代理并启用 HTTPS
- 定期备份 `data/nav_system.db` 数据库文件和 `articles/` 目录
- `SECRET_KEY` 必须是随机生成的 32 字符以上字符串
- 首次启动会自动创建数据库表结构
- Docker 部署时确保挂载 `data` 目录以持久化数据

## 📄 License

MIT License
