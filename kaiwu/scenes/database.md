---
key: database
name: 数据库设计
keywords: [数据库, database, sql, mysql, postgresql, sqlite, 建表, 表设计, 索引, orm]
---

# 数据库设计规范

## 快速参考
| 任务 | 推荐方案 |
|------|---------|
| 快速原型 | SQLite |
| 生产环境 | PostgreSQL |
| ORM | SQLAlchemy 2.0 / Prisma |
| 迁移 | Alembic / Prisma Migrate |

## 核心规范

### 命名规则
- 表名：`snake_case` 单数形式（`user` 不是 `users`）
- 列名：`snake_case`（`created_at` 不是 `createdAt`）
- 主键：统一用 `id`
- 外键：`<关联表名>_id`（如 `user_id`）
- 索引：`idx_<表名>_<列名>`（如 `idx_user_email`）
- 唯一约束：`uk_<表名>_<列名>`

### 必备字段
每张表必须包含以下三个字段：

```sql
CREATE TABLE user (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    -- 业务字段 ...
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

- `id`：自增主键（或 UUID，根据场景选择）
- `created_at`：创建时间，默认当前时间，不可更新
- `updated_at`：更新时间，每次修改时更新

### 外键约束
- 必须显式定义 `ON DELETE` 行为，不留默认
- 子记录跟随删除：`ON DELETE CASCADE`
- 保护性拒绝：`ON DELETE RESTRICT`
- 置空解除关系：`ON DELETE SET NULL`
- 禁止出现孤儿记录（外键指向不存在的主记录）

```sql
ALTER TABLE order
ADD CONSTRAINT fk_order_user
FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE;
```

### 索引策略
- 联合索引遵循**最左前缀原则**：`INDEX(a, b, c)` 能加速 `WHERE a=` 和 `WHERE a= AND b=`
- 高频查询的 WHERE/ORDER BY 列建索引
- 区分度低的列（如性别/状态）不单独建索引
- 单表索引不超过 5 个，过多影响写入性能
- 覆盖索引：查询列全部在索引中，避免回表

```sql
-- 用户按邮箱查询（高频）
CREATE UNIQUE INDEX uk_user_email ON user(email);

-- 订单按用户+时间范围查询
CREATE INDEX idx_order_user_created ON order(user_id, created_at);
```

### 参数化查询（100% 强制）
- 所有 SQL 必须参数化，零例外
- 禁止字符串拼接 SQL（SQL 注入的根源）
- ORM 的 where 方法天然参数化，直接用

```python
# 正确 - 参数化
cursor.execute("SELECT * FROM user WHERE email = ?", (email,))

# 正确 - ORM
db.query(User).filter(User.email == email).first()

# 错误 - 字符串拼接（SQL 注入风险）
cursor.execute(f"SELECT * FROM user WHERE email = '{email}'")
```

### 分页查询
- 使用 `LIMIT + OFFSET` 实现分页
- 大数据量用游标分页（基于上一页最后 ID）
- 前端传 `page` 和 `page_size`，后端计算 offset
- 限制 `page_size` 最大值（如 100）

```sql
-- 基础分页
SELECT * FROM order ORDER BY id DESC LIMIT 20 OFFSET 40;

-- 游标分页（大数据量性能更好）
SELECT * FROM order WHERE id < ? ORDER BY id DESC LIMIT 20;
```

### 预加载（避免 N+1）
- ORM 查询关联数据时使用 eager loading
- SQLAlchemy：`joinedload()` 或 `selectinload()`
- 先查主表再批量查关联表，不要循环中单条查询

```python
# 正确 - 一次查询加载关联
users = db.query(User).options(joinedload(User.orders)).all()

# 错误 - N+1 问题
users = db.query(User).all()
for user in users:
    print(user.orders)  # 每次触发一条 SQL
```

### 数据完整性
- 非空字段加 `NOT NULL`
- 枚举值用 `CHECK` 约束或应用层校验
- 金额用 `DECIMAL`，不用 `FLOAT`（精度丢失）
- 文本长度有明确上限：`VARCHAR(255)`

## 自检清单
- [ ] 表名/列名 snake_case 单数
- [ ] 每张表有 id/created_at/updated_at
- [ ] 外键显式定义 ON DELETE 行为
- [ ] 索引遵循最左前缀原则
- [ ] 所有 SQL 100% 参数化
- [ ] 分页用 LIMIT，page_size 有上限
- [ ] 关联查询使用 eager loading
- [ ] 金额字段用 DECIMAL 类型
