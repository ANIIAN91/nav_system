# 重构大纲

> 用途：定义重构阶段结构，`progress.md` 的阶段进度需与本文件一致。

## 一、当前采用结构

- 结构类型（本科论文 / 期刊论文 / 学位论文 / 其他）：工程重构计划
- 版本号：v1
- 最后更新：2026-03-23

## 二、章节目录

### Phase 1 Backend Boundary Cleanup
- 目标：路由层瘦身，路径与文件系统逻辑下沉到 service/core

### Phase 2 Settings Model Migration
- 2.1 typed `site_settings` 模型
- 2.2 `SettingsService` 与缓存边界
- 2.3 settings 路由契约与模板读取
- 2.4 迁移窗口与兼容层

### Phase 3 Logging Optimization
- 3.1 热路径单次写入
- 3.2 retention 脚本与运维说明

### Phase 4 Auth, Cache, Rate Limit
- 4.1 限流抽象
- 4.2 logout revoke 语义一致
- 4.3 cache/rate-limit 边界清理

### Phase 5 Frontend Decomposition
- 5.1 首页模块化
- 5.2 文章页模块化
- 5.3 共享 core/ui 模块

### Phase 6 External Client Contract
- 6.1 Python 同步客户端
- 6.2 Obsidian 插件 API helper
- 6.3 端点契约测试

### Phase 7 Tests, CI, Docs
- 7.1 测试补齐
- 7.2 CI 守卫
- 7.3 README 与发布流更新

## 三、变更记录

### [2026-03-23] [初始化重构大纲]
- 变更内容：将论文模板替换为 Nav System 重构阶段结构。
- 变更原因：当前任务是工程重构，需要 plan 文件能承载实际执行阶段。
- 影响章节：全部阶段结构
