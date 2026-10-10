"""LLM API 客户端 - 支持 OpenAI 兼容接口 + 演示模式"""

import json
import os
from threading import RLock
from openai import OpenAI
from openai import AuthenticationError, APIError
from dotenv import load_dotenv
from core.model_settings import DEFAULT_BASE_URL, DEFAULT_MODEL, normalize_provider_url, validate_model_name

load_dotenv()

_client = None
_clients = {}
_config = {}
_config_lock = RLock()
_CLIENT_CACHE_LIMIT = 128
DEMO_MODE = False  # 无 API Key 时自动启用演示模式

_AUTH_ERROR = '[api_error: API Key 无效或权限不足，请检查当前账号的模型配置]'
_API_ERROR = '[api_error: 模型服务请求失败，请稍后重试或检查配置]'
_REQUEST_ERROR = '[error: 模型请求失败，请检查配置后重试]'


def update_config(**kwargs):
    global _client, _config
    with _config_lock:
        _config.update(kwargs)
        _client = None
        _clients.clear()


def _selected_api_key(config_override=None):
    personal_key = config_override.get('api_key') if isinstance(config_override, dict) else None
    if personal_key is not None and not isinstance(personal_key, str):
        raise ValueError('API Key 必须是文本')
    if personal_key and personal_key.strip():
        return personal_key.strip(), True
    with _config_lock:
        key = _config.get('api_key', os.getenv('LLM_API_KEY', ''))
    if key is not None and not isinstance(key, str):
        raise ValueError('API Key 必须是文本')
    return (key or '').strip(), False


def _merged_config(config_override=None):
    with _config_lock:
        api_key, personal = _selected_api_key(config_override)
        shared = dict(_config)
        shared_base_url = shared.get('base_url') or os.getenv('LLM_BASE_URL') or DEFAULT_BASE_URL
        shared_model = shared.get('model') or os.getenv('LLM_MODEL') or DEFAULT_MODEL
    if personal:
        # A personal key belongs to its own provider. Missing personal settings
        # use our defaults, never the provider selected for the shared key.
        base_url = config_override.get('base_url') or DEFAULT_BASE_URL
        model = config_override.get('model') or DEFAULT_MODEL
    else:
        # Endpoint/model overrides without a personal key are ignored: they
        # cannot route the shared credential to another provider.
        base_url = shared_base_url
        model = shared_model
    return {
        'api_key': api_key,
        'base_url': normalize_provider_url(base_url),
        'model': validate_model_name(model),
    }


def is_demo_mode(config_override=None):
    """检查是否为演示模式（无有效 API Key）"""
    api_key, _personal = _selected_api_key(config_override)
    return DEMO_MODE or not api_key or api_key.startswith("sk-placeholder")


def get_client(config_override=None):
    with _config_lock:
        return _client_for_config(_merged_config(config_override))


def _prepare_request(config_override=None, model_override=''):
    # Resolve demo status, provider/key/model, and cache acquisition together.
    # update_config cannot clear the cache between an old configuration snapshot
    # and its insertion, or turn a pending request into a placeholder-key call.
    with _config_lock:
        if is_demo_mode(config_override):
            return None
        config = _merged_config(config_override)
        _api_key, personal = _selected_api_key(config_override)
        model = validate_model_name(model_override) if personal and model_override else config['model']
        return _client_for_config(config), model


def _client_for_config(config):
    global _client
    api_key = config['api_key'] or 'sk-placeholder'
    base_url = config['base_url']
    cache_key = (api_key, base_url)
    with _config_lock:
        client = _clients.pop(cache_key, None)
        if client is None:
            client = OpenAI(api_key=api_key, base_url=base_url)
        _clients[cache_key] = client
        while len(_clients) > _CLIENT_CACHE_LIMIT:
            _clients.pop(next(iter(_clients)))
        _client = client
        return client


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.3, model_override: str = "", config_override=None) -> str:
    """调用 LLM，返回原始文本。演示模式下返回 mock 数据"""
    try:
        prepared = _prepare_request(config_override, model_override)
        if prepared is None:
            return '[demo_mode]'
        client, model = prepared
        timeout = int(os.getenv("LLM_TIMEOUT", "300"))
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
        return _AUTH_ERROR
    except APIError:
        return _API_ERROR
    except Exception:
        return _REQUEST_ERROR


def call_llm_stream(system_prompt: str, user_prompt: str, temperature: float = 0.3, model_override: str = "", config_override=None):
    """流式调用 LLM，yield 文本块。演示模式下 yield '[demo_mode]'"""
    try:
        prepared = _prepare_request(config_override, model_override)
        if prepared is None:
            yield '[demo_mode]'
            return
        client, model = prepared
        timeout = int(os.getenv("LLM_TIMEOUT", "300"))
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
        yield _AUTH_ERROR
    except APIError:
        yield _API_ERROR
    except Exception:
        yield _REQUEST_ERROR


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
    if not isinstance(api_key, str) or not api_key.strip() or api_key.strip().startswith('sk-placeholder'):
        return False, "请输入 API Key"
    if not base_url:
        return False, "请选择 Base URL"
    if not model:
        return False, "请选择默认模型"
    try:
        base_url = normalize_provider_url(base_url)
        model = validate_model_name(model)
        client = get_client({'api_key': api_key, 'base_url': base_url, 'model': model})
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
    except ValueError:
        return False, '模型服务地址或模型名称不正确'
    except APIError:
        return False, '接口返回错误，请检查服务状态和模型配置'
    except Exception:
        return False, '连接失败，请检查模型配置后重试'
