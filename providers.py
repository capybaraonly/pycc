"""
pycc 的多厂商支持模块。

支持的厂商：
  anthropic  — Claude（claude-opus-4-6、claude-sonnet-4-6 等）
  openai     — GPT（gpt-4o、o3-mini 等）
  gemini     — 谷歌 Gemini（gemini-2.0-flash、gemini-1.5-pro 等）
  kimi       — 月之暗面 AI（moonshot-v1-8k/32k/128k）
  qwen       — 阿里通义千问（qwen-max、qwen-plus 等）
  zhipu      — 智谱 GLM（glm-4、glm-4-plus 等）
  deepseek   — 深度求索（deepseek-chat、deepseek-reasoner 等）
  minimax    — 迷你最大（MiniMax-Text-01、abab6.5s-chat 等）
  ollama     — 本地 Ollama（llama3.3、qwen2.5-coder 等）
  lmstudio   — 本地 LM Studio（任意已加载模型）
  custom     — 任意兼容 OpenAI 接口的端点

模型字符串格式：
  "claude-opus-4-6"          自动识别 → anthropic
  "gpt-4o"                   自动识别 → openai
  "ollama/qwen2.5-coder"     显式指定厂商前缀
  "custom/my-model"          使用配置中的 CUSTOM_BASE_URL
"""
from __future__ import annotations
import json
import urllib.request
from typing import Generator

# ── 厂商注册中心 ──────────────────────────────────────────────────────

PROVIDERS: dict[str, dict] = {
    "anthropic": {
        "type":       "anthropic",
        "api_key_env": "ANTHROPIC_API_KEY",
        "context_limit": 200000,
        "models": [
            "claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001",
            "claude-opus-4-5", "claude-sonnet-4-5",
            "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022",
        ],
    },
    "openai": {
        "type":       "openai",
        "api_key_env": "OPENAI_API_KEY",
        "base_url":   "https://api.openai.com/v1",
        "context_limit": 128000,
        "max_completion_tokens": 16384,  # gpt-4o/gpt-4.1 系列通用安全上限
        "models": [
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4.1", "gpt-4.1-mini",
            "o3-mini", "o1", "o1-mini",
        ],
    },
    "gemini": {
        "type":       "openai",
        "api_key_env": "GEMINI_API_KEY",
        "base_url":   "https://generativelanguage.googleapis.com/v1beta/openai/",
        "context_limit": 1000000,
        "models": [
            "gemini-2.5-pro-preview-03-25",
            "gemini-2.0-flash", "gemini-2.0-flash-lite",
            "gemini-1.5-pro", "gemini-1.5-flash",
        ],
    },
    "kimi": {
        "type":       "openai",
        "api_key_env": "MOONSHOT_API_KEY",
        "base_url":   "https://api.moonshot.cn/v1",
        "context_limit": 128000,
        "models": [
            "moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k",
            "kimi-latest",
        ],
    },
    "qwen": {
        "type":       "openai",
        "api_key_env": "DASHSCOPE_API_KEY",
        "base_url":   "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "context_limit": 1000000,
        "models": [
            "qwen-max", "qwen-plus", "qwen-turbo", "qwen-long",
            "qwen2.5-72b-instruct", "qwen2.5-coder-32b-instruct",
            "qwq-32b",
        ],
    },
    "zhipu": {
        "type":       "openai",
        "api_key_env": "ZHIPU_API_KEY",
        "base_url":   "https://open.bigmodel.cn/api/paas/v4/",
        "context_limit": 128000,
        "models": [
            "glm-4-plus", "glm-4", "glm-4-flash", "glm-4-air",
            "glm-z1-flash",
        ],
    },
    "deepseek": {
        "type":       "openai",
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url":   "https://api.deepseek.com/v1",
        "context_limit": 64000,
        "models": [
            "deepseek-chat", "deepseek-coder", "deepseek-reasoner",
        ],
    },
    "minimax": {
        "type":       "openai",
        "api_key_env": "MINIMAX_API_KEY",
        "base_url":   "https://api.minimaxi.chat/v1",
        "context_limit": 1000000,
        "models": [
            "MiniMax-Text-01", "MiniMax-VL-01",
            "abab6.5s-chat", "abab6.5-chat",
            "abab5.5s-chat", "abab5.5-chat",
        ],
    },
    "ollama": {
        "type":       "ollama",
        "api_key_env": None,
        "base_url":   "http://localhost:11434",
        "api_key":    "ollama",
        "context_limit": 128000,
        "models": [
            "llama3.3", "llama3.2", "phi4", "mistral", "mixtral",
            "qwen2.5-coder", "deepseek-r1", "gemma3",
        ],
    },
    "lmstudio": {
        "type":       "openai",
        "api_key_env": None,
        "base_url":   "http://localhost:1234/v1",
        "api_key":    "lm-studio",
        "context_limit": 128000,
        "models": [],   # 动态，取决于加载的模型
    },
    "custom": {
        "type":       "openai",
        "api_key_env": "CUSTOM_API_KEY",
        "base_url":   None,   # 从 config["custom_base_url"] 读取
        "context_limit": 128000,
        "models": [],
    },
}

