---
key: code_review
name: 代码审查
keywords: [review, 审查, 代码审查, code review, 重构, refactor, 优化, 代码质量]
---

# 代码审查规范

## 快速参考
| 审查维度 | 优先级 |
|---------|--------|
| 正确性 | P0 - 最高 |
| 安全性 | P0 - 最高 |
| 性能 | P1 - 高 |
| 可读性 | P2 - 中 |
| 可维护性 | P2 - 中 |

## 核心规范

### 审查优先级顺序
1. **正确性**：逻辑是否正确？边界条件是否处理？
2. **安全性**：是否有注入、泄露、越权风险？
3. **性能**：是否有明显的性能问题（N+1、无限循环、内存泄漏）？
4. **可读性**：代码是否容易理解？命名是否清晰？
5. **可维护性**：是否便于未来修改和扩展？

按此顺序逐一审查，先修高优先级问题。

### 正确性检查
- 函数在所有分支都有返回值
- 循环有终止条件，不会无限循环
- 空值/空集合已处理（不假设输入永远合法）
- 类型转换安全（不会因脏数据崩溃）
- 并发场景的竞态条件

```python
# 问题：missing else 分支返回 None
def get_level(score):
    if score >= 90:
        return 'A'
    elif score >= 60:
        return 'B'
    # score < 60 时返回 None！

# 修正
def get_level(score):
    if score >= 90:
        return 'A'
    elif score >= 60:
        return 'B'
    else:
        return 'C'
```

### 安全性检查（OWASP Top 10）
- **注入**：SQL/命令/模板注入，所有外部输入必须参数化或转义
- **认证**：密码明文存储、JWT 未验证过期、session 未失效
- **敏感数据**：API Key/密码出现在日志、代码、URL 参数中
- **越权**：仅检查登录状态，未校验资源归属（用户 A 能改用户 B 数据）
- **XSS**：用户输入未转义直接渲染到 HTML
- **CSRF**：状态修改接口未带 token
- **路径遍历**：用户输入拼接文件路径（`../../etc/passwd`）

```python
# 危险 - SQL 注入
query = f"SELECT * FROM user WHERE name = '{name}'"

# 安全 - 参数化
query = "SELECT * FROM user WHERE name = %s"
cursor.execute(query, (name,))
```

### 复杂度控制
- 圈复杂度（Cyclomatic Complexity）< 10
- 单个函数不超过 50 行
- 嵌套不超过 3 层（if 里 for 里 if → 提取函数）
- 参数不超过 5 个（多了用对象/字典封装）

```python
# 坏味道：嵌套过深
for item in items:
    if item.active:
        for sub in item.children:
            if sub.valid:
                process(sub)  # 4 层嵌套

# 改进：提前 continue + 提取函数
for item in items:
    if not item.active:
        continue
    process_children(item.children)
```

### DRY 原则
- 相同逻辑出现 3 次及以上 → 必须提取为函数
- 相似代码（只差参数）→ 抽象为带参函数
- 魔法数字 → 提取为命名常量
- 重复的异常处理 → 装饰器或上下文管理器

### 命名质量
- 变量名能表达含义：`user_count` 不是 `n`，`is_active` 不是 `flag`
- 函数名是动词短语：`calculate_total`、`send_notification`
- 布尔变量用 `is_/has_/can_` 前缀
- 避免缩写（除非是通用缩写如 `url`、`id`、`db`）
- 作用域越大，名字越描述性；作用域越小（循环变量），可以短

### 异常处理
- 禁止空 except：`except: pass`（吞掉所有错误，调试噩梦）
- 禁止 `except Exception`（太宽泛，掩盖 bug）
- 捕获具体异常类型
- 异常信息要有上下文（什么操作失败、输入是什么）

```python
# 禁止 - 静默吞掉异常
try:
    process(data)
except:
    pass

# 正确 - 捕获具体类型，记录上下文
try:
    result = process(data)
except ValueError as e:
    logger.error(f"数据处理失败 data_id={data.id}: {e}")
    raise
```

### 审查反馈格式
- 每条反馈标注严重级别：`[P0-阻塞]` `[P1-重要]` `[P2-建议]`
- 说明问题是什么、为什么有问题、建议怎么改
- 给出代码示例（不只是说"这里有问题"）
- 肯定好的设计，不只挑毛病

## 自检清单
- [ ] 按优先级顺序审查：正确性→安全性→性能→可读性→可维护性
- [ ] 检查了 OWASP Top 10 相关风险
- [ ] 单函数复杂度 < 10，行数 < 50
- [ ] 重复代码（≥3 次）已提取
- [ ] 变量/函数命名清晰有意义
- [ ] 无空 except 或静默吞异常
- [ ] 反馈标注了严重级别和修改建议
