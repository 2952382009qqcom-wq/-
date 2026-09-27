"""LLM API 客户端 - 支持 OpenAI 兼容接口 + 演示模式"""

import json
import os
from openai import OpenAI
from openai import AuthenticationError, APIError
from dotenv import load_dotenv

load_dotenv()

_client = None
_clients = {}
_config = {}
DEMO_MODE = False  # 无 API Key 时自动启用演示模式


def update_config(**kwargs):
    global _client, _config
    _config.update(kwargs)
    _client = None


def _merged_config(config_override=None):
    config = dict(_config)
    if config_override:
        config.update({k: v for k, v in config_override.items() if v})
    return config


def is_demo_mode(config_override=None):
    """检查是否为演示模式（无有效 API Key）"""
    config = _merged_config(config_override)
    api_key = config.get("api_key") or os.getenv("LLM_API_KEY", "")
    return DEMO_MODE or not api_key or api_key.startswith("sk-placeholder")


def get_client(config_override=None):
    global _client
    config = _merged_config(config_override)
    api_key = config.get("api_key") or os.getenv("LLM_API_KEY", "sk-placeholder")
    base_url = config.get("base_url") or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    cache_key = (api_key, base_url)
    if config_override:
        if cache_key not in _clients:
            _clients[cache_key] = OpenAI(api_key=api_key, base_url=base_url)
        return _clients[cache_key]
    if _client is None:
        _client = OpenAI(api_key=api_key, base_url=base_url)
    return _client


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.3, model_override: str = "", config_override=None) -> str:
    """调用 LLM，返回原始文本。演示模式下返回 mock 数据"""
    if is_demo_mode(config_override):
        return '[demo_mode]'

    config = _merged_config(config_override)
    model = model_override or config.get("model") or os.getenv("LLM_MODEL", "gpt-4o")
    timeout = int(os.getenv("LLM_TIMEOUT", "300"))

    try:
        client = get_client(config_override)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            timeout=timeout,
        )
        return response.choices[0].message.content
    except AuthenticationError:
        global DEMO_MODE
        DEMO_MODE = True
        return '[demo_mode]'
    except APIError as e:
        return f'[api_error: {str(e)[:200]}]'
    except Exception as e:
        return f'[error: {str(e)[:200]}]'


def call_llm_stream(system_prompt: str, user_prompt: str, temperature: float = 0.3, model_override: str = "", config_override=None):
    """流式调用 LLM，yield 文本块。演示模式下 yield '[demo_mode]'"""
    if is_demo_mode(config_override):
        yield '[demo_mode]'
        return

    config = _merged_config(config_override)
    model = model_override or config.get("model") or os.getenv("LLM_MODEL", "gpt-4o")
    timeout = int(os.getenv("LLM_TIMEOUT", "300"))

    try:
        client = get_client(config_override)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            timeout=timeout,
            stream=True,
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except AuthenticationError:
        global DEMO_MODE
        DEMO_MODE = True
        yield '[demo_mode]'
    except APIError as e:
        yield f'[api_error: {str(e)[:200]}]'
    except Exception as e:
        yield f'[error: {str(e)[:200]}]'


def _parse_json_response(raw: str) -> dict:
    """解析 LLM 返回的 JSON，处理 markdown 代码块包裹"""
    if raw == '[demo_mode]':
        return {"demo_mode": True}
    if raw.startswith('[api_error:') or raw.startswith('[error:'):
        return {"error": raw}

    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            return {
                "error": "模型返回的 JSON 顶层必须是对象",
                "invalid_response_type": type(parsed).__name__,
            }
        return parsed
    except json.JSONDecodeError:
        return {"raw_response": raw, "parse_error": True}


def call_llm_json(system_prompt: str, user_prompt: str, temperature: float = 0.2, model_override: str = "", config_override=None) -> dict:
    """调用 LLM 并解析 JSON 响应"""
    raw = call_llm(system_prompt, user_prompt, temperature, model_override, config_override)
    return _parse_json_response(raw)


def call_llm_stream_json(system_prompt: str, user_prompt: str, temperature: float = 0.2, model_override: str = "", config_override=None):
    """流式调用 LLM，先 yield 文本块，最后 yield 解析后的 JSON 对象。

    用法：
        for item in call_llm_stream_json(sys, usr):
            if isinstance(item, str):
                print(item, end="")  # 文本块
            else:
                result = item  # 最终的 dict
    """
    full_text = ""
    for chunk in call_llm_stream(system_prompt, user_prompt, temperature, model_override, config_override):
        if chunk.startswith('[') and (chunk.startswith('[demo_mode]') or chunk.startswith('[api_error:') or chunk.startswith('[error:')):
            yield _parse_json_response(chunk)
            return
        full_text += chunk
        yield chunk
    yield _parse_json_response(full_text)


def test_llm_connection(api_key: str, base_url: str, model: str):
    """用一次极小请求测试 OpenAI 兼容接口是否可用。"""
    if not api_key:
        return False, "请输入 API Key"
    if not base_url:
        return False, "请选择 Base URL"
    if not model:
        return False, "请选择默认模型"
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            temperature=0,
            max_tokens=8,
            timeout=30,
        )
        return True, "连接测试成功"
    except AuthenticationError:
        return False, "API Key 无效或权限不足"
    except APIError as e:
        return False, f"接口返回错误：{str(e)[:160]}"
    except Exception as e:
        return False, f"连接失败：{str(e)[:160]}"