# 每百万 tokens 成本（近似值，未知模型返回 0）
COSTS = {
    "claude-opus-4-6":          (15.0, 75.0),
    "claude-sonnet-4-6":        (3.0,  15.0),
    "claude-haiku-4-5-20251001": (0.8,  4.0),
    "gpt-4o":                   (2.5,  10.0),
    "gpt-4o-mini":              (0.15,  0.6),
    "o3-mini":                  (1.1,   4.4),
    "gemini-2.0-flash":         (0.075, 0.3),
    "gemini-1.5-pro":           (1.25,  5.0),
    "gemini-2.5-pro-preview-03-25": (1.25, 10.0),
    "moonshot-v1-8k":           (1.0,   3.0),
    "moonshot-v1-32k":          (2.4,   7.0),
    "moonshot-v1-128k":         (8.0,  24.0),
    "qwen-max":                 (2.4,   9.6),
    "qwen-plus":                (0.4,   1.2),
    "deepseek-chat":            (0.27,  1.1),
    "deepseek-reasoner":        (0.55,  2.19),
    "glm-4-plus":               (0.7,   0.7),
    "MiniMax-Text-01":          (0.7,   2.1),
    "abab6.5s-chat":            (0.1,   0.1),
    "abab6.5-chat":             (0.5,   0.5),
}

# 自动识别规则：前缀 → 厂商名
_PREFIXES = [
    ("claude-",       "anthropic"),
    ("gpt-",          "openai"),
    ("o1",            "openai"),
    ("o3",            "openai"),
    ("gemini-",       "gemini"),
    ("moonshot-",     "kimi"),
    ("kimi-",         "kimi"),
    ("qwen",          "qwen"),  # qwen-max、qwen2.5-...
    ("qwq-",          "qwen"),
    ("glm-",          "zhipu"),
    ("deepseek-",     "deepseek"),
    ("minimax-",      "minimax"),
    ("MiniMax-",      "minimax"),
    ("abab",          "minimax"),
    ("llama",         "ollama"),
    ("mistral",       "ollama"),
    ("phi",           "ollama"),
    ("gemma",         "ollama"),
]


def detect_provider(model: str) -> str:
    """根据模型字符串返回厂商名称。
    支持 '厂商/模型' 显式格式，或根据前缀自动识别。"""
    if "/" in model:
        return model.split("/", 1)[0]
    for prefix, pname in _PREFIXES:
        if model.lower().startswith(prefix):
            return pname
    return "openai"   # 默认兜底


def bare_model(model: str) -> str:
    """如果存在 '厂商/' 前缀，将其去除。"""
    return model.split("/", 1)[1] if "/" in model else model


