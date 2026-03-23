# Nav System

基于 `FastAPI + Jinja2 + Vanilla JS + SQLite` 的个人导航与 Markdown 文章系统。

当前代码已经按重构清单切分出比较明确的边界：

- 后端路由保持薄控制器，文件系统/设置/限流逻辑分别落在 `app/services/*`
- 文章与目录路径规则统一在 `app/core/pathing.py`
- 站点设置使用 typed `site_settings` 模型和 `SettingsService`
- 浏览器端按 `core / ui / pages` 拆分
- Python 同步脚本与 Obsidian 插件都通过各自的 API helper 维护 `/api/v1` 契约

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

### 2. Docker Compose

```bash
docker compose up -d --build
```

默认访问：`http://localhost:8001`

容器入口默认会先执行一次：

```bash
alembic upgrade head
```

只有在迁移由外部流程保证时，才应显式设置 `SKIP_MIGRATIONS=true` 跳过。

挂载说明：

- `./articles`：Markdown 文章
- `./data`：SQLite 数据库
- `./static/icons`：站点图标缓存

### 3. 本地开发

```bash
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

如果是已有部署升级，必须先执行：

```bash
alembic upgrade head
```

应用启动阶段不再自动建表；无论是空库初始化还是版本升级，都必须通过 Alembic 管理 schema。

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

默认部署会在应用启动后先执行一次日志保留清理，并在后台按固定间隔重复执行。

默认参数：

- `ENABLE_LOG_CLEANUP=true`
- `LOG_CLEANUP_INTERVAL_SECONDS=21600`（每 6 小时一次）
- `MAX_VISIT_RECORDS=1000`
- `MAX_UPDATE_RECORDS=500`

如果已经通过外部调度执行清理脚本，可以显式设置 `ENABLE_LOG_CLEANUP=false` 关闭应用内定时清理。

手动清理入口仍然保留：

```bash
python scripts/cleanup_logs.py
python scripts/cleanup_logs.py --max-visits 2000 --max-updates 1000
docker compose run --rm --profile maintenance log-cleanup
```

说明：

- 应用内定时清理是本地、裸机和 Docker Compose 默认路径
- `scripts/cleanup_logs.py` 适合手动补跑或外部调度
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
    articles.js
```

说明：

- `core/endpoints.js` 是浏览器端接口路径唯一来源
- `core/http.js` 负责通用请求、鉴权头和 401 回调
- `pages/home.js`、`pages/articles.js` 只保留页面编排逻辑
- 模板中不再保留文章页内联业务脚本，首页也已切到模块入口

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

本地运行：

```bash
pytest -q
```

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
├── docker-compose.yml
├── Dockerfile
└── REFACTOR_CHECKLIST.md
```

## 维护建议

- 生产环境请放在 HTTPS 反向代理后
- 定期备份 `data/` 与 `articles/`
- 任何环境启动前都要先确保 `alembic upgrade head` 已执行
- 默认应用内日志清理保持开启；只有在外部已有调度时再关闭并改用 `scripts/cleanup_logs.py`

## License

MIT
