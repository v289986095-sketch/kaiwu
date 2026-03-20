# 贡献指南

感谢你对 kaiwu 的关注！以下是参与贡献的指南。

## 开发环境搭建

```bash
# 克隆仓库
git clone https://github.com/val1813/kaiwu.git
cd kaiwu

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
python -m pytest tests/ -v
```

## 提交 Pull Request

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 编写代码和测试
4. 确保所有测试通过：`python -m pytest tests/ -v`
5. 确保代码风格一致：`ruff check kaiwu/`
6. 提交并推送：`git push origin feature/your-feature`
7. 创建 Pull Request

## 代码规范

- Python 3.10+
- 使用 [ruff](https://github.com/astral-sh/ruff) 进行代码检查
- 行宽限制 100 字符
- 文件编码统一 UTF-8
- 所有公共函数需要 docstring
- 新功能需要配套单元测试

## 测试

```bash
# 运行全部测试
python -m pytest tests/ -v

# 运行单个测试文件
python -m pytest tests/test_experience.py -v

# 运行带覆盖率
python -m pytest tests/ --cov=kaiwu --cov-report=term-missing
```

## 项目结构

```
kaiwu/
├── server.py          # MCP Server（7 个工具入口）
├── planner.py         # DeepSeek 规划引擎
├── lessons.py         # 三层错误诊断
├── recorder.py        # 任务记录 + 轨迹审计
├── condenser.py       # 上下文压缩
├── session.py         # 会话管理
├── config.py          # 配置管理
├── llm_client.py      # LLM 调用客户端
├── task_classifier.py # 任务分类器（零 token）
├── storage/
│   ├── experience.py  # 经验库
│   └── error_kb.py    # 错误知识库
├── knowledge/         # 知识库 MD 文件
└── scenes/            # 编码场景规范
```

## 贡献者协议

提交 Pull Request 前，请阅读并签署 [贡献者许可协议（CLA）](CLA.md)。
