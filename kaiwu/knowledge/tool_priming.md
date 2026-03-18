# 开物工具调用最佳实践

> 本文档面向主 AI（Claude Code / Cursor / Copilot），指导如何高效调用开物 MCP 工具。
> 核心理念：精准的参数 = 更好的结果。参数传得好，小模型也能跑出大模型的效果。

## kaiwu_context — 任务第一步，建立项目认知

**何时调用**：每个新任务的第一个调用，优先于 kaiwu_plan。

**必传参数**：
- `directory_tree`：项目文件树。推荐获取方式：`find . -type f -not -path '*/node_modules/*' -not -path '*/.git/*' | head -80`
- `task`：用户的原始任务描述

**效果**：返回 `session_id`，后续所有工具传入此 ID 即可获得跨调用记忆。

**陷阱**：
- 不传 directory_tree 而只传 task → 技术栈无法自动识别，后续规划会缺失关键上下文
- 忘记保存返回的 session_id → 后续调用全部丧失会话记忆

---

## kaiwu_plan — 获取结构化规划

**必传参数**：
- `task`：任务描述，至少 20 字。越具体，规划越精准
- `context`：至少包含以下之一：
  - 项目文件树（或 kaiwu_context 已处理则传 session_id 即可）
  - 当前文件路径和关键函数签名
  - pyproject.toml / package.json 的 dependencies 部分

**强烈推荐**：
- `session_id`：传入后规划器知道之前做了什么，不会重复规划已完成步骤
- `project_name`：传入后经验检索优先召回同项目的历史，如 "giotrip"

**返回值重点字段（按优先级）**：
1. `anchors` — 技术决策，后续步骤必须遵守
2. `edge_cases` — 每个边界情况都要处理，不能跳过
3. `verify` — 每完成一步立即执行验证
4. `reuse` — 先看这里，避免重新实现已有功能
5. `difficulty_map` — hard 步骤先调 kaiwu_condense(mode=inject) 补充上下文

**陷阱**：
- context 不传 → confidence 低于 0.5，规划基本是猜测
- task 太短（<20字）→ 步骤过于笼统，不如直接做

---

## kaiwu_lessons — 错误诊断（三层架构，越精准越省 token）

**必传参数**：
- `error_text`：包含**完整 Traceback**，不要截断最后几行
- `context`：当前正在做什么（"正在运行 pytest" / "正在 pip install"）

**为什么 error_text 要完整**：
- Layer 1（精确匹配）靠错误指纹，截断会导致指纹不匹配
- 指纹匹配命中 → 0 token 消耗，毫秒级返回
- 指纹不匹配 → 走 Layer 3 DeepSeek 分析，消耗 1 次配额

**陷阱**：
- 只传最后一行错误 → 强制走 Layer 3，浪费 token
- context 为空 → DeepSeek 无法区分是网络问题还是代码问题

---

## kaiwu_condense — 跨轮次记忆核心

**必须调用的时机**：
1. 任务开始：`mode="init"` 创建 session（或用 kaiwu_context 自动创建）
2. 超过 15 轮对话：`mode="compress"` 压缩历史，否则小模型会"遗忘"早期决策
3. hard 难度步骤前：`mode="inject"` 获取完整上下文再执行

**不需要调用**：简单任务（<5步，单文件）；已知答案的错误（Layer 1/2 命中）

---

## kaiwu_record — 记录经验，越用越智能

**必须记录**：
- 任务成功完成（success=True），DeepSeek 会自动提炼经验
- 新类型错误解决后（success=False + error_summary），丰富错误库

**不需要记录**：中间步骤失败后立即重试；简单语法错误修正

**关键参数**：
- `session_id` + `subtask_seq`：记录检查点，所有子任务完成时自动标记会话结束
- `anchors`：JSON 数组字符串，如 `'["框架: FastAPI", "数据库: SQLite"]'`
- `project_name`：经验归属项目，下次同项目任务优先召回

---

## kaiwu_scene — 获取场景编码规范

**何时调用**：收到新任务时，和 kaiwu_plan 并行调用。

**返回值**：场景特定的编码规范（.md 文件内容），如 React 组件规范、数据库建表规范等。

**支持 19 个场景**：web, react, dataviz, python_script, backend_api, data_analysis, web_scraping, shell_script, copywriting, game_dev, test_case, database, code_review, docx, pdf, pptx, xlsx, china_deploy, wechat_pay

---

## kaiwu_profile — 用户偏好画像

**何时调用**：新会话开始时调用一次，了解用户的编码风格偏好。

**返回值**：用户偏好文本（测试框架、命名规范、代码风格等），随使用自动学习。

---

## 推荐工作流（模型同权最佳实践）

```
1. kaiwu_context(directory_tree, task)     → 获得 session_id
2. kaiwu_scene(task)                       → 获得场景规范（并行）
3. kaiwu_plan(task, session_id=sid)        → 获得规划 + difficulty_map
4. 逐步执行：
   - easy 步骤 → 直接执行
   - medium 步骤 → 参考 edge_cases 后执行
   - hard 步骤 → 先 kaiwu_condense(mode=inject) 补充上下文
5. 每步完成后执行 verify 中的检查命令
6. 遇到错误 → kaiwu_lessons(error_text, context, session_id)
7. 子任务完成 → kaiwu_record(task, session_id, subtask_seq=N)
8. 超 15 轮 → kaiwu_condense(mode=compress) 压缩历史
9. 全部完成 → kaiwu_record(task, session_id, anchors=锚点列表)
```
