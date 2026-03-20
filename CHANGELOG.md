# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.2.2] - 2026-03-20

### Added
- 执行轨迹审计：分析 AI 执行过程中的转折点，提炼可复用方法论
- 方法论模式库：`[方法论]` 标签经验，"在X情境下做Y比做Z好"
- Strong 模型积极学习：Opus/GPT-4o 的路线和犯错模式都被记录
- Token 消耗追踪：`kaiwu stats` 展示 LLM 调用次数、token 消耗、本地命中率
- 经验助攻率度量：追踪每条经验被注入后是否帮助任务成功
- Plan vs Trace 零 token 对比：规划与实际路线的关键词重叠度分析
- 方法论跨项目泛化：高置信度通用方法论自动标记 universal，跨项目可见
- 错误库模式聚类：10 类错误自动归类，同类别最佳方案匹配
- TF-IDF 精排：纯 Python 实现，Jaccard 粗排 + TF-IDF 精排混合检索
- 核心模块单元测试：158 个测试用例覆盖 experience/recorder/classifier/error_kb
- GitHub Actions CI：Python 3.10/3.11/3.12 自动测试 + ruff lint
- CONTRIBUTING.md 贡献指南
- py.typed PEP 561 标记

### Changed
- 审计门控重构：strong 模型不再跳过，而是积极学习最佳实践和犯错模式
- 审计 prompt 支持 best_practice / pitfall 双类型
- README 重写：增加飞轮架构图、审计管线、四态决策流程、能力自适应矩阵
- README 措辞专业化，联系方式改为 GitHub Issues

## [0.2.1] - 2026-03-15

### Added
- 四态经验去重（ADD/UPDATE/DELETE/NONE）
- Tag 分类体系（6 类标签 + 优先级矩阵）
- 项目隔离（project_name 过滤）
- 决策锚点（ANCHOR 层永久保留）
- 异步蒸馏（后台线程不阻塞）

## [0.2.0] - 2026-03-10

### Added
- 初始发布：7 个 MCP 工具
- DeepSeek 智能规划
- 三层错误诊断
- 经验学习与注入
- 上下文压缩
- 19 个编码场景规范
- 用户习惯画像
- Claude Code Plugin 模式
- 多平台 MCP 注册（Claude Code / Cursor / Codex）
