"""Shared validation for supported model providers and model identifiers."""

import re
from urllib.parse import urlsplit


DEFAULT_MODEL = "deepseek-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"

_PROVIDER_PATHS = {
    "api.deepseek.com": "/v1",
    "dashscope.aliyuncs.com": "/compatible-mode/v1",
    "open.bigmodel.cn": "/api/paas/v4",
    "api.moonshot.cn": "/v1",
    "api.openai.com": "/v1",
}
_MODEL_NAME = re.compile(r"[a-zA-Z0-9_./:-]+", flags=re.ASCII)


def normalize_provider_url(value):
    """Return a canonical, explicitly supported HTTPS API base URL."""
    error = "请选择受支持的 HTTPS 模型服务地址"
    if not isinstance(value, str) or not value.strip():
        raise ValueError(error)
    # urlsplit silently removes several control characters. Reject them before
    # parsing so a displayed URL and its actual destination cannot disagree.
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError(error)
    value = value.strip()
    if "?" in value or "#" in value or "\\" in value:
        raise ValueError(error)
    try:
        parts = urlsplit(value)
        host = parts.hostname
        port = parts.port
    except ValueError:
        raise ValueError(error) from None
    if (
        parts.scheme.lower() != "https"
        or host not in _PROVIDER_PATHS
        or parts.username is not None
        or parts.password is not None
        or port not in (None, 443)
        or parts.netloc.lower() not in (host, f"{host}:443")
        or parts.path.rstrip("/") != _PROVIDER_PATHS[host]
    ):
        raise ValueError(error)
    return f"https://{host}{_PROVIDER_PATHS[host]}"


def validate_model_name(value):
    """Accept a short text identifier without whitespace or control characters."""
    if not isinstance(value, str) or not 1 <= len(value) <= 100 or not _MODEL_NAME.fullmatch(value):
        raise ValueError("模型名称需为1至100个字符，且只能包含字母、数字、_ . / : -")
    return value
