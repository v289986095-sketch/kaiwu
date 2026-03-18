---
key: backend_api
name: 后端 API 开发
keywords: [api, 后端, fastapi, flask, django, rest, 接口, 服务端, backend, server]
---

# 后端 API 开发规范

## 快速参考
| 任务 | 推荐方案 |
|------|---------|
| 快速原型 | FastAPI |
| 传统项目 | Flask + Blueprint |
| ORM | SQLAlchemy 2.0 |
| 数据校验 | Pydantic BaseModel |

## 核心规范

### 模块化路由
- FastAPI：每个资源一个 `APIRouter`，在 `routers/` 目录下
- Flask：每个资源一个 `Blueprint`，统一前缀
- 主文件只做路由注册，不写业务逻辑

```python
# routers/users.py
from fastapi import APIRouter
router = APIRouter(prefix="/users", tags=["用户管理"])

@router.get("/")
async def list_users(): ...
```

### 统一响应格式
- 所有接口返回统一结构：`{ "code": 0, "data": ..., "message": "success" }`
- 成功：`code=0`，失败：`code` 为错误码
- 列表接口返回 `{ "code": 0, "data": { "items": [], "total": 100 } }`

```python
def ok(data=None, message="success"):
    return {"code": 0, "data": data, "message": message}

def fail(code: int, message: str):
    return {"code": code, "data": None, "message": message}
```

### HTTP 状态码
- 200：成功
- 201：创建成功
- 400：参数错误（客户端问题）
- 401：未认证
- 403：无权限
- 404：资源不存在
- 422：数据校验失败
- 500：服务器内部错误
- 不要所有错误都返回 200，状态码必须语义正确

### Pydantic 数据校验
- 请求体用 Pydantic BaseModel 定义
- 响应也用 BaseModel 控制输出字段
- 使用 `Field` 添加验证和文档描述
- 敏感字段（密码）在响应模型中排除

```python
from pydantic import BaseModel, Field

class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    email: str = Field(..., pattern=r'^[\w.-]+@[\w.-]+\.\w+$')
    password: str = Field(..., min_length=8)

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime
```

### 数据库 Session 管理
- 使用上下文管理器控制 Session 生命周期
- FastAPI 用 `Depends(get_db)` 注入
- 每个请求独立 Session，请求结束自动关闭
- 写操作显式 `commit()`，异常时 `rollback()`

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### CORS 中间件
- 开发环境允许所有来源（`allow_origins=["*"]`）
- 生产环境白名单限制
- 必须配置 `allow_methods` 和 `allow_headers`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境改为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 错误处理
- 全局异常处理器捕获未处理异常
- 业务异常抛 HTTPException，附带明确 message
- 日志记录异常堆栈（`logger.exception`）
- 生产环境不向客户端暴露堆栈信息

## 自检清单
- [ ] 路由按资源拆分到独立文件
- [ ] 响应格式统一（code/data/message）
- [ ] HTTP 状态码语义正确
- [ ] 请求体有 Pydantic 校验
- [ ] 数据库 Session 正确关闭
- [ ] CORS 已配置
- [ ] 全局异常处理器已注册
