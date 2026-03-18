"""统一 LLM 调用客户端

根据 config 中 api_format 自动选择调用方式：
  - "openai"     → OpenAI SDK (openai.OpenAI)
  - "anthropic"  → httpx.post 调用 /v1/messages（Anthropic 原生格式）

容错机制：
  - 指数退避重试（最多 2 次重试，共 3 次尝试）
  - 简易熔断器：连续失败 5 次后短路 60s，避免雪崩

无需新增依赖：openai 和 httpx 均在现有依赖链中。
"""

import time
from typing import Optional

from loguru import logger

from kaiwu.config import get_config, DEFAULT_MAX_TOKENS, DEFAULT_TIMEOUT

# 重试配置
MAX_RETRIES = 2        # 最多重试 2 次（共 3 次尝试）
RETRY_BASE_DELAY = 3.0 # 首次重试间隔秒数（指数退避：3s → 6s）
_RETRYABLE_ERRORS = (
    "timeout", "timed out", "connection", "connect",
    "502", "503", "429", "rate limit", "overloaded",
    "server error", "internal server error",
)

# 简易熔断器状态
_circuit_breaker = {
    "consecutive_failures": 0,
    "open_until": 0.0,         # 熔断器打开截止时间
}
_CB_THRESHOLD = 5              # 连续失败 N 次触发熔断
_CB_COOLDOWN = 60.0            # 熔断冷却时间（秒）


def _is_retryable(error: Exception) -> bool:
    """判断错误是否值得重试（网络/超时/限流类错误）"""
    error_str = str(error).lower()
    return any(keyword in error_str for keyword in _RETRYABLE_ERRORS)


def _check_circuit_breaker() -> tuple[bool, str]:
    """检查熔断器状态

    Returns:
        (is_open, message) — True 表示熔断器打开，应拒绝调用
    """
    now = time.time()
    if _circuit_breaker["open_until"] > now:
        remaining = int(_circuit_breaker["open_until"] - now)
        return True, f"LLM 熔断器已触发（连续 {_CB_THRESHOLD} 次失败），{remaining}s 后自动恢复"
    # 冷却期过了，自动半开
    if _circuit_breaker["open_until"] > 0 and now >= _circuit_breaker["open_until"]:
        _circuit_breaker["open_until"] = 0.0
        _circuit_breaker["consecutive_failures"] = 0
    return False, ""


def _record_success():
    """调用成功，重置熔断器"""
    _circuit_breaker["consecutive_failures"] = 0
    _circuit_breaker["open_until"] = 0.0


def _record_failure():
    """调用失败，累加计数，达阈值触发熔断"""
    _circuit_breaker["consecutive_failures"] += 1
    if _circuit_breaker["consecutive_failures"] >= _CB_THRESHOLD:
        _circuit_breaker["open_until"] = time.time() + _CB_COOLDOWN
        logger.warning(
            f"LLM 熔断器触发: 连续 {_CB_THRESHOLD} 次失败，"
            f"暂停 {_CB_COOLDOWN}s"
        )


def call_llm(
    messages: list[dict],
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = 0.3,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """统一调用 LLM，返回文本内容

    容错机制：
    1. 指数退避重试：3s → 6s（最多 2 次重试，共 3 次尝试）
    2. 只重试瞬态错误（超时/网络/限流/5xx），认证/参数错误直接抛出
    3. 简易熔断器：连续失败 5 次后短路 60s，避免持续请求加重问题

    Args:
        messages: OpenAI 格式的消息列表 [{"role": "system"/"user", "content": "..."}]
        max_tokens: 最大输出 token 数
        temperature: 温度参数
        timeout: 超时秒数

    Returns:
        模型返回的文本内容。调用失败时抛出异常。
    """
    # 熔断检查
    is_open, cb_msg = _check_circuit_breaker()
    if is_open:
        raise RuntimeError(cb_msg)

    config = get_config()
    api_format = config.llm_api_format

    last_error: Optional[Exception] = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            if api_format == "anthropic":
                result = _call_anthropic(messages, max_tokens, temperature, timeout)
            else:
                result = _call_openai(messages, max_tokens, temperature, timeout)
            _record_success()
            return result
        except Exception as e:
            last_error = e
            _record_failure()
            if attempt < MAX_RETRIES and _is_retryable(e):
                delay = RETRY_BASE_DELAY * (2 ** attempt)  # 3s, 6s
                logger.info(
                    f"LLM 调用失败（第 {attempt + 1} 次）: {e}，"
                    f"{delay:.0f}s 后重试..."
                )
                time.sleep(delay)
            else:
                raise

    # 理论上不会走到这里，但保险起见
    raise last_error  # type: ignore


def _call_openai(
    messages: list[dict],
    max_tokens: int,
    temperature: float,
    timeout: int,
) -> str:
    """通过 OpenAI SDK 调用（兼容 DeepSeek / OpenAI / 任何 OpenAI 兼容 API）"""
    from openai import OpenAI

    config = get_config()
    client = OpenAI(
        api_key=config.llm_api_key,
        base_url=config.llm_base_url,
    )

    response = client.chat.completions.create(
        model=config.llm_model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=timeout,
    )

    return response.choices[0].message.content or ""


def _call_anthropic(
    messages: list[dict],
    max_tokens: int,
    temperature: float,
    timeout: int,
) -> str:
    """通过 httpx 调用 Anthropic 原生 /v1/messages 接口"""
    import httpx

    config = get_config()
    base_url = config.llm_base_url.rstrip("/")

    # 从 messages 中提取 system 消息（Anthropic 格式需要单独的 system 参数）
    system_text: Optional[str] = None
    non_system_messages: list[dict] = []
    for msg in messages:
        if msg["role"] == "system":
            system_text = msg["content"]
        else:
            non_system_messages.append({"role": msg["role"], "content": msg["content"]})

    body: dict = {
        "model": config.llm_model,
        "messages": non_system_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if system_text:
        body["system"] = system_text

    headers = {
        "x-api-key": config.llm_api_key or "",
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    resp = httpx.post(
        f"{base_url}/v1/messages",
        headers=headers,
        json=body,
        timeout=timeout,
    )
    resp.raise_for_status()

    data = resp.json()
    # Anthropic 响应格式: {"content": [{"type": "text", "text": "..."}]}
    content_blocks = data.get("content", [])
    if content_blocks:
        return content_blocks[0].get("text", "")
    return ""
