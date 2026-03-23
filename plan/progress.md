# 进度追踪

> 用途：记录每轮任务执行前后的状态变化。

## 一、当前状态

- 最后更新：2026-03-23
- 当前阶段：Phase 7 Tests, CI, Docs 已完成
- 当前任务：将 checklist 完成状态写回 `REFACTOR_CHECKLIST.md`
- 下一步行动：进入常规维护，仅处理后续缺陷修复或增量需求

## 二、本轮任务卡（每轮都要更新）

- 任务名称：REFACTOR_CHECKLIST 完成标记回写
- 任务类型（写作/润色/翻译/画图/环境配置/文献整理）：工程重构
- 输入文件：REFACTOR_CHECKLIST.md、plan/*.md
- 输出文件：补充完成标记后的 checklist 与 plan/*.md
- 验收标准：
  - checklist 本身包含明确完成标记区
  - 文档内状态与 plan 状态一致
  - 不引入与当前仓库状态冲突的结论
  - plan 已回写本轮操作

## 三、执行记录

### [2026-03-23] [Phase 2 typed settings 收口]

- 执行动作：初始化 plan 目录，补齐 settings typed DTO、router response model、迁移窗口处理和 route-level 测试。
- 完成结果：已完成 `SiteSettingsUpdateResponse` 契约、严格 payload 校验、legacy settings 保留窗口修正，以及 settings 路由测试扩充。
- 产物路径：plan/project-overview.md；plan/progress.md；plan/notes.md；plan/stage-gates.md；plan/outline.md；app/schemas/site_settings.py；app/schemas/__init__.py；app/routers/settings.py；alembic/versions/20260324_02_drop_legacy_settings_table.py；tests/test_settings.py
- 遇到问题：`apply_patch` 在当前线程不可用，且现有 drop migration 会提前删除 legacy settings 表。
- 解决方案：改用顺序写文件完成受控修改，并把 `20260324_02` 调整为 release window 占位 revision。
- 下一步：按清单继续推进 Phase 3 或 Phase 4，并决定 legacy schema/model 的最终删除时机。

### [2026-03-23] [Phase 3 日志优化收口]

- 执行动作：补充 `log-cleanup` compose 维护入口，更新 README 日志保留说明，并新增日志服务 retention 测试。
- 完成结果：日志保留策略已经具备脚本入口、compose 入口、文档说明和测试锁定；页面热路径仍保持后台单次插入。
- 产物路径：docker-compose.yml；README.md；tests/test_log_service.py；plan/progress.md；plan/notes.md；plan/stage-gates.md
- 遇到问题：compose 本身不提供定时能力，仍需外部调度器触发 maintenance service。
- 解决方案：在 README 中明确要求由 cron、systemd timer、Windows 任务计划程序或外部调度器执行 `docker compose run --rm --profile maintenance log-cleanup`。
- 下一步：推进 Phase 4，收口 auth/cache/rate-limit 边界。

### [2026-03-23] [Phase 4 auth/cache/rate-limit 收口]

- 执行动作：将 cache 和 rate-limit 改为可替换后端 API + 代理访问，认证路由统一改走 `AuthService` 依赖，并补充 swappable backend 与 logout revoke 契约测试。
- 完成结果：`cache` 与 `rate_limit` 已不再依赖直接暴露的模块级后端实例；`AuthService` 接管 token verify/revoke 路径；settings cache 的 `use_cache=False` 语义也修正为只绕过不回填。
- 产物路径：app/utils/cache.py；app/services/rate_limit.py；app/utils/security.py；app/services/auth.py；app/routers/auth.py；app/utils/__init__.py；app/services/__init__.py；app/services/settings.py；tests/conftest.py；tests/test_auth.py；tests/test_settings_service.py；tests/test_endpoints_contract.py
- 遇到问题：settings cache 测试暴露 `use_cache=False` 仍会回填缓存，导致 swappable backend 断言失真。
- 解决方案：同步修正 `SettingsService.get_settings()` 的缓存语义，并调整测试期望。
- 下一步：决定 legacy settings 兼容层最终删除时机，并视需要继续清理 Phase 7 剩余尾项。

### [2026-03-23] [最终 cutover 与 Phase 7 收尾]

- 执行动作：删除 legacy `settings` model/schema 与服务层双写逻辑，把 `20260324_02` 改成真实 drop migration，并补充文章页模块入口与 legacy 删除守卫测试。
- 完成结果：`site_settings` 已成为唯一设置来源；旧 `settings` 表只在迁移 `20260324_01` 用于搬迁，随后由 `20260324_02` 删除；CI 也会阻止 legacy 文件和旧前端入口回归。
- 产物路径：app/services/settings.py；app/models/__init__.py；alembic/env.py；alembic/versions/20260324_02_drop_legacy_settings_table.py；tests/test_settings_service.py；tests/test_endpoints_contract.py；.github/workflows/ci.yml；README.md；plan/project-overview.md；plan/stage-gates.md；plan/notes.md；plan/progress.md
- 遇到问题：需要在删除兼容层的同时保留旧部署可升级路径，不能只删代码而忽略 Alembic head 的行为。
- 解决方案：让 `20260324_01` 继续负责从旧表搬迁数据，`20260324_02` 在 head 上执行真实 drop，并在 downgrade 中按 typed row 回填旧表。
- 下一步：进入常规维护，后续仅处理缺陷修复与增量需求。

### [2026-03-23] [REFACTOR_CHECKLIST 完成度审计]

- 执行动作：逐项比对 checklist、当前代码、CI 和测试覆盖，重点复核 Phase 7 的 links/categories 测试要求。
- 完成结果：大部分阶段已落地，但 checklist 还不能判定为“全部完成”；`tests/test_links.py` 未覆盖 batch reorder，`tests/test_categories.py` 未覆盖 reorder 与 category visibility。
- 产物路径：REFACTOR_CHECKLIST.md；tests/test_links.py；tests/test_categories.py；app/routers/links.py；app/routers/categories.py；plan/project-overview.md；plan/stage-gates.md；plan/notes.md；plan/progress.md
- 遇到问题：`plan` 中此前已把阶段写成“全部完成”，与本次实际审计结果不一致。
- 解决方案：把 plan 状态回调为“Phase 7 审计中”，待补齐残余测试后再关闭重构。
- 下一步：补齐 `tests/test_links.py` 和 `tests/test_categories.py` 的 checklist 测试项。

### [2026-03-23] [补齐 links/categories 测试缺口]

- 执行动作：为 `tests/test_links.py` 增加 batch reorder 断言，为 `tests/test_categories.py` 增加 batch reorder 和私密分类可见性断言，并执行针对性与全量测试。
- 完成结果：checklist 审计指出的两个测试缺口已补齐；仓库当前 `pytest -q` 全量通过，共 46 条测试。
- 产物路径：tests/test_links.py；tests/test_categories.py；plan/project-overview.md；plan/stage-gates.md；plan/notes.md；plan/progress.md
- 遇到问题：需要在不改业务代码的前提下验证排序和权限过滤，只能通过现有公开接口组合出稳定断言。
- 解决方案：直接走 `/api/v1/links/reorder/batch`、`/api/v1/categories/reorder/batch` 和 `/api/v1/links`，用 API 层回包验证最终顺序与可见性。
- 下一步：进入常规维护，仅处理缺陷修复与增量需求。

### [2026-03-23] [checklist 完成标记回写]

- 执行动作：在 `REFACTOR_CHECKLIST.md` 增加完成状态摘要区，明确状态日期、总体状态、验证快照和各阶段完成情况。
- 完成结果：checklist 文档本身已能独立表达“全部完成”的结论，不再需要依赖额外口头说明或外部审计上下文。
- 产物路径：REFACTOR_CHECKLIST.md；plan/progress.md；plan/notes.md
- 遇到问题：需要确保文档中的完成结论与当前仓库、测试和 plan 记录保持一致。
- 解决方案：沿用上一轮审计与测试结果，仅写入已被验证的完成事实，不扩展新的未验证断言。
- 下一步：进入常规维护，仅处理缺陷修复与增量需求。

## 四、里程碑

| 里程碑 | 计划日期 | 实际日期 | 状态 |
|---|---|---|---|
| 选题确定 |  | 2026-03-23 | ✅ |
| 文献综述完成 |  |  | ⏳ |
| 方法设计完成 |  | 2026-03-23 | ✅ |
| 初稿完成 |  | 2026-03-23 | ✅ |
| 润色完成 |  |  | ⏳ |
| 定稿提交 |  |  | ⏳ |

状态说明：`⏳待开始` `🔄进行中` `✅已完成` `🔧需返工`

## 五、章节完成度（按 outline 实际填写）

| 章节 | 状态 | 字数 | 备注 |
|---|---|---|---|
| 摘要 | ⏳待开始 | 0 | 不适用 |
| 引言 | ⏳待开始 | 0 | 不适用 |
| 文献综述 | ⏳待开始 | 0 | 不适用 |
| 方法 | ✅已完成 | 0 | 已明确分阶段重构方法 |
| 结果/发现 | ✅已完成 | 0 | REFACTOR_CHECKLIST 全部完成并验证 |
| 讨论 | ⏳待开始 | 0 | 不适用 |
| 结论 | ⏳待开始 | 0 | 不适用 |
| 参考文献 | ⏳待开始 | 0篇 | 不适用 |

## 六、待办事项

### 高优先级
- [x] 创建并初始化 plan 目录
- [x] 完成 Phase 2 代码收口
- [x] 完成 Phase 3 代码收口
- [x] 完成 Phase 4 代码收口
- [x] 运行 pytest 验证

### 中优先级
- [x] 复核 legacy schema/model 删除时机
- [x] 评估是否继续做最终文档与兼容层删除收尾

### 低优先级
- [ ] 评估日志路由的额外 contract test 需求