def get_api_key(provider_name: str, config: dict) -> str:
    prov = PROVIDERS.get(provider_name, {})
    # 1. 优先从配置字典读取（例如 config["kimi_api_key"]）
    cfg_key = config.get(f"{provider_name}_api_key", "")
    if cfg_key:
        return cfg_key
    # 2. 从环境变量读取
    env_var = prov.get("api_key_env")
    if env_var:
        import os
        return os.environ.get(env_var, "")
    # 3. 硬编码默认值（本地厂商使用）
    return prov.get("api_key", "")


def calc_cost(model: str, in_tok: int, out_tok: int) -> float:
    ic, oc = COSTS.get(bare_model(model), (0.0, 0.0))
    return (in_tok * ic + out_tok * oc) / 1_000_000


# ── 工具格式转换 ─────────────────────────────────────────────────

def tools_to_openai(tool_schemas: list) -> list:
    """将 Anthropic 风格的工具描述转换为 OpenAI 函数调用格式。"""
    return [
        {
            "type": "function",
            "function": {
                "name":        t["name"],
                "description": t["description"],
                "parameters":  t["input_schema"],
            },
        }
        for t in tool_schemas
    ]


# ── 消息格式转换 ──────────────────────────────────────────────
#
# 内部统一消息格式：
#   {"role": "user",      "content": "文本"}
#   {"role": "assistant", "content": "文本", "tool_calls": [
#       {"id": "...", "name": "...", "input": {...}}
#   ]}
#   {"role": "tool", "tool_call_id": "...", "name": "...", "content": "..."}

def messages_to_anthropic(messages: list) -> list:
    """将统一消息格式 → 转换为 Anthropic API 格式。"""
    result = []
    i = 0
    while i < len(messages):
        m = messages[i]
        role = m["role"]

        if role == "user":
            result.append({"role": "user", "content": m["content"]})
            i += 1

        elif role == "assistant":
            blocks = []
            text = m.get("content", "")
            if text:
                blocks.append({"type": "text", "text": text})
            for tc in m.get("tool_calls", []):
                blocks.append({
                    "type":  "tool_use",
                    "id":    tc["id"],
                    "name":  tc["name"],
                    "input": tc["input"],
                })
            result.append({"role": "assistant", "content": blocks})
            i += 1

        elif role == "tool":
            # 将连续的工具结果合并为一条用户消息
            tool_blocks = []
            while i < len(messages) and messages[i]["role"] == "tool":
                t = messages[i]
                tool_blocks.append({
                    "type":        "tool_result",
                    "tool_use_id": t["tool_call_id"],
                    "content":     t["content"],
                })
                i += 1
            result.append({"role": "user", "content": tool_blocks})

        else:
            i += 1

    return result


def messages_to_openai(messages: list, ollama_native_images: bool = False) -> list:
    """将统一消息格式 → 转换为 OpenAI API 格式。

    参数：
        ollama_native_images: 如果为 True，直接在用户消息中传递 'images' 列表
                              使用 Ollama 原生格式（消息对象上的 base64 列表）。
                              仅在目标为 Ollama 后端时设置。
                              如果为 False（默认），图片会转换为 OpenAI/Gemini
                              的 multipart ``image_url`` 格式，确保视觉模型正常识别。
    """
    result = []
    for m in messages:
        role = m["role"]

        if role == "user":
            content = m["content"]
            if ollama_native_images and m.get("images"):
                # Ollama 原生格式：消息上直接带 base64 图片列表
                msg_out = {"role": "user", "content": content, "images": m["images"]}
            elif not ollama_native_images and m.get("images"):
                # OpenAI / Gemini 视觉格式
                parts = [{"type": "text", "text": content}]
                for img_b64 in m["images"]:
                    parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                    })
                msg_out = {"role": "user", "content": parts}
            else:
                msg_out = {"role": "user", "content": content}
            result.append(msg_out)

        elif role == "assistant":
            msg: dict = {"role": "assistant", "content": m.get("content") or None}
            tcs = m.get("tool_calls", [])
            if tcs:
                msg["tool_calls"] = []
                for tc in tcs:
                    tc_msg = {
                        "id":   tc["id"],
                        "type": "function",
                        "function": {
                            "name":      tc["name"],
                            "arguments": json.dumps(tc["input"], ensure_ascii=False),
                        },
                    }
                    # 透传厂商专属字段（例如 Gemini thought_signature）
                    if tc.get("extra_content"):
                        tc_msg["extra_content"] = tc["extra_content"]
                    msg["tool_calls"].append(tc_msg)
            result.append(msg)

        elif role == "tool":
            result.append({
                "role":         "tool",
                "tool_call_id": m["tool_call_id"],
                "content":      m["content"],
            })

    return result


