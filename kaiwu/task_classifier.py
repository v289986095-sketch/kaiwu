"""任务分类器 — 控制 DeepSeek 各模块的注入策略（零 token 消耗）

纯关键词/规则逻辑，不调 LLM。在 server.py 各工具入口统一调用。

核心理念：分类器控制的是「注入什么内容」，不是「参不参与」。
- 经验记录和错误收集在任何模式下都运作
- 知识库注入才是按需开关的

v0.3 架构重构（消除 LEAN 黑名单的技术债）：

  旧方案：LEAN 黑名单正向匹配 → 不断加特例排除 → 维护成本高
  新方案：白名单驱动 — inject_knowledge 由 should_inject_knowledge() 统一控制
         ACTIVE/RESCUE 由正向信号触发，其余都是 NORMAL
         知识库注入在 NORMAL 下也通过 should_inject_knowledge() 按需开启

三个等级：
  - NORMAL:   常规模式 — 经验按需注入，知识库由 should_inject_knowledge 白名单控制
  - ACTIVE:   主动模式 — 主动注入知识库+经验+DeepSeek 规划
  - RESCUE:   救火模式 — 全力出马（循环/高错误数/高轮数）

注意：不再有 LEAN 等级。原 LEAN 场景（纯算法/SQL）走 NORMAL，
由于 should_inject_knowledge 白名单不会命中，知识库自然不注入，效果等同。
但"计算个税"这类交叉场景，白名单会命中"个税"→ 自然注入，无需特例。
"""

import re
from typing import NamedTuple

from loguru import logger


class TaskVerdict(NamedTuple):
    """分类结果"""
    level: str          # "normal" | "active" | "rescue"
    reason: str         # 人类可读的判断理由
    inject_knowledge: bool   # 是否注入知识库
    inject_experience: bool  # 是否注入经验
    call_llm: bool           # 是否允许调 DeepSeek LLM（规划/蒸馏）


# ── ACTIVE 类任务：知识库高增益，主动注入 ─────────────────────────────

_ACTIVE_KEYWORDS: dict[str, list[str]] = {
    "china": [
        "gbk", "utf-8", "编码", "乱码", "中文", "微信", "wechat", "支付宝",
        "alipay", "小程序", "抖音", "tiktok", "淘宝", "京东", "钉钉",
        "备案", "实名", "身份证", "手机号", "openid", "镜像源",
        "pip.*清华", "npm.*mirror", "taobao", "npmmirror",
        "腾讯云", "阿里云", "华为云", "七牛", "又拍",
        "坐标系", "gcj", "火星坐标", "高德", "百度地图",
        "a股", "股票", "akshare", "tushare", "回测",
        "gmv", "电商", "双十一",
        "jieba", "分词", "古诗", "农历", "春节", "节假日",
        "个税", "社保", "公积金",
        "pipl", "等保", "icp", "aigc", "数据出境", "隐私政策",
    ],
    "deploy": [
        "部署", "deploy", "nginx", "systemd", "gunicorn", "uwsgi",
        "docker", "compose", "kubernetes", "k8s", "ci/cd", "github actions",
        "服务器", "vps", "ssl", "https", "证书", "cert",
        "宝塔", "pm2", "supervisor", "systemctl",
    ],
    "encoding": [
        "编码", "encoding", "unicode", "ascii", "路径", "path",
        "windows.*路径", "反斜杠", "backslash",
        "gbk", "cp936", "locale", "codec",
    ],
    "deps": [
        "安装", "install", "pip install", "npm install", "yarn add",
        "依赖", "dependency", "版本冲突", "requirements",
        "node_modules", "package.json", "pyproject",
    ],
    "architecture": [
        "重构", "refactor", "架构", "architecture", "设计模式",
        "微服务", "microservice", "中间件", "middleware",
        "鉴权", "auth", "jwt", "oauth", "rbac",
        "websocket", "sse", "长连接", "消息队列", "mq", "redis",
    ],
}


