---
key: test_case
name: 测试用例编写
keywords: [测试, test, 单元测试, pytest, unittest, jest, 测试用例, 断言, mock]
---

# 测试用例编写规范

## 快速参考
| 任务 | 推荐方案 |
|------|---------|
| Python 测试 | pytest |
| JS/TS 测试 | Jest / Vitest |
| Mock | unittest.mock / jest.mock |
| 参数化 | pytest.parametrize / test.each |

## 核心规范

### AAA 模式（Arrange-Act-Assert）
- 每个测试严格分为三段：准备、执行、断言
- 段之间用空行分隔，不加注释也能看出结构
- 一个测试只测一个行为，不在一个函数里塞多个 Act

```python
def test_calculate_discount_for_vip_user():
    # Arrange - 准备测试数据
    user = User(level='vip', balance=1000)
    product = Product(price=200)

    # Act - 执行被测操作
    result = calculate_discount(user, product)

    # Assert - 验证结果
    assert result == 160  # VIP 8折
```

### 命名规范
- 格式：`test_<被测函数>_<场景>_<预期结果>`
- 用英文下划线连接，可以长但必须清晰
- 看名字就知道测什么、在什么条件下、期望什么

```python
# 好的命名
def test_login_with_expired_token_returns_401(): ...
def test_parse_csv_with_empty_file_returns_empty_list(): ...
def test_send_email_with_invalid_address_raises_ValueError(): ...

# 差的命名
def test_login(): ...
def test_case_1(): ...
def test_it_works(): ...
```

### 测试隔离
- 每个测试独立运行，不依赖其他测试的执行顺序
- 测试前后清理状态（数据库/文件/全局变量）
- 使用 `setUp`/`tearDown` 或 pytest `fixture` 管理
- 不在测试间共享可变状态

```python
@pytest.fixture
def temp_db():
    db = create_test_database()
    yield db
    db.drop_all()

def test_create_user(temp_db):
    user = temp_db.create_user(name='test')
    assert user.id is not None
```

### Mock 外部依赖
- 网络请求、数据库、文件系统、时间 — 全部 mock
- Mock 粒度：只 mock 当前测试不关心的部分
- 验证 mock 被正确调用（次数、参数）
- 不 mock 被测对象本身

```python
from unittest.mock import patch, MagicMock

@patch('services.email.send_email')
def test_register_sends_welcome_email(mock_send):
    register_user('test@example.com', 'password123')

    mock_send.assert_called_once_with(
        to='test@example.com',
        subject='欢迎注册'
    )
```

### 边界覆盖
每个函数至少覆盖以下场景：
1. **正常路径**：标准输入，期望输出
2. **空值/空集合**：None、空字符串、空列表
3. **边界值**：0、1、-1、最大值、最小值
4. **异常路径**：非法输入、网络超时、权限不足

```python
@pytest.mark.parametrize("input_val, expected", [
    ([3, 1, 2], [1, 2, 3]),      # 正常
    ([], []),                      # 空列表
    ([1], [1]),                    # 单元素
    ([2, 2, 2], [2, 2, 2]),       # 全相同
    ([-1, 0, 1], [-1, 0, 1]),     # 含负数
])
def test_sort_list(input_val, expected):
    assert sort_list(input_val) == expected
```

### 精确断言
- 用 `==` 比较确切值，不用 `assertTrue(x > 0)` 这种模糊断言
- 浮点数用 `pytest.approx`：`assert result == pytest.approx(3.14, rel=1e-3)`
- 异常断言用 `pytest.raises`：`with pytest.raises(ValueError, match='无效')`
- 集合断言：`assert set(result) == {1, 2, 3}`（忽略顺序）

### pytest.parametrize
- 多组输入输出相同逻辑时，用参数化代替复制粘贴
- 参数命名清晰，用 `ids` 给每组起名

```python
@pytest.mark.parametrize("filename, expected_ext", [
    ("report.pdf", ".pdf"),
    ("image.PNG", ".png"),
    ("noext", ""),
    (".gitignore", ""),
], ids=["normal", "uppercase", "no_ext", "dotfile"])
def test_get_extension(filename, expected_ext):
    assert get_extension(filename) == expected_ext
```

### 测试文件组织
- 测试文件与源码一一对应：`src/utils.py` → `tests/test_utils.py`
- 共用 fixture 放 `conftest.py`
- 测试数据放 `tests/fixtures/` 或 `tests/data/`

## 自检清单
- [ ] 每个测试遵循 AAA 模式
- [ ] 命名格式 test_函数_场景_预期
- [ ] 测试间无顺序依赖
- [ ] 外部依赖已 mock
- [ ] 覆盖了正常/空值/边界/异常四种场景
- [ ] 断言精确（不用 assertTrue 判断复杂条件）
- [ ] 重复逻辑用 parametrize 参数化
