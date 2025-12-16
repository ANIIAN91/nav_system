# Nav System - 个人导航与文章系统

[Demo](https://navsystem-navsystem.up.railway.app/) | 预览账号: `admin` / `admin123`

基于 FastAPI + PostgreSQL 的个人主页系统，集成导航站和 Markdown 文章展示功能。

## 功能特性

### 导航站
- 分类展示常用链接，支持权限控制（部分分组需登录可见）
- 自动获取网站 favicon
- 链接大小可调（小/中/大）
- 实时时钟显示

### 文章系统
- Markdown 文章在线展示与编辑
- 目录结构浏览（可折叠）
- 目录权限控制
- Obsidian 插件同步支持

### 管理功能
- 站点设置（标题、备案信息、受保护目录等）
- 访问记录与更新记录
- 深色/浅色主题切换
- 暴力破解防护（5次失败锁定15分钟）

## 技术栈

- **后端**: Python FastAPI
- **数据库**: PostgreSQL + SQLAlchemy (async)
- **认证**: JWT Token
- **前端**: HTML + CSS + JavaScript + Jinja2

## 项目结构

```
nav_system/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置管理
│   ├── database.py          # 数据库连接
│   ├── models/              # SQLAlchemy 模型
│   ├── schemas/             # Pydantic 模型
│   ├── routers/             # API 路由
│   │   ├── auth.py          # 认证
│   │   ├── links.py         # 导航链接
│   │   ├── categories.py    # 分类管理
│   │   ├── articles.py      # 文章管理
│   │   ├── folders.py       # 目录管理
│   │   ├── settings.py      # 站点设置
│   │   ├── logs.py          # 访问/更新记录
│   │   └── favicon.py       # 图标获取
│   ├── services/            # 业务逻辑
│   └── utils/               # 工具函数
├── templates/               # HTML 模板
├── static/                  # 静态资源
├── articles/                # Markdown 文章
├── data/                    # JSON 数据（旧版兼容）
├── scripts/
│   ├── migrate_data.py      # JSON → PostgreSQL 迁移
│   └── sync_articles.py     # 批量同步脚本
├── alembic/                 # 数据库迁移
├── tests/                   # 测试
├── obsidian-plugin/         # Obsidian 同步插件
├── requirements.txt
├── Dockerfile
└── .env                     # 环境变量配置
```

## 快速开始

### 1. 环境准备

```bash
# 创建 conda 环境
conda create -n homepage python=3.9
conda activate homepage

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```env
# 数据库（密码中的特殊字符需 URL 编码，如 @ 编码为 %40）
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/nav_system

# 安全配置
SECRET_KEY=your-secret-key-at-least-32-characters
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
```

### 3. 数据库迁移

如果有旧版 JSON 数据需要迁移：

```bash
python scripts/migrate_data.py
```

### 4. 启动服务

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

访问 `http://localhost:8001`

## Docker 部署

```bash
# 拉取镜像
docker pull aniian/nav-system

# 运行容器
docker run -d \
  --name nav-system \
  -p 8001:8000 \
  --env-file .env \
  -v $(pwd)/articles:/app/articles \
  -v $(pwd)/static/icons:/app/static/icons \
  --restart unless-stopped \
  aniian/nav-system:latest
```

## Railway 一键部署

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/MxkRwo?referralCode=TEG7-_)

## API 接口

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

## Obsidian 插件

1. 将 `obsidian-plugin/` 复制到 `.obsidian/plugins/nav-system-sync/`
2. 在 Obsidian 设置中启用插件
3. 配置 API 地址和 JWT Token

使用方法：
- 右键文件 → "上传到 Nav System"
- 右键文件夹 → "上传文件夹到 Nav System"

## 批量同步脚本

```bash
python scripts/sync_articles.py \
  --vault /path/to/obsidian/vault \
  --api https://your-domain.com \
  --token YOUR_JWT_TOKEN
```

## 数据格式

### 导航链接

```json
{
  "categories": [
    {
      "name": "工具",
      "auth_required": false,
      "links": [
        {"title": "GitHub", "url": "https://github.com", "icon": "github.png"}
      ]
    }
  ]
}
```

### 站点设置

```json
{
  "site_title": "个人导航",
  "article_page_title": "文章",
  "link_size": "medium",
  "protected_article_paths": ["private"],
  "icp": "备案号",
  "copyright": "© 2024"
}
```

## 注意事项

- 数据库密码中的特殊字符需要 URL 编码（如 `@` → `%40`）
- 建议使用 Nginx 反向代理并启用 HTTPS
- 定期备份数据库和 `articles/` 目录