# ── 流式响应适配器 ─────────────────────────────────────────────────────

class TextChunk:
    """实时文字片段"""
    def __init__(self, text): self.text = text

class ThinkingChunk:
    """实时思考片段"""
    def __init__(self, text): self.text = text

class Response:
    """完成的一轮助手响应，包含文本 + 工具调用。"""
    def __init__(self, text, tool_calls, in_tokens, out_tokens):
        self.text        = text
        self.tool_calls  = tool_calls   # 列表：{id, name, input}
        self.in_tokens   = in_tokens
        self.out_tokens  = out_tokens


def stream_anthropic(
    api_key: str,
    model: str,
    system: str,
    messages: list,
    tool_schemas: list,
    config: dict,
) -> Generator:
    """从 Anthropic API 流式获取响应。
    先抛出 TextChunk/ThinkingChunk，最后抛出 Response。"""
    import anthropic as _ant
    client = _ant.Anthropic(api_key=api_key)

    kwargs = {
        "model":      model,
        "max_tokens": config.get("max_tokens", 8192),
        "system":     system,
        "messages":   messages_to_anthropic(messages),
        "tools":      tool_schemas,
    }
    if config.get("thinking"):
        kwargs["thinking"] = {
            "type":          "enabled",
            "budget_tokens": config.get("thinking_budget", 10000),
        }

    tool_calls = []
    text       = ""

    with client.messages.stream(**kwargs) as stream:
        for event in stream:
            etype = getattr(event, "type", None)
            if etype == "content_block_delta":
                delta = event.delta
                dtype = getattr(delta, "type", None)
                if dtype == "text_delta":
                    text += delta.text
                    yield TextChunk(delta.text)
                elif dtype == "thinking_delta":
                    yield ThinkingChunk(delta.thinking)

        final = stream.get_final_message()
        for block in final.content:
            if block.type == "tool_use":
                tool_calls.append({
                    "id":    block.id,
                    "name":  block.name,
                    "input": block.input,
                })

        yield Response(
            text, tool_calls,
            final.usage.input_tokens,
            final.usage.output_tokens,
        )


