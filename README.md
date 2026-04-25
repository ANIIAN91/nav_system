# Nav System

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688)
![SQLite](https://img.shields.io/badge/SQLite-Alembic-07405E)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED)
![License](https://img.shields.io/badge/License-MIT-green)

Nav System 是一个基于 `FastAPI + Jinja2 + Vanilla JS + SQLite` 的个人导航与 Markdown 文章系统。它适合部署为个人主页、知识库入口、书签导航站，支持分类链接、文章管理、目录保护、访问日志、Docker 部署和 Obsidian/脚本同步。

- Demo: <https://navsystem-navsystem.up.railway.app/>
- 预览账号: `admin / admin123`
- Docker 镜像: `aniian/nav-system:latest`

## 目录

- [特性](#特性)
- [快速开始](#快速开始)
- [配置](#配置)
- [本地开发](#本地开发)
- [Docker 部署](#docker-部署)
- [数据与迁移](#数据与迁移)
- [同步客户端](#同步客户端)
- [API 约定](#api-约定)
- [项目结构](#项目结构)
- [测试与 CI](#测试与-ci)
- [安全与隐私](#安全与隐私)
- [维护建议](#维护建议)
- [License](#license)

## 特性

- 分类导航、链接管理、拖拽排序、导入导出
- Markdown 文章浏览、编辑、目录管理和同步
- 目录级文章保护，受保护目录只对登录用户开放
- 管理后台设置、访问日志、更新日志
- JWT 登录、服务端登出撤销、登录限流
- 自动 favicon 获取和本地图标缓存
- Obsidian 插件同步与 Python 批量同步脚本
- Docker 入口自动执行 Alembic 数据库迁移

## 快速开始

### 使用 Docker Compose

```bash
cp .env.example .env
mkdir -p articles data static/icons
docker compose up -d --build
```

启动后访问：

```text
http://localhost:8001
```

### 使用已发布镜像

```bash
cp .env.example .env
mkdir -p articles data static/icons

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

## 配置

最少需要在 `.env` 中配置：

```env
SECRET_KEY=generate-a-random-32-char-string-here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_this_password
```

也可以使用 `ADMIN_PASSWORD_HASH` 代替明文 `ADMIN_PASSWORD`。

常用环境变量：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/nav_system.db` | 数据库连接字符串 |
| `SECRET_KEY` | 无 | JWT 签名密钥，生产环境必须使用随机强密钥 |
| `ADMIN_USERNAME` | 无 | 管理员用户名 |
| `ADMIN_PASSWORD` | 无 | 管理员明文密码 |
| `ADMIN_PASSWORD_HASH` | 无 | 管理员密码哈希，优先用于生产部署 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `43200` | 登录 token 有效期，默认 30 天 |
| `MAX_LOGIN_ATTEMPTS` | `5` | 登录窗口内最大失败次数 |
| `LOGIN_WINDOW_SECONDS` | `300` | 登录限流统计窗口 |
| `LOCKOUT_SECONDS` | `900` | 登录锁定时间 |
| `ENABLE_LOG_CLEANUP` | `true` | 是否启用应用内日志清理任务 |
| `LOG_CLEANUP_INTERVAL_SECONDS` | `21600` | 日志清理间隔，默认 6 小时 |
| `MAX_VISIT_RECORDS` | `1000` | 访问日志保留数量 |
| `MAX_UPDATE_RECORDS` | `500` | 更新日志保留数量 |
| `SKIP_MIGRATIONS` | `false` | Docker 入口是否跳过 Alembic 迁移 |

## 本地开发

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
python -m alembic upgrade head
uvicorn app.main:app --reload
```

默认开发地址：

```text
http://localhost:8000
```

运行测试：

```bash
pytest
```

## Docker 部署

容器内监听端口是 `8000`。推荐挂载三个目录：

| 宿主机目录 | 容器目录 | 用途 |
| --- | --- | --- |
| `./articles` | `/app/articles` | Markdown 文章 |
| `./data` | `/app/data` | SQLite 数据库和备份 |
| `./static/icons` | `/app/static/icons` | favicon 缓存 |

常用管理命令：

```bash
docker logs -f nav-system
docker stop nav-system
docker start nav-system
docker rm -f nav-system
```

升级镜像：

```bash
docker pull aniian/nav-system:latest
docker rm -f nav-system
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

挂载目录不变时，升级不会迁移或覆盖文章、数据库和图标缓存。新容器启动时会自动执行最新数据库迁移。

## 数据与迁移

数据库 schema 由 Alembic 管理。Docker 入口默认执行：

```bash
alembic upgrade head
```

这意味着：

- 空库首次启动会自动创建表结构
- 旧版本升级会自动执行迁移
- 应用启动阶段不再使用 `create_all()` 隐式建表
- 只有外部流程已经保证迁移时，才应该设置 `SKIP_MIGRATIONS=true`

当前设置模型使用单行 typed 表 `site_settings`，主要字段包括：

- `site_title`
- `article_page_title`
- `icp`
- `copyright`
- `link_size`
- `timezone`
- `github_url`
- `protected_article_paths_json`

旧的 key-value `settings` 表、`app/models/setting.py` 和 `app/schemas/setting.py` 兼容层已移除。旧部署升级到当前版本时，需要执行 `alembic upgrade head`，让迁移链完成数据迁移和旧表删除。

如果数据库中同时存在已写入的 `site_settings` 和旧 `settings`，迁移会拒绝继续，避免在双写状态下静默丢失配置。

## 同步客户端

### Python 批量同步

脚本入口：

```text
scripts/sync_articles.py
```

示例：

```bash
python scripts/sync_articles.py \
  --vault /path/to/obsidian/vault \
  --api http://localhost:8001 \
  --token YOUR_JWT_TOKEN
```

常用参数：

| 参数 | 说明 |
| --- | --- |
| `--target` | 目标目录前缀 |
| `--pattern` | 自定义匹配模式 |
| `--exclude` | 排除模式 |
| `--force` | 强制重传 |
| `--test` | 仅测试连接 |

共享 API 契约在 `scripts/nav_client.py` 中维护。

### Obsidian 插件

插件目录：

```text
obsidian-plugin/
```

配置项：

- 服务地址
- JWT Token
- 默认同步路径
- 自动同步开关

共享 API 契约在 `obsidian-plugin/api.js` 中维护。Token 可在首页管理弹窗的“导入导出”页签中复制。

## API 约定

所有接口统一使用 `/api/v1` 前缀。

| 分组 | 路径 |
| --- | --- |
| 认证 | `/api/v1/auth/*` |
| 导航 | `/api/v1/links/*`、`/api/v1/categories/*` |
| 文章 | `/api/v1/articles/*`、`/api/v1/folders/*` |
| favicon | `/api/v1/favicon/*` |
| 设置 | `/api/v1/settings`、`/api/v1/settings/admin` |
| 日志 | `/api/v1/logs/*` |

访问约束：

- `GET /api/v1/settings` 是公开接口，只返回页面展示需要的站点设置
- `GET /api/v1/settings/admin` 需要有效 JWT，返回管理弹窗需要的完整设置
- 公开设置接口不会返回 `protected_article_paths_json` 对应的受保护目录列表
- 设置写入、日志、导入导出、文章与目录管理接口都需要有效 JWT

## 项目结构

```text
nav_system/
├── app/
│   ├── api/                 # API 注册、依赖和错误响应映射
│   ├── application/         # 用例层和端口定义
│   ├── core/                # 路径、URL 等共享基础规则
│   ├── domain/              # 领域对象和领域服务
│   ├── infrastructure/      # 仓储与基础设施适配
│   ├── models/              # SQLAlchemy 模型
│   ├── routers/             # FastAPI API 路由
│   ├── services/            # 业务服务与兼容服务
│   └── web/                 # Jinja 页面路由
├── alembic/                 # 数据库迁移
├── articles/                # Markdown 文章目录
├── obsidian-plugin/         # Obsidian 同步插件
├── scripts/                 # 同步、备份、日志清理脚本
├── static/                  # 前端静态资源
├── templates/               # Jinja 模板
├── tests/                   # Pytest 测试
├── Dockerfile
└── docker-compose.yml
```

前端入口：

```text
static/js/
├── core/                    # auth、endpoints
├── ui/                      # modal、theme、toast
└── pages/
    ├── home-20260425c.js       # 首页入口
    └── home/                # 文章浮页和文章管理模块
```

## 测试与 CI

CI 当前校验：

- 空库可以直接执行 `alembic upgrade head`
- 测试通过
- 客户端业务代码不重新硬编码 `/api/v1/...`
- 首页模板不回退到旧 `static/js/main.js`
- 独立文章页前端不被重新引入
- legacy settings model/schema 不被重新引入

本地执行：

```bash
pytest
```

## 安全与隐私

- 生产环境必须更换 `SECRET_KEY` 和管理员密码
- 推荐使用 `ADMIN_PASSWORD_HASH`，减少明文密码暴露面
- 生产环境建议放在 HTTPS 反向代理后
- 不要提交真实 `.env`、数据库、个人文章、备份文件或图标缓存
- 默认 `.gitignore` 已排除 `.env`、`data/`、`articles/`、`static/icons/` 和常见密钥文件
- 前端只提供“记住用户名”，不保存密码
- 登录保持依赖本地 token，有效期由 `ACCESS_TOKEN_EXPIRE_MINUTES` 控制，默认 30 天

## 维护建议

- 定期备份 `data/` 与 `articles/`
- 保留 Alembic 迁移链，避免旧部署升级时缺表或丢配置
- 每次升级前先拉取新镜像，再用原有挂载目录重建容器
- 默认应用内日志清理保持开启；只有已有外部调度时再关闭

手动清理日志：

```bash
docker exec nav-system python scripts/cleanup_logs.py
docker exec nav-system python scripts/cleanup_logs.py --max-visits 2000 --max-updates 1000
```

## License

MIT
