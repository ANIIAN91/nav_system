# Nav System

基于 `FastAPI + Jinja2 + Vanilla JS + SQLite` 的个人导航与 Markdown 文章系统。

[Demo](https://navsystem-navsystem.up.railway.app/) | 预览账号: `admin / admin123`

## 功能

- 导航链接、分类、拖拽排序、导入导出
- Markdown 文章浏览、编辑、目录管理
- 目录级文章保护
- 管理后台设置、访问日志、更新日志
- JWT 登录、服务端登出撤销、登录限流
- Obsidian 插件同步和 Python 批量同步脚本

## API 约定

所有接口统一使用 `/api/v1` 前缀。

常用分组：

- 认证：`/api/v1/auth/*`
- 导航：`/api/v1/links/*`、`/api/v1/categories/*`
- 文章：`/api/v1/articles/*`、`/api/v1/folders/*`
- 设置与日志：`/api/v1/settings`、`/api/v1/logs/*`

## 快速开始

- 镜像：`aniian/nav-system:latest`
- 容器内监听端口：`8000`
- 示例宿主机端口：`8001`
- 数据持久化目录：`articles/`、`data/`、`static/icons/`

### 1. 配置环境变量

复制模板：

```bash
cp .env.example .env
```

最少需要：

```env
SECRET_KEY=generate-a-random-32-char-string-here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_this_password
```

也可以改用 `ADMIN_PASSWORD_HASH`。

### 2. 准备持久化目录

这些目录会挂载到容器中，删除容器后数据仍然保留：

- `./articles`：Markdown 文章
- `./data`：SQLite 数据库
- `./static/icons`：站点图标缓存

如果目录还不存在，先创建：

```bash
mkdir -p articles data static/icons
```

### 3. 拉取镜像

```bash
docker pull aniian/nav-system:latest
```

### 4. 启动容器

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

参数说明：

- `-d`：后台运行容器
- `--name nav-system`：固定容器名，方便后续日志、重启、升级操作
- `-p 8001:8000`：把宿主机 `8001` 映射到容器内 `8000`
- `--env-file .env`：从项目目录下的 `.env` 读取环境变量
- `-v ...:/app/articles`：持久化文章目录
- `-v ...:/app/data`：持久化 SQLite 数据库
- `-v ...:/app/static/icons`：持久化图标缓存
- `--restart unless-stopped`：宿主机重启后自动拉起

启动完成后访问：`http://localhost:8001`

### 5. 首次启动会做什么

容器入口会默认先执行：

```bash
alembic upgrade head
```

这意味着：

- 空库首次启动时会自动初始化 schema
- 老版本升级时会自动执行数据库迁移
- 只有在迁移已经由外部流程保证时，才应该显式设置 `SKIP_MIGRATIONS=true`

应用启动阶段不再使用 `create_all()` 自动建表，schema 统一由 Alembic 管理。

### 6. 常用容器管理

查看日志：

```bash
docker logs -f nav-system
```

停止容器：

```bash
docker stop nav-system
```

启动容器：

```bash
docker start nav-system
```

删除容器：

```bash
docker rm -f nav-system
```

### 7. 升级方式

保留挂载目录不变时，升级只需要替换容器，不需要迁移文章和数据库文件：

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

因为数据库和文章目录都在宿主机挂载中，新容器启动时会直接复用旧数据，并自动执行最新迁移。

## 设置模型

站点设置已集中到单行 typed 表 `site_settings`，主要字段包括：

- `site_title`
- `article_page_title`
- `icp`
- `copyright`
- `link_size`
- `timezone`
- `github_url`
- `protected_article_paths_json`

对应读写入口是 `app/services/settings.py`。

旧的 key-value `settings` 表、`app/models/setting.py` 和 `app/schemas/setting.py` 兼容层已移除。旧部署升级到当前版本时，需要先执行 `alembic upgrade head`，让 `20260324_01` 完成数据迁移，再由 `20260324_02` 删除旧表。如果数据库里同时存在已写入的 `site_settings` 和旧 `settings`，迁移会显式拒绝继续，避免在双写状态下静默丢失配置。

## 日志保留策略

页面请求路径上只做单次插入，不再在热路径里做 `count + delete`。

默认 Docker 容器会在应用启动后先执行一次日志保留清理，并在后台按固定间隔重复执行。

默认参数：

- `ENABLE_LOG_CLEANUP=true`
- `LOG_CLEANUP_INTERVAL_SECONDS=21600`（每 6 小时一次）
- `MAX_VISIT_RECORDS=1000`
- `MAX_UPDATE_RECORDS=500`

如果已经通过外部调度执行清理脚本，可以显式设置 `ENABLE_LOG_CLEANUP=false` 关闭应用内定时清理。

手动清理入口仍然保留：

```bash
docker exec nav-system python scripts/cleanup_logs.py
docker exec nav-system python scripts/cleanup_logs.py --max-visits 2000 --max-updates 1000
```

说明：

- 应用内定时清理是默认 Docker 运行路径
- `scripts/cleanup_logs.py` 适合手动补跑或由宿主机外部调度执行
- 清理结果会输出删除数量和当前保留数量，可从脚本 stdout 或应用日志观察

## 同步客户端

### Python 批量同步

脚本入口：`scripts/sync_articles.py`

共享 API 契约：`scripts/nav_client.py`

示例：

```bash
python scripts/sync_articles.py \
  --vault /path/to/obsidian/vault \
  --api http://localhost:8001 \
  --token YOUR_JWT_TOKEN
```

常用参数：

- `--target`：目标目录前缀
- `--pattern`：自定义匹配模式
- `--exclude`：排除模式
- `--force`：强制重传
- `--test`：仅测试连接

### Obsidian 插件

插件目录：`obsidian-plugin/`

共享 API 契约：`obsidian-plugin/api.js`

配置项：

- 服务地址
- JWT Token
- 默认同步路径
- 自动同步开关

Token 可在首页管理弹窗的“导入导出”页签中复制。前端现在只提供“记住用户名”，不再保存密码。

## 前端结构

```text
static/js/
  core/
    auth.js
    endpoints.js
    http.js
    state.js
  ui/
    modal.js
    theme.js
    toast.js
  pages/
    home.js
    home/
      article-manager.js
      article-sheet.js
```

说明：

- `core/endpoints.js` 是浏览器端接口路径唯一来源
- `core/http.js` 负责通用请求、鉴权头和 401 回调
- `pages/home.js` 负责首页编排，文章浮页和文章管理已拆到 `pages/home/*`
- 独立 `/articles` 页面已退场，旧链接会重定向回首页

## 后端结构

```text
app/
  core/
    pathing.py
  models/
    site_settings.py
  routers/
    articles.py
    auth.py
    folders.py
    settings.py
  services/
    articles.py
    auth.py
    folders.py
    rate_limit.py
    settings.py
```

说明：

- `routers/*` 负责参数解析、依赖注入和响应映射
- `services/articles.py`、`services/folders.py` 接管文件系统操作
- `services/auth.py` 使用 `RateLimiter` 抽象
- `services/settings.py` 负责 typed settings、默认值和缓存

## 测试与 CI

CI 当前会校验：

- 空库可以直接执行 `alembic upgrade head`
- 测试通过
- 客户端业务代码里不重新硬编码 `/api/v1/...`
- 首页模板不再回退到旧 `static/js/main.js`
- 文章页模板没有重新引入大段内联脚本
- legacy settings model/schema 不被重新引入

## 目录概览

```text
nav_system/
├── app/
├── alembic/
├── articles/
├── data/
├── obsidian-plugin/
├── scripts/
├── static/
├── templates/
├── tests/
├── Dockerfile
└── REFACTOR_CHECKLIST.md
```

## 维护建议

- 生产环境请放在 HTTPS 反向代理后
- 定期备份 `data/` 与 `articles/`
- 每次升级前先 `docker pull` 新镜像，再用原有挂载目录重新创建容器
- 默认应用内日志清理保持开启；只有在外部已有调度时再关闭并改用 `scripts/cleanup_logs.py`

## License

MIT