def stream_openai_compat(
    api_key: str,
    base_url: str,
    model: str,
    system: str,
    messages: list,
    tool_schemas: list,
    config: dict,
) -> Generator:
    """从任意兼容 OpenAI 接口的 API 流式获取响应。
    先抛出 TextChunk，最后抛出 Response。"""
    from openai import OpenAI
    client = OpenAI(api_key=api_key or "dummy", base_url=base_url)

    oai_messages = [{"role": "system", "content": system}] + messages_to_openai(messages)

    kwargs: dict = {
        "model":    model,
        "messages": oai_messages,
        "stream":   True,
    }

    # 仅为已知的 Ollama/LM Studio 端口传递 num_ctx，避免匹配其他本地服务
    _is_local_ollama = "11434" in base_url
    _is_lmstudio     = "1234" in base_url and ("lmstudio" in base_url or "localhost" in base_url or "127.0.0.1" in base_url)
    if _is_local_ollama or _is_lmstudio:
        prov = detect_provider(model)
        ctx_limit = PROVIDERS.get(prov if prov in ("ollama", "lmstudio") else "ollama", {}).get("context_limit", 128000)
        kwargs["extra_body"] = {"options": {"num_ctx": ctx_limit}}

    if tool_schemas and not config.get("no_tools"):
        kwargs["tools"] = tools_to_openai(tool_schemas)
        # "auto" 需要 vLLM 开启 --enable-auto-tool-choice，服务器不支持则省略
        if not config.get("disable_tool_choice"):
            kwargs["tool_choice"] = "auto"
    if config.get("max_tokens"):
        prov_cap = PROVIDERS.get(detect_provider(model), {}).get("max_completion_tokens")
        mt = config["max_tokens"]
        kwargs["max_tokens"] = min(mt, prov_cap) if prov_cap else mt

    text          = ""
    tool_buf: dict = {}   # 索引 → {id, name, args_str}
    in_tok = out_tok = 0

    stream = client.chat.completions.create(**kwargs)
    for chunk in stream:
        if not chunk.choices:
            # 仅包含用量的片段（部分厂商最后发送）
            if hasattr(chunk, "usage") and chunk.usage:
                in_tok  = chunk.usage.prompt_tokens
                out_tok = chunk.usage.completion_tokens
            continue

        choice = chunk.choices[0]
        delta  = choice.delta

        if delta.content:
            text += delta.content
            yield TextChunk(delta.content)

        if delta.tool_calls:
            for tc in delta.tool_calls:
                idx = tc.index
                if idx not in tool_buf:
                    tool_buf[idx] = {"id": "", "name": "", "args": "", "extra_content": None}
                if tc.id:
                    tool_buf[idx]["id"] = tc.id
                if tc.function:
                    if tc.function.name:
                        tool_buf[idx]["name"] += tc.function.name
                    if tc.function.arguments:
                        tool_buf[idx]["args"] += tc.function.arguments
                # 捕获额外内容（例如 Gemini thought_signature）
                extra = getattr(tc, "extra_content", None)
                if extra:
                    tool_buf[idx]["extra_content"] = extra

        # 部分厂商在最后一个片段中包含用量信息
        if hasattr(chunk, "usage") and chunk.usage:
            in_tok  = chunk.usage.prompt_tokens  or in_tok
            out_tok = chunk.usage.completion_tokens or out_tok

    tool_calls = []
    for idx in sorted(tool_buf):
        v = tool_buf[idx]
        try:
            inp = json.loads(v["args"]) if v["args"] else {}
        except json.JSONDecodeError:
            inp = {"_raw": v["args"]}
        tc_entry = {"id": v["id"] or f"call_{idx}", "name": v["name"], "input": inp}
        if v.get("extra_content"):
            tc_entry["extra_content"] = v["extra_content"]
        tool_calls.append(tc_entry)

    yield Response(text, tool_calls, in_tok, out_tok)