def classify_task(
    task: str,
    turns: int = 0,
    error_count: int = 0,
    is_looping: bool = False,
) -> TaskVerdict:
    """判断当前任务的注入策略

    白名单驱动：
    1. RESCUE/ACTIVE 由正向信号触发 → 全量注入
    2. 其余都是 NORMAL → 知识库由 should_inject_knowledge 按需决定
    3. 经验注入在所有等级下都开启

    Args:
        task: 任务描述
        turns: 当前已进行的轮数
        error_count: 当前 session 的累计错误数
        is_looping: 是否处于循环检测状态

    Returns:
        TaskVerdict
    """
    if not task.strip():
        return TaskVerdict("normal", "空任务", False, True, False)

    task_lower = task.lower()
    task_clean = re.sub(r'[，。！？、；：""''【】（）《》…—]', ' ', task_lower)

    # ── 最高优先级：RESCUE ────────────────────────────────────────
    if is_looping:
        return TaskVerdict("rescue", "循环检测触发", True, True, True)
    if error_count >= 3:
        return TaskVerdict("rescue", f"累计 {error_count} 个错误", True, True, True)
    if turns >= 10:
        return TaskVerdict("rescue", f"已 {turns} 轮，升级为救火模式", True, True, True)

    # ── ACTIVE：高风险/中国特色/部署/架构 ─────────────────────────
    for category, keywords in _ACTIVE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in task_clean)
        if hits >= 2:
            return TaskVerdict(
                "active",
                f"{category} 相关（{hits} 个关键词命中）",
                True, True, True,
            )
        for kw in keywords:
            if len(kw) >= 4 and kw in task_clean:
                return TaskVerdict(
                    "active",
                    f"{category} 相关（强信号: {kw}）",
                    True, True, True,
                )

    # ── NORMAL：白名单驱动 ─────────────────────────────────────────
    # 知识库是否注入，由 should_inject_knowledge 在 server.py 逐个 KB 判断
    # 这里只做粗略标记：任何 KB 能命中就标记 inject_knowledge=True
    any_kb_hit = any(
        should_inject_knowledge(task, kb)
        for kb in ("china_kb", "python_compat", "deps_pitfalls", "tool_priming")
    )

    return TaskVerdict(
        "normal", "常规任务",
        inject_knowledge=any_kb_hit,
        inject_experience=True,
        call_llm=False,
    )


def should_inject_knowledge(task: str, kb_name: str) -> bool:
    """判断特定知识库是否应该注入（白名单匹配）

    这是整个注入策略的核心：所有"要不要注入某个 KB"的判断都集中在这里。
    新增场景只需在对应 KB 的触发词列表里加一个词，不需要改其他任何地方。
    """
    task_lower = task.lower()
    task_clean = re.sub(r'[，。！？、；：""''【】（）《》…—]', ' ', task_lower)

    _KB_TRIGGERS: dict[str, list[str]] = {
        "china_kb": [
            "gbk", "utf", "编码", "乱码", "中文", "镜像", "mirror",
            "微信", "wechat", "支付宝", "alipay", "小程序", "抖音",
            "腾讯", "阿里", "华为", "百度", "高德", "坐标",
            "备案", "身份证", "手机号", "openid",
            "npm.*mirror", "pip.*清华", "docker.*mirror",
            # A股/金融
            "a股", "股票", "akshare", "tushare", "baostock", "macd",
            "k线", "回测", "涨跌停", "复权",
            # 电商
            "gmv", "电商", "双十一", "618", "客单价", "复购",
            # 中文NLP/古诗词
            "jieba", "分词", "古诗", "唐诗", "宋词", "繁简转换",
            # 农历/节假日
            "农历", "春节", "节假日", "节气", "生肖", "lunardate",
            # 个税/社保
            "个税", "个人所得税", "社保", "公积金", "年终奖", "税后",
            # 法规合规
            "pipl", "等保", "icp", "aigc.*合规", "数据出境",
            "隐私政策", "未成年人", "内容审核",
        ],
        "python_compat": [
            "python.*版本", "python.*3\\.\\d", "兼容", "compat",
            "deprecated", "breaking change", "升级.*python",
        ],
        "deps_pitfalls": [
            "安装", "install", "pip", "npm", "yarn", "pnpm",
            "依赖", "dependency", "版本冲突", "requirements",
            "build.*fail", "编译.*失败", "wheel", "binary",
        ],
        "tool_priming": [
            "mcp", "tool", "工具", "function call",
        ],
    }

    triggers = _KB_TRIGGERS.get(kb_name, [])
    if not triggers:
        return False

    for trigger in triggers:
        if re.search(trigger, task_clean):
            return True

    return False


def extract_task_tokens(task_lower: str) -> set[str]:
    """从任务描述中提取搜索关键词

    英文：3+ 字符的完整单词
    中文：2字 ngram 滑窗（因为中文无空格分词）
    """
    tokens = set()

    # 英文单词
    tokens.update(re.findall(r'[a-zA-Z_]{3,}', task_lower))

    # 中文：提取连续中文段，再做 2字 ngram
    for seg in re.findall(r'[\u4e00-\u9fff]+', task_lower):
        for i in range(len(seg) - 1):
            tokens.add(seg[i:i+2])

    return tokens
