# 重要笔记

> 用途：记录用户偏好、关键决策和上下文恢复信息。

## 一、用户偏好

### 写作风格偏好
- 需要先记录计划，再执行重构
- 按清单分阶段推进，不做无关展开

### 排版偏好
- 正文默认不加粗
- 段落之间空一行
- 正文优先连续段落，不使用列表
- plan 文档允许使用列表与检查项

### 输出偏好
- 默认交付代码修改、测试结果与 plan 记录

## 二、关键决策

### [2026-03-23] [Phase 2 优先级]

- 背景：用户要求先用 Research Writing Assistant 记录计划，再执行 Phase 2。
- 决策：先初始化并维护 `plan/`，然后以 settings typed migration 为本轮唯一主线。
- 原因：与 skill 门禁一致，也能降低跨轮次上下文丢失。
- 影响范围：plan 目录、settings 相关代码、迁移、测试。

### [2026-03-23] [legacy settings 发布窗口]

- 背景：现有 `20260324_02` 会在执行 `alembic upgrade head` 时删除 legacy `settings` 表。
- 决策：将该 revision 调整为占位 revision，当前 release window 内不执行 drop。
- 原因：这更符合清单中“先完成全面切换，再移除旧表”的要求。
- 影响范围：Alembic 升级路径、settings 兼容期、后续删除时机。

### [2026-03-23] [Phase 3 维护入口]

- 背景：日志清理脚本已经存在，但 compose 层没有明确维护入口，测试覆盖也缺失。
- 决策：增加显式 `log-cleanup` 维护服务，并用测试锁定日志插入与 retention 行为。
- 原因：这能让日志保留策略更可执行，也更符合清单里的 explicit 和 observable 要求。
- 影响范围：docker-compose、README、日志相关测试。

### [2026-03-23] [Phase 4 边界显式化]

- 背景：cache 与 rate-limit 仍依赖模块级后端实例，auth 路由也还在直接触达 utils token 校验。
- 决策：引入可替换后端 API 和代理访问层，并让 auth 路由统一依赖 `AuthService`。
- 原因：这能让认证关键状态和缓存状态从“原始全局对象”提升为显式边界，也便于测试替换后端。
- 影响范围：app/utils/cache.py；app/services/rate_limit.py；app/services/auth.py；app/routers/auth.py；相关测试。

### [2026-03-23] [legacy settings 最终 cutover]

- 背景：Phase 5-7 已基本到位，但 `SettingsService` 仍保留 legacy `settings` 表读写，`20260324_02` 也还是占位 revision。
- 决策：结束兼容窗口，删除 `app/models/setting.py`、`app/schemas/setting.py` 和服务层双写逻辑，并让 `20260324_02` 成为真实 drop migration。
- 原因：应用、脚本、模板和测试均已切换到 typed `site_settings` 单一来源，继续保留兼容层只会增加维护成本和误用空间。
- 影响范围：settings 服务、Alembic 升级路径、CI 守卫、README、plan 文档。

### [2026-03-23] [checklist 审计残项]

- 背景：对 `REFACTOR_CHECKLIST.md` 做逐项核对时，发现 `Phase 7` 中针对 `tests/test_links.py` 和 `tests/test_categories.py` 的补测要求未完全兑现。
- 决策：将重构状态从“全阶段完成”回调为“Phase 7 审计中”，待补齐 links batch reorder、categories reorder 与 category visibility 测试后再关闭。
- 原因：当前路由已经暴露对应能力，但测试仍只覆盖基础增删查，和 checklist 的明确要求不一致。
- 影响范围：plan 状态、测试收口判断、后续收尾节奏。

### [2026-03-23] [checklist 审计收口]

- 背景：已补齐 links batch reorder、categories reorder 和 category visibility 测试，需要确认 checklist 是否可以正式关闭。
- 决策：恢复项目状态为“Phase 7 已完成”，并将 `REFACTOR_CHECKLIST` 标记为已全部收口。
- 原因：本轮补测后，全量 `pytest` 通过，且此前审计指出的唯一残项已经消除。
- 影响范围：plan 状态、最终交付判断、后续维护节奏。

### [2026-03-23] [checklist 内嵌完成标记]

- 背景：虽然 `plan` 已记录重构完成状态，但 `REFACTOR_CHECKLIST.md` 本身还缺少一眼可见的完成摘要。
- 决策：在 checklist 顶部新增 `Completion Status` 区块，写入状态日期、总体状态、验证快照和分阶段完成汇总。
- 原因：这样后续查看 checklist 时，不需要先翻 `plan` 或重新做一轮口头审计。
- 影响范围：REFACTOR_CHECKLIST.md、文档交付清晰度、后续维护效率。

## 三、约束与风险

- 硬性约束（格式、字数、截止时间）：保持 `/api/v1` 前缀；不改技术栈；路由保持薄控制器。
- 当前风险（时间、数据、文献、方法）：旧环境若跳过 `alembic upgrade head` 直接运行新代码，可能因为未完成 settings 表迁移而出现结构不一致。
- 风险应对：README、migration 和 CI 已同步强调 typed `site_settings` 是唯一来源；部署升级时先执行 Alembic。

## 四、文献与数据笔记

### 文献
- 标题：不适用
- 作者/年份：不适用
- 核心观点：不适用
- 与本研究关系：不适用

### 数据
- 数据来源：仓库现有源代码与迁移文件
- 数据质量问题：compose 不自带定时调度能力；旧部署升级需要显式执行迁移
- 清洗说明：通过 service 边界、typed settings 单一来源、缓存代理和 out-of-band maintenance 维持主路径稳定

## 五、上下文恢复卡（必须维护）

- 项目一句话概述：Nav System 按 REFACTOR_CHECKLIST 持续推进模块化重构。
- 当前正在做什么：全部阶段已完成，当前维护收口后的回归验证结果。
- 下一步立即行动：进入常规维护，仅处理缺陷修复与增量需求。
- 当前不可违反的规则：不回退到路由层设置逻辑；不把日志 retention 放回热路径；不重新引入原始模块级 auth/cache/rate-limit 后端依赖。