def stream_ollama(
    base_url: str,
    model: str,
    system: str,
    messages: list,
    tool_schemas: list,
    config: dict,
) -> Generator:
    # pass_images=True：Ollama /api/chat 原生支持消息中的 base64 图片
    oai_messages = [{"role": "system", "content": system}] + messages_to_openai(messages, ollama_native_images=True)
    
    # Ollama 要求工具参数为字典，而非字符串；OpenAI 使用字符串
    for m in oai_messages:
        if m.get("content") is None:
            m["content"] = ""
        if "tool_calls" in m and m["tool_calls"]:
            for tc in m["tool_calls"]:
                fn = tc.get("function", {})
                if isinstance(fn.get("arguments"), str):
                    try:
                        fn["arguments"] = json.loads(fn["arguments"])
                    except Exception:
                        pass
    
    payload = {
        "model": model,
        "messages": oai_messages,
        "stream": True,
        "options": {
            "num_ctx": config.get("context_limit", 128000)
        }
    }
    
    if tool_schemas and not config.get("no_tools"):
        payload["tools"] = tools_to_openai(tool_schemas)

    def _make_request(p):
        return urllib.request.Request(
            f"{base_url.rstrip('/')}/api/chat",
            data=json.dumps(p).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

    req = _make_request(payload)

    text = ""
    tool_buf: dict = {}

    try:
        resp_cm = urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        if e.code == 500 and "tools" in payload:
            # 模型不支持工具调用 → 不带工具重试
            print(
                f"\n\033[33m[警告] {model} 返回 HTTP 500（可能不支持工具调用）。"
                " 正在不带工具重试。\033[0m"
            )
            payload.pop("tools", None)
            req = _make_request(payload)
            resp_cm = urllib.request.urlopen(req)
        else:
            raise

    with resp_cm as resp:
        for line in resp:
            if not line.strip(): continue
            try:
                data = json.loads(line)
            except Exception:
                continue
            
            msg = data.get("message", {})
            
            # Ollama 原生推理模型会在这里流式输出思考过程
            if "thinking" in msg and msg["thinking"]:
                yield ThinkingChunk(msg["thinking"])
                
            if "content" in msg and msg["content"]:
                text += msg["content"]
                yield TextChunk(msg["content"])
            
            # 处理原生 Ollama 工具格式（与 OpenAI 一致）
            for tc in msg.get("tool_calls", []):
                fn = tc.get("function", {})
                idx = len(tool_buf) # Ollama 发送完整工具调用，而非增量
                tool_buf[idx] = {
                    "id": "call_ollama" + str(idx),
                    "name": fn.get("name", ""),
                    "args": json.dumps(fn.get("arguments", {})),
                    "input": fn.get("arguments", {})
                }

    tool_calls = []
    for idx in sorted(tool_buf):
        v = tool_buf[idx]
        tool_calls.append({"id": v["id"], "name": v["name"], "input": v["input"]})

    # Ollama 直播流不易直接返回精确 token 数，直到 "done"，
    # 但可以粗略估算或返回 0，pycc 能优雅处理 0
    yield Response(text, tool_calls, 0, 0)


def stream(
    model: str,
    system: str,
    messages: list,
    tool_schemas: list,
    config: dict,
) -> Generator:
    """
    统一流式调用入口。
    从模型字符串自动识别厂商。
    抛出：TextChunk | ThinkingChunk | Response
    """
    provider_name = detect_provider(model)
    model_name    = bare_model(model)
    prov          = PROVIDERS.get(provider_name, PROVIDERS["openai"])
    api_key       = get_api_key(provider_name, config)

    if prov["type"] == "anthropic":
        yield from stream_anthropic(api_key, model_name, system, messages, tool_schemas, config)
    elif prov["type"] == "ollama":
        base_url = prov.get("base_url", "http://localhost:11434")
        yield from stream_ollama(base_url, model_name, system, messages, tool_schemas, config)
    else:
        import os as _os
        if provider_name == "custom":
            base_url = (config.get("custom_base_url")
                        or _os.environ.get("CUSTOM_BASE_URL", ""))
            if not base_url:
                raise ValueError(
                    "custom 厂商需要设置 base_url。"
                    " 设置 CUSTOM_BASE_URL 环境变量或执行：/config custom_base_url=http://..."
                )
        else:
            base_url = prov.get("base_url", "https://api.openai.com/v1")
        yield from stream_openai_compat(
            api_key, base_url, model_name, system, messages, tool_schemas, config
        )


def list_ollama_models(base_url: str) -> list[str]:
    """从 Ollama 服务器获取本地可用模型列表。"""
    try:
        url = f"{base_url.rstrip('/')}/api/tags"
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            # Ollama 返回格式：{"models": [{"name": "llama3:latest", ...}, ...]}
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []