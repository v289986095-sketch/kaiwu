---
key: python_script
name: Python 脚本开发
keywords: [python, 脚本, script, py, 自动化, 工具, 批处理]
---

# Python 脚本开发规范

## 快速参考
| 任务 | 推荐方案 |
|------|---------|
| 参数解析 | argparse（标准库） |
| 日志 | logging 模块 |
| 路径处理 | pathlib.Path |
| HTTP 请求 | httpx（优先）或 requests |

## 核心规范

### 文件结构（固定顺序）
```python
"""模块文档字符串：一句话说明用途"""

# 标准库
import os
import sys
import logging
from pathlib import Path

# 第三方库
import httpx

# 本地模块
from utils import helper

# 常量
BASE_DIR = Path(__file__).parent
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(message)s'

# 日志配置
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# 函数定义
def main():
    ...

# 入口
if __name__ == '__main__':
    main()
```

### 模块级日志
- 每个文件顶部 `logger = logging.getLogger(__name__)`
- 关键操作用 `logger.info`，异常用 `logger.error`
- 不用 `print` 做日志（调试除外）
- 日志消息用中文说明操作内容

### 类型标注
- 函数参数和返回值必须加类型标注
- 复杂类型用 `from typing import Optional, List, Dict`
- Python 3.10+ 可用 `str | None` 替代 `Optional[str]`

```python
def process_file(path: Path, encoding: str = 'utf-8') -> list[dict]:
    ...
```

### 异常处理
- 捕获具体异常类型，禁止裸 `except:`
- 文件操作指定 `encoding='utf-8'`
- 网络请求设置超时 `timeout=10`
- 关键操作用 try/except 包裹并记录日志

```python
try:
    resp = httpx.get(url, timeout=10)
    resp.raise_for_status()
except httpx.TimeoutException:
    logger.error(f'请求超时: {url}')
except httpx.HTTPStatusError as e:
    logger.error(f'HTTP 错误 {e.response.status_code}: {url}')
```

### argparse 参数
- 脚本入口使用 argparse 解析命令行参数
- 提供 `--help` 友好描述
- 必选参数用位置参数，可选参数用 `--flag`
- 提供合理默认值

```python
parser = argparse.ArgumentParser(description='批量处理数据文件')
parser.add_argument('input', type=Path, help='输入文件路径')
parser.add_argument('-o', '--output', type=Path, default=Path('output.csv'))
parser.add_argument('-v', '--verbose', action='store_true')
```

### 命名规范
- 函数/变量：`snake_case`
- 类名：`PascalCase`
- 常量：`UPPER_SNAKE_CASE`
- 私有方法/属性：`_leading_underscore`
- 文件名：小写 + 下划线，不用连字符

### 路径处理
- 一律使用 `pathlib.Path`，不用 `os.path.join`
- 文件存在检查：`path.exists()`
- 创建目录：`path.mkdir(parents=True, exist_ok=True)`
- 读写文件：`path.read_text(encoding='utf-8')`

## 自检清单
- [ ] 文件有模块文档字符串
- [ ] import 按标准库/第三方/本地分组
- [ ] 函数有类型标注
- [ ] 异常捕获是具体类型（非裸 except）
- [ ] 文件操作指定 encoding='utf-8'
- [ ] 有 `if __name__ == '__main__':` 入口
- [ ] 日志用 logging 而非 print
