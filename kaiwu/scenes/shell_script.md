---
key: shell_script
name: Shell 脚本
keywords: [bash, shell, sh, 脚本, 运维, 部署, deploy, linux, 命令行]
---

# Shell 脚本规范

## 快速参考
| 任务 | 推荐方案 |
|------|---------|
| 安全头 | set -euo pipefail |
| 日志 | 自定义 log 函数 + 时间戳 |
| 参数解析 | getopts 或 case 语句 |
| 路径 | SCRIPT_DIR 变量 |

## 核心规范

### 脚本头部（固定模板）
```bash
#!/usr/bin/env bash
set -euo pipefail

# 脚本说明：一句话描述用途
# 用法：./script.sh [选项] <参数>

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
```

- `set -e`：命令失败立即退出
- `set -u`：引用未定义变量报错
- `set -o pipefail`：管道中任一命令失败则整体失败

### 日志函数
```bash
log_info()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO]  $*"; }
log_warn()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN]  $*" >&2; }
log_error() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" >&2; }
```

- 所有输出通过 log 函数，不直接 echo
- 警告和错误输出到 stderr（`>&2`）
- 关键步骤前后打印日志

### 变量默认值
- 使用 `${VAR:-default}` 提供默认值
- 使用 `${VAR:?'错误信息'}` 要求必填
- 变量引用一律加双引号：`"${MY_VAR}"`

```bash
OUTPUT_DIR="${1:-./output}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
API_KEY="${API_KEY:?'必须设置 API_KEY 环境变量'}"
```

### 错误处理
- 可能失败的命令用 `|| {}` 兜底
- 重要操作前检查前置条件
- 提供 cleanup 函数配合 trap

```bash
cleanup() {
    log_info "清理临时文件..."
    rm -rf "${TMP_DIR:-/tmp/script_tmp}"
}
trap cleanup EXIT

# 前置检查
command -v python3 >/dev/null 2>&1 || {
    log_error "python3 未安装"
    exit 1
}
```

### 依赖检查
- 脚本开头检查所需命令是否存在
- 使用 `command -v` 而非 `which`（更可移植）
- 缺失依赖给出安装提示

```bash
check_deps() {
    local missing=()
    for cmd in python3 jq curl; do
        command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "缺少依赖: ${missing[*]}"
        exit 1
    fi
}
check_deps
```

### POSIX 兼容注意
- 数组、`[[ ]]`、`{a..z}` 是 bash 扩展，非 POSIX
- 如果需要在 sh 上运行，避免 bash 特有语法
- shebang 明确写 `bash` 还是 `sh`

### 文件与路径
- 临时文件用 `mktemp`：`TMP_FILE=$(mktemp)`
- 路径拼接用变量：`"${SCRIPT_DIR}/config.yml"`
- 检查文件存在：`[[ -f "$file" ]]`
- 检查目录存在：`[[ -d "$dir" ]]`

### 函数编写
- 函数名用小写 + 下划线
- 局部变量用 `local` 声明
- 函数返回状态码，不用 echo 传值（除非管道）

```bash
create_backup() {
    local src="$1"
    local dst="${2:-${src}.bak}"
    cp -r "$src" "$dst"
    log_info "备份完成: $src -> $dst"
}
```

## 自检清单
- [ ] 脚本头部有 set -euo pipefail
- [ ] 有 SCRIPT_DIR 变量
- [ ] 变量引用加了双引号
- [ ] 日志有时间戳和级别
- [ ] 依赖命令做了检查
- [ ] 临时文件有 trap cleanup
- [ ] 错误输出到 stderr
