# pycc

**pycc** is a lightweight, hackable Python implementation of an AI coding assistant, inspired by Claude Code. It runs a streaming agent loop with tool use, supports 10+ model providers out of the box, and exposes a clean REPL you can extend with custom skills and MCP servers.

```bash
pip install anthropic          # or openai, or any supported provider SDK
export ANTHROPIC_API_KEY=...
python pycc.py                 # start the REPL
```

Requires Python ≥ 3.10.

---

## Features

| Feature | Details |
|---|---|
| Multi-provider | Anthropic · OpenAI · Gemini · Kimi · Qwen · Zhipu · DeepSeek · MiniMax · Ollama · LM Studio · Custom endpoint |
| Interactive REPL | readline history, Tab-complete slash commands with descriptions + subcommand hints; Bracketed Paste Mode for reliable multi-line paste |
| Agent loop | Streaming API + automatic tool-use loop |
| 27 built-in tools | Read · Write · Edit · Bash · Glob · Grep · WebFetch · WebSearch · **NotebookEdit** · **GetDiagnostics** · MemorySave · MemoryDelete · MemorySearch · MemoryList · Agent · SendMessage · CheckAgentResult · ListAgentTasks · ListAgentTypes · Skill · SkillList · AskUserQuestion · TaskCreate/Update/Get/List · **SleepTimer** · **EnterPlanMode** · **ExitPlanMode** · *(MCP tools auto-added at startup)* |
| MCP integration | Connect any MCP server (stdio/SSE/HTTP), tools auto-registered and callable by Claude |
| AskUserQuestion | Claude can pause and ask the user a clarifying question mid-task, with optional numbered choices |
| Task management | TaskCreate/Update/Get/List tools; sequential IDs; metadata; persisted to `.pycc/tasks.json`; `/tasks` REPL command |
| Diff view | Git-style red/green diff display for Edit and Write |
| Context compression | Auto-compact long conversations to stay within model limits |
| Persistent memory | Dual-scope memory (user + project) with 4 types, confidence/source metadata, conflict detection, recency-weighted search, `last_used_at` tracking, and `/memory consolidate` for auto-extraction |
| Multi-agent | Spawn typed sub-agents (coder/reviewer/researcher/…), git worktree isolation, background mode |
| Skills | Built-in `/commit` · `/review` + custom markdown skills with argument substitution and fork/inline execution |
| Permission system | `auto` / `accept-all` / `manual` / `plan` modes |
| Plan mode | `/plan <desc>` enters read-only analysis mode; Claude writes only to the plan file; `EnterPlanMode` / `ExitPlanMode` agent tools for autonomous planning |
| Vision input | `/image` (or `/img`) captures the clipboard image and sends it to any vision-capable model — Ollama (`llava`, `gemma4`, `llama3.2-vision`) via native format, or cloud models (GPT-4o, Gemini 2.0 Flash, …) via OpenAI `image_url` multipart format. Requires `pip install pycc[vision]`; Linux also needs `xclip`. |
| Force quit | 3× Ctrl+C within 2 seconds triggers `os._exit(1)` — kills the process immediately regardless of blocking I/O |
| Rich Live streaming | When `rich` is installed, responses render as live-updating Markdown in place. Auto-disabled in SSH sessions to prevent repeated output; override with `/config rich_live=false`. |
| Context injection | Auto-loads `CLAUDE.md`, git status, cwd, persistent memory |
| Session persistence | Autosave on exit to `daily/YYYY-MM-DD/` (per-day limit) + `history.json` (master, all sessions) + `session_latest.json` (/resume); sessions include `session_id` and `saved_at` metadata; `/load` grouped by date |
| Extended Thinking | Toggle on/off for Claude models; native `<think>` block streaming for local Ollama reasoning models (deepseek-r1, qwen3, gemma4) |
| Cost tracking | Token usage + estimated USD cost |
| Non-interactive mode | `--print` flag for scripting / CI |

---

## Supported Models

### Closed-Source (API)

| Provider | Model | Context | Strengths | API Key Env |
|---|---|---|---|---|
| **Anthropic** | `claude-opus-4-6` | 200k | Most capable, best for complex reasoning | `ANTHROPIC_API_KEY` |
| **Anthropic** | `claude-sonnet-4-6` | 200k | Balanced speed & quality | `ANTHROPIC_API_KEY` |
| **Anthropic** | `claude-haiku-4-5-20251001` | 200k | Fast, cost-efficient | `ANTHROPIC_API_KEY` |
| **OpenAI** | `gpt-4o` | 128k | Strong multimodal & coding | `OPENAI_API_KEY` |
| **OpenAI** | `gpt-4o-mini` | 128k | Fast, cheap | `OPENAI_API_KEY` |
| **OpenAI** | `o3-mini` | 200k | Strong reasoning | `OPENAI_API_KEY` |
| **OpenAI** | `o1` | 200k | Advanced reasoning | `OPENAI_API_KEY` |
| **Google** | `gemini-2.5-pro-preview-03-25` | 1M | Long context, multimodal | `GEMINI_API_KEY` |
| **Google** | `gemini-2.0-flash` | 1M | Fast, large context | `GEMINI_API_KEY` |
| **Google** | `gemini-1.5-pro` | 2M | Largest context window | `GEMINI_API_KEY` |
| **Moonshot (Kimi)** | `moonshot-v1-8k` | 8k | Chinese & English | `MOONSHOT_API_KEY` |
| **Moonshot (Kimi)** | `moonshot-v1-32k` | 32k | Chinese & English | `MOONSHOT_API_KEY` |
| **Moonshot (Kimi)** | `moonshot-v1-128k` | 128k | Long context | `MOONSHOT_API_KEY` |
| **Alibaba (Qwen)** | `qwen-max` | 32k | Best Qwen quality | `DASHSCOPE_API_KEY` |
| **Alibaba (Qwen)** | `qwen-plus` | 128k | Balanced | `DASHSCOPE_API_KEY` |
| **Alibaba (Qwen)** | `qwen-turbo` | 1M | Fast, cheap | `DASHSCOPE_API_KEY` |
| **Alibaba (Qwen)** | `qwq-32b` | 32k | Strong reasoning | `DASHSCOPE_API_KEY` |
| **Zhipu (GLM)** | `glm-4-plus` | 128k | Best GLM quality | `ZHIPU_API_KEY` |
| **Zhipu (GLM)** | `glm-4` | 128k | General purpose | `ZHIPU_API_KEY` |
| **Zhipu (GLM)** | `glm-4-flash` | 128k | Free tier available | `ZHIPU_API_KEY` |
| **DeepSeek** | `deepseek-chat` | 64k | Strong coding | `DEEPSEEK_API_KEY` |
| **DeepSeek** | `deepseek-reasoner` | 64k | Chain-of-thought reasoning | `DEEPSEEK_API_KEY` |
| **MiniMax** | `MiniMax-Text-01` | 1M | Long context, strong reasoning | `MINIMAX_API_KEY` |
| **MiniMax** | `MiniMax-VL-01` | 1M | Vision + language | `MINIMAX_API_KEY` |
| **MiniMax** | `abab6.5s-chat` | 256k | Fast, cost-efficient | `MINIMAX_API_KEY` |
| **MiniMax** | `abab6.5-chat` | 256k | Balanced quality | `MINIMAX_API_KEY` |

### Open-Source (Local via Ollama)

| Model | Size | Strengths | Pull Command |
|---|---|---|---|
| `llama3.3` | 70B | General purpose, strong reasoning | `ollama pull llama3.3` |
| `llama3.2` | 3B / 11B | Lightweight | `ollama pull llama3.2` |
| `qwen2.5-coder` | 7B / 32B | **Best for coding tasks** | `ollama pull qwen2.5-coder` |
| `qwen2.5` | 7B / 72B | Chinese & English | `ollama pull qwen2.5` |
| `deepseek-r1` | 7B–70B | Reasoning, math | `ollama pull deepseek-r1` |
| `deepseek-coder-v2` | 16B | Coding | `ollama pull deepseek-coder-v2` |
| `mistral` | 7B | Fast, efficient | `ollama pull mistral` |
| `mixtral` | 8x7B | Strong MoE model | `ollama pull mixtral` |
| `phi4` | 14B | Microsoft, strong reasoning | `ollama pull phi4` |
| `gemma3` | 4B / 12B / 27B | Google open model | `ollama pull gemma3` |
| `codellama` | 7B / 34B | Code generation | `ollama pull codellama` |
| `llava` | 7B / 13B | **Vision** — image understanding | `ollama pull llava` |
| `llama3.2-vision` | 11B | **Vision** — multimodal reasoning | `ollama pull llama3.2-vision` |

> **Note:** Tool calling requires a model that supports function calling. Recommended local models: `qwen2.5-coder`, `llama3.3`, `mistral`, `phi4`.

> **Reasoning models:** `deepseek-r1`, `qwen3`, and `gemma4` stream native `<think>` blocks. Enable with `/verbose` and `/thinking` to see thoughts in the terminal. Note: models fed a large system prompt (like pycc's 25 tool schemas) may suppress their thinking phase to avoid breaking the expected JSON format — this is model behavior, not a bug.

---

## Installation

### Recommended: install as a global command with `uv`

[uv](https://docs.astral.sh/uv/) installs `pycc` into an isolated environment and puts it on your PATH so you can run it from anywhere:

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone https://github.com/SafeRL-Lab/clawspring
cd pycc
uv tool install .
```

After that, `pycc` is available as a global command:

```bash
pycc                        # start REPL
pycc --model gpt-4o         # choose a model
pycc -p "explain this"      # non-interactive
```

To update after pulling new code:

```bash
uv tool install . --reinstall
```

To uninstall:

```bash
uv tool uninstall pycc
```

### Alternative: run directly from the repo

```bash
git clone https://github.com/SafeRL-Lab/clawspring
cd pycc

pip install -r requirements.txt
# or manually:
pip install anthropic openai httpx rich

python pycc.py
```

---

## Usage: Closed-Source API Models

### Anthropic Claude

Get your API key at [console.anthropic.com](https://console.anthropic.com).

```bash
export ANTHROPIC_API_KEY=sk-ant-api03-...

# Default model (claude-opus-4-6)
pycc

# Choose a specific model
pycc --model claude-sonnet-4-6
pycc --model claude-haiku-4-5-20251001

# Enable Extended Thinking
pycc --model claude-opus-4-6 --thinking --verbose
```

### OpenAI GPT

Get your API key at [platform.openai.com](https://platform.openai.com).

```bash
export OPENAI_API_KEY=sk-...

pycc --model gpt-4o
pycc --model gpt-4o-mini
pycc --model gpt-4.1-mini
pycc --model o3-mini
```

### Google Gemini

Get your API key at [aistudio.google.com](https://aistudio.google.com).

```bash
export GEMINI_API_KEY=AIza...

pycc --model gemini/gemini-2.0-flash
pycc --model gemini/gemini-1.5-pro
pycc --model gemini/gemini-2.5-pro-preview-03-25
```

### Kimi (Moonshot AI)

Get your API key at [platform.moonshot.cn](https://platform.moonshot.cn).

```bash
export MOONSHOT_API_KEY=sk-...

pycc --model kimi/moonshot-v1-32k
pycc --model kimi/moonshot-v1-128k
```

### Qwen (Alibaba DashScope)

Get your API key at [dashscope.aliyun.com](https://dashscope.aliyun.com).

```bash
export DASHSCOPE_API_KEY=sk-...

pycc --model qwen/Qwen3.5-Plus
pycc --model qwen/Qwen3-MAX
pycc --model qwen/Qwen3.5-Flash
```

### Zhipu GLM

Get your API key at [open.bigmodel.cn](https://open.bigmodel.cn).

```bash
export ZHIPU_API_KEY=...

pycc --model zhipu/glm-4-plus
pycc --model zhipu/glm-4-flash   # free tier
```

### DeepSeek

Get your API key at [platform.deepseek.com](https://platform.deepseek.com).

```bash
export DEEPSEEK_API_KEY=sk-...

pycc --model deepseek/deepseek-chat
pycc --model deepseek/deepseek-reasoner
```

### MiniMax

Get your API key at [platform.minimaxi.chat](https://platform.minimaxi.chat).

```bash
export MINIMAX_API_KEY=...

pycc --model minimax/MiniMax-Text-01
pycc --model minimax/MiniMax-VL-01
pycc --model minimax/abab6.5s-chat
```

---

## Usage: Open-Source Models (Local)

### Option A — Ollama (Recommended)

Ollama runs models locally with zero configuration. No API key required.

**Step 1: Install Ollama**

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# Or download from https://ollama.com/download
```

**Step 2: Pull a model**

```bash
# Best for coding (recommended)
ollama pull qwen2.5-coder          # 4.7 GB (7B)
ollama pull qwen2.5-coder:32b      # 19 GB (32B)

# General purpose
ollama pull llama3.3               # 42 GB (70B)
ollama pull llama3.2               # 2.0 GB (3B)

# Reasoning
ollama pull deepseek-r1            # 4.7 GB (7B)
ollama pull deepseek-r1:32b        # 19 GB (32B)

# Other
ollama pull phi4                   # 9.1 GB (14B)
ollama pull mistral                # 4.1 GB (7B)
```

**Step 3: Start Ollama server** (runs automatically on macOS; on Linux run manually)

```bash
ollama serve     # starts on http://localhost:11434
```

**Step 4: Run pycc**

```bash
pycc --model ollama/qwen2.5-coder
pycc --model ollama/llama3.3
pycc --model ollama/deepseek-r1
```

Or

```bash
python pycc.py --model ollama/qwen2.5-coder
python pycc.py --model ollama/llama3.3
python pycc.py --model ollama/deepseek-r1
python pycc.py --model ollama/qwen3.5:35b
```

**List your locally available models:**

```bash
ollama list
```

Then use any model from the list:

```bash
pycc --model ollama/<model-name>
```

---

### Option B — LM Studio

LM Studio provides a GUI to download and run models, with a built-in OpenAI-compatible server.

**Step 1:** Download [LM Studio](https://lmstudio.ai) and install it.

**Step 2:** Search and download a model inside LM Studio (GGUF format).

**Step 3:** Go to **Local Server** tab → click **Start Server** (default port: 1234).

**Step 4:**

```bash
pycc --model lmstudio/<model-name>
# e.g.:
pycc --model lmstudio/phi-4-GGUF
pycc --model lmstudio/qwen2.5-coder-7b
```

The model name should match what LM Studio shows in the server status bar.

---

### Option C — vLLM / Self-Hosted OpenAI-Compatible Server

For self-hosted inference servers (vLLM, TGI, llama.cpp server, etc.) that expose an OpenAI-compatible API:

Quick Start for option C:
Step 1: Start vllm:
 ```
CUDA_VISIBLE_DEVICES=7 python -m vllm.entrypoints.openai.api_server \
      --model Qwen/Qwen2.5-Coder-7B-Instruct \
      --host 0.0.0.0 \
      --port 8000 \
      --enable-auto-tool-choice \
      --tool-call-parser hermes
```


 Step 2: Start pycc：
```
  export CUSTOM_BASE_URL=http://localhost:8000/v1
  export CUSTOM_API_KEY=none
  pycc --model custom/Qwen/Qwen2.5-Coder-7B-Instruct
```


```bash
# Example: vLLM serving Qwen2.5-Coder-32B
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-Coder-32B-Instruct \
    --port 8000

# Then run pycc pointing to your server:
pycc
```

Inside the REPL:

```
/config custom_base_url=http://localhost:8000/v1
/config custom_api_key=token-abc123    # skip if no auth
/model custom/Qwen2.5-Coder-32B-Instruct
```

Or set via environment:

```bash
export CUSTOM_BASE_URL=http://localhost:8000/v1
export CUSTOM_API_KEY=token-abc123

pycc --model custom/Qwen2.5-Coder-32B-Instruct
```

For a remote GPU server:

```bash
/config custom_base_url=http://192.168.1.100:8000/v1
/model custom/your-model-name
```

---

## Model Name Format

Three equivalent formats are supported:

```bash
# 1. Auto-detect by prefix (works for well-known models)
pycc --model gpt-4o
pycc --model gemini-2.0-flash
pycc --model deepseek-chat

# 2. Explicit provider prefix with slash
pycc --model ollama/qwen2.5-coder
pycc --model kimi/moonshot-v1-128k

# 3. Explicit provider prefix with colon (also works)
pycc --model kimi:moonshot-v1-32k
pycc --model qwen:qwen-max
```

**Auto-detection rules:**

| Model prefix | Detected provider |
|---|---|
| `claude-` | anthropic |
| `gpt-`, `o1`, `o3` | openai |
| `gemini-` | gemini |
| `moonshot-`, `kimi-` | kimi |
| `qwen`, `qwq-` | qwen |
| `glm-` | zhipu |
| `deepseek-` | deepseek |
| `MiniMax-`, `minimax-`, `abab` | minimax |
| `llama`, `mistral`, `phi`, `gemma`, `mixtral`, `codellama` | ollama |

---

## CLI Reference

```
pycc [OPTIONS] [PROMPT]
# or: python pycc.py [OPTIONS] [PROMPT]

Options:
  -p, --print          Non-interactive: run prompt and exit
  -m, --model MODEL    Override model (e.g. gpt-4o, ollama/llama3.3)
  --accept-all         Auto-approve all operations (no permission prompts)
  --verbose            Show thinking blocks and per-turn token counts
  --thinking           Enable Extended Thinking (Claude only)
  --version            Print version and exit
  -h, --help           Show help
```

**Examples:**

```bash
# Interactive REPL with default model
pycc

# Switch model at startup
pycc --model gpt-4o
pycc -m ollama/deepseek-r1:32b

# Non-interactive / scripting
pycc --print "Write a Python fibonacci function"
pycc -p "Explain the Rust borrow checker in 3 sentences" -m gemini/gemini-2.0-flash

# CI / automation (no permission prompts)
pycc --accept-all --print "Initialize a Python project with pyproject.toml"

# Debug mode (see tokens + thinking)
pycc --thinking --verbose
```

---

## Slash Commands (REPL)

Type `/` and press **Tab** to see all commands with descriptions. Continue typing to filter, then Tab again to auto-complete. After a command name, press **Tab** again to see its subcommands (e.g. `/mcp ` → `reload`, `add`, `remove`, …).

| Command | Description |
|---|---|
| `/help` | Show all commands |
| `/clear` | Clear conversation history |
| `/model` | Show current model + list all available models |
| `/model <name>` | Switch model (takes effect immediately) |
| `/config` | Show all current config values |
| `/config key=value` | Set a config value (persisted to disk) |
| `/save` | Save session (auto-named by timestamp) |
| `/save <filename>` | Save session to named file |
| `/load` | Interactive list grouped by date; enter number, `1,2,3` to merge, or `H` for full history |
| `/load <filename>` | Load a saved session by filename |
| `/resume` | Restore the last auto-saved session (`mr_sessions/session_latest.json`) |
| `/resume <filename>` | Load a specific file from `mr_sessions/` (or absolute path) |
| `/history` | Print full conversation history |
| `/context` | Show message count and token estimate |
| `/cost` | Show token usage and estimated USD cost |
| `/verbose` | Toggle verbose mode (tokens + thinking) |
| `/thinking` | Toggle Extended Thinking (Claude only) |
| `/permissions` | Show current permission mode |
| `/permissions <mode>` | Set permission mode: `auto` / `accept-all` / `manual` |
| `/cwd` | Show current working directory |
| `/cwd <path>` | Change working directory |
| `/memory` | List all persistent memories |
| `/memory <query>` | Search memories by keyword (ranked by confidence × recency) |
| `/memory consolidate` | AI-extract up to 3 long-term insights from the current session |
| `/skills` | List available skills |
| `/agents` | Show sub-agent task status |
| `/mcp` | List configured MCP servers and their tools |
| `/mcp reload` | Reconnect all MCP servers and refresh tools |
| `/mcp reload <name>` | Reconnect a single MCP server |
| `/mcp add <name> <cmd> [args]` | Add a stdio MCP server to user config |
| `/mcp remove <name>` | Remove a server from user config |
| `/image [prompt]` | Capture clipboard image and send to vision model with optional prompt |
| `/img [prompt]` | Alias for `/image` |
| `/plan <description>` | Enter plan mode: read-only analysis, writes only to the plan file |
| `/plan` | Show current plan file contents |
| `/plan done` | Exit plan mode and restore original permissions |
| `/plan status` | Show whether plan mode is active |
| `/compact` | Manually compact the conversation (same as auto-compact but user-triggered) |
| `/compact <focus>` | Compact with focus instructions (e.g. `/compact keep the auth refactor context`) |
| `/init` | Create a `CLAUDE.md` template in the current working directory |
| `/export` | Export the conversation as a Markdown file to `.nano_claude/exports/` |
| `/export <filename>` | Export as Markdown or JSON (detected by `.json` extension) |
| `/copy` | Copy the last assistant response to the clipboard |
| `/status` | Show version, model, provider, permissions, session ID, token usage, and context % |
| `/doctor` | Diagnose installation health: Python, git, API key, optional deps, CLAUDE.md |
| `/exit` / `/quit` | Exit |

**Switching models inside a session:**

```
[myproject] ❯ /model
  Current model: claude-opus-4-6  (provider: anthropic)

  Available models by provider:
    anthropic     claude-opus-4-6, claude-sonnet-4-6, ...
    openai        gpt-4o, gpt-4o-mini, o3-mini, ...
    ollama        llama3.3, llama3.2, phi4, mistral, ...
    ...

[myproject] ❯ /model gpt-4o
  Model set to gpt-4o  (provider: openai)

[myproject] ❯ /model ollama/qwen2.5-coder
  Model set to ollama/qwen2.5-coder  (provider: ollama)
```

---

## Configuring API Keys

### Method 1: Environment Variables (recommended)

```bash
# Add to ~/.bashrc or ~/.zshrc
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
export GEMINI_API_KEY=AIza...
export MOONSHOT_API_KEY=sk-...       # Kimi
export DASHSCOPE_API_KEY=sk-...      # Qwen
export ZHIPU_API_KEY=...             # Zhipu GLM
export DEEPSEEK_API_KEY=sk-...       # DeepSeek
export MINIMAX_API_KEY=...           # MiniMax
```

### Method 2: Set Inside the REPL (persisted)

```
/config anthropic_api_key=sk-ant-...
/config openai_api_key=sk-...
/config gemini_api_key=AIza...
/config kimi_api_key=sk-...
/config qwen_api_key=sk-...
/config zhipu_api_key=...
/config deepseek_api_key=sk-...
/config minimax_api_key=...
```

Keys are saved to `~/.pycc/config.json` and loaded automatically on next launch.

### Method 3: Edit the Config File Directly

```json
// ~/.pycc/config.json
{
  "model": "qwen/qwen-max",
  "max_tokens": 8192,
  "permission_mode": "auto",
  "verbose": false,
  "thinking": false,
  "qwen_api_key": "sk-...",
  "kimi_api_key": "sk-...",
  "deepseek_api_key": "sk-...",
  "minimax_api_key": "..."
}
```

---

## Permission System

| Mode | Behavior |
|---|---|
| `auto` (default) | Read-only operations always allowed. Prompts before Bash commands and file writes. |
| `accept-all` | Never prompts. All operations proceed automatically. |
| `manual` | Prompts before every single operation, including reads. |
| `plan` | Read-only analysis mode. Only the plan file (`.nano_claude/plans/`) is writable. Entered via `/plan <desc>` or the `EnterPlanMode` tool. |

**When prompted:**

```
  Allow: Run: git commit -am "fix bug"  [y/N/a(ccept-all)]
```

- `y` — approve this one action
- `n` or Enter — deny
- `a` — approve and switch to `accept-all` for the rest of the session

**Commands always auto-approved in `auto` mode:**
`ls`, `cat`, `head`, `tail`, `wc`, `pwd`, `echo`, `git status`, `git log`, `git diff`, `git show`, `find`, `grep`, `rg`, `python`, `node`, `pip show`, `npm list`, and other read-only shell commands.

---

## Built-in Tools

### Core Tools

| Tool | Description | Key Parameters |
|---|---|---|
| `Read` | Read file with line numbers | `file_path`, `limit`, `offset` |
| `Write` | Create or overwrite file (shows diff) | `file_path`, `content` |
| `Edit` | Exact string replacement (shows diff) | `file_path`, `old_string`, `new_string`, `replace_all` |
| `Bash` | Execute shell command | `command`, `timeout` (default 30s) |
| `Glob` | Find files by glob pattern | `pattern` (e.g. `**/*.py`), `path` |
| `Grep` | Regex search in files (uses ripgrep if available) | `pattern`, `path`, `glob`, `output_mode` |
| `WebFetch` | Fetch and extract text from URL | `url`, `prompt` |
| `WebSearch` | Search the web via DuckDuckGo | `query` |

### Notebook & Diagnostics Tools

| Tool | Description | Key Parameters |
|---|---|---|
| `NotebookEdit` | Edit a Jupyter notebook (`.ipynb`) cell | `notebook_path`, `new_source`, `cell_id`, `cell_type`, `edit_mode` (`replace`/`insert`/`delete`) |
| `GetDiagnostics` | Get LSP-style diagnostics for a source file (pyright/mypy/flake8 for Python; tsc/eslint for JS/TS; shellcheck for shell) | `file_path`, `language` (optional override) |

### Memory Tools

| Tool | Description | Key Parameters |
|---|---|---|
| `MemorySave` | Save or update a persistent memory | `name`, `type`, `description`, `content`, `scope` |
| `MemoryDelete` | Delete a memory by name | `name`, `scope` |
| `MemorySearch` | Search memories by keyword (or AI ranking) | `query`, `scope`, `use_ai`, `max_results` |
| `MemoryList` | List all memories with age and metadata | `scope` |

### Sub-Agent Tools

| Tool | Description | Key Parameters |
|---|---|---|
| `Agent` | Spawn a sub-agent for a task | `prompt`, `subagent_type`, `isolation`, `name`, `model`, `wait` |
| `SendMessage` | Send a message to a named background agent | `name`, `message` |
| `CheckAgentResult` | Check status/result of a background agent | `task_id` |
| `ListAgentTasks` | List all active and finished agent tasks | — |
| `ListAgentTypes` | List available agent type definitions | — |

### Background & Autonomy Tools

| Tool | Description | Key Parameters |
|---|---|---|
| `SleepTimer` | Schedule a silent background timer; injects an automated wake-up prompt when it fires so the agent can resume monitoring or deferred tasks | `seconds` |

### Skill Tools

| Tool | Description | Key Parameters |
|---|---|---|
| `Skill` | Invoke a skill by name from within the conversation | `name`, `args` |
| `SkillList` | List all available skills with triggers and metadata | — |

### MCP Tools

MCP tools are discovered automatically from configured servers and registered under the name `mcp__<server>__<tool>`. Claude can use them exactly like built-in tools.

| Example tool name | Where it comes from |
|---|---|
| `mcp__git__git_status` | `git` server, `git_status` tool |
| `mcp__filesystem__read_file` | `filesystem` server, `read_file` tool |
| `mcp__myserver__my_action` | custom server you configured |

> **Adding custom tools:** See [Architecture Guide](docs/architecture.md#tool-registry) for how to register your own tools.

---

## Memory

The model can remember things across conversations using the built-in memory system.

### Storage

Memories are stored as individual markdown files in two scopes:

| Scope | Path | Visibility |
|---|---|---|
| **User** (default) | `~/.pycc/memory/` | Shared across all projects |
| **Project** | `.pycc/memory/` in cwd | Local to the current repo |

A `MEMORY.md` index (≤ 200 lines / 25 KB) is auto-rebuilt on every save or delete and injected into the system prompt so the model always has an overview of what's been remembered.

### Memory types

| Type | Use for |
|---|---|
| `user` | Your role, preferences, background |
| `feedback` | How you want the model to behave (corrections AND confirmations) |
| `project` | Ongoing work, deadlines, decisions not in git history |
| `reference` | Links to external systems (Linear, Grafana, Slack, etc.) |

### Memory file format

Each memory is a markdown file with YAML frontmatter:

```markdown
---
name: coding_style
description: Python formatting preferences
type: feedback
created: 2026-04-02
confidence: 0.95
source: user
last_used_at: 2026-04-05
conflict_group: coding_style
---
Prefer 4-space indentation and full type hints in all Python code.
**Why:** user explicitly stated this preference.
**How to apply:** apply to every Python file written or edited.
```

**Metadata fields** (new — auto-managed):

| Field | Default | Description |
|---|---|---|
| `confidence` | `1.0` | Reliability score 0–1. Explicit user statements = 1.0; inferred preferences ≈ 0.8; auto-consolidated ≈ 0.8 |
| `source` | `user` | Origin: `user` / `model` / `tool` / `consolidator` |
| `last_used_at` | — | Updated automatically each time this memory is returned by MemorySearch |
| `conflict_group` | — | Groups related memories (e.g. `writing_style`) for conflict tracking |

### Conflict detection

When `MemorySave` is called with a name that already exists but different content, the system reports the conflict before overwriting:

```
Memory saved: 'writing_style' [feedback/user]
⚠ Replaced conflicting memory (was user-sourced, 100% confidence, written 2026-04-01).
  Old content: Prefer formal, academic style...
```

### Ranked retrieval

`MemorySearch` ranks results by **confidence × recency** (30-day exponential decay) rather than plain keyword order. Memories that haven't been used recently fade in priority. Each search hit also updates `last_used_at` so frequently-accessed memories stay prominent.

```
You: /memory python
  [feedback/user] coding_style [conf:95% src:user]
    Python formatting preferences
    Prefer 4-space indentation and full type hints...
```

### `/memory consolidate` — auto-extract long-term insights

After a meaningful session, run:

```
[myproject] ❯ /memory consolidate
  Analyzing session for long-term memories…
  ✓ Consolidated 2 memory/memories: user_prefers_direct_answers, avoid_trailing_summaries
```

The command sends a condensed session transcript to the model and asks it to identify up to **3** insights worth keeping long-term (user preferences, feedback corrections, project decisions). Extracted memories are saved with `confidence: 0.80` and `source: consolidator` — they **never overwrite** an existing memory that already has higher confidence.

Good times to run `/memory consolidate`:
- After correcting the model's behavior several times in a row
- After a session where you shared project background or decisions
- After completing a task with clear planning choices

### Example interaction

```
You: Remember that I prefer 4-space indentation and type hints.
AI: [calls MemorySave] Memory saved: 'coding_style' [feedback/user]

You: /memory
  1 memory/memories:
  [feedback  |user   ] coding_style.md
    Python formatting preferences

You: /memory python
  Found 1 relevant memory for 'python':
  [feedback/user] coding_style
    Prefer 4-space indentation and full type hints in all Python code.

You: /memory consolidate
  ✓ Consolidated 1 memory: user_prefers_verbose_commit_messages
```

**Staleness warnings:** Memories older than 1 day show a `⚠ stale` caveat — claims about file:line citations or code state may be outdated; verify before acting.

**AI-ranked search:** `MemorySearch(query="...", use_ai=true)` uses the model to rank candidates by relevance before applying the confidence × recency re-ranking.

---

## Skills

Skills are reusable prompt templates that give the model specialized capabilities. Two built-in skills ship out of the box — no setup required.

**Built-in skills:**

| Trigger | Description |
|---|---|
| `/commit` | Review staged changes and create a well-structured git commit |
| `/review [PR]` | Review code or PR diff with structured feedback |

**Quick start — custom skill:**

```bash
mkdir -p ~/.pycc/skills
```

Create `~/.pycc/skills/deploy.md`:

```markdown
---
name: deploy
description: Deploy to an environment
triggers: [/deploy]
allowed-tools: [Bash, Read]
when_to_use: Use when the user wants to deploy a version to an environment.
argument-hint: [env] [version]
arguments: [env, version]
context: inline
---

Deploy $VERSION to the $ENV environment.
Full args: $ARGUMENTS
```

Now use it:

```
You: /deploy staging 2.1.0
AI: [deploys version 2.1.0 to staging]
```

**Argument substitution:**
- `$ARGUMENTS` — the full raw argument string
- `$ARG_NAME` — positional substitution by named argument (first word → first name)
- Missing args become empty strings

**Execution modes:**
- `context: inline` (default) — runs inside current conversation history
- `context: fork` — runs as an isolated sub-agent with fresh history; supports `model` override

**Priority** (highest wins): project-level > user-level > built-in

**List skills:** `/skills` — shows triggers, argument hint, source, and `when_to_use`

**Skill search paths:**

```
./.pycc/skills/     # project-level (overrides user-level)
~/.pycc/skills/     # user-level
```

---

## Sub-Agents

The model can spawn independent sub-agents to handle tasks in parallel.

**Specialized agent types** — built-in:

| Type | Optimized for |
|---|---|
| `general-purpose` | Research, exploration, multi-step tasks |
| `coder` | Writing, reading, and modifying code |
| `reviewer` | Security, correctness, and code quality analysis |
| `researcher` | Web search and documentation lookup |
| `tester` | Writing and running tests |

**Basic usage:**
```
You: Search this codebase for all TODO comments and summarize them.
AI: [calls Agent(prompt="...", subagent_type="researcher")]
    Sub-agent reads files, greps for TODOs...
    Result: Found 12 TODOs across 5 files...
```

**Background mode** — spawn without waiting, collect result later:
```
AI: [calls Agent(prompt="run all tests", name="test-runner", wait=false)]
AI: [continues other work...]
AI: [calls CheckAgentResult / SendMessage to follow up]
```

**Git worktree isolation** — agents work on an isolated branch with no conflicts:
```
Agent(prompt="refactor auth module", isolation="worktree")
```
The worktree is auto-cleaned up if no changes were made; otherwise the branch name is reported.

**Custom agent types** — create `~/.pycc/agents/myagent.md`:
```markdown
---
name: myagent
description: Specialized for X
model: claude-haiku-4-5-20251001
tools: [Read, Grep, Bash]
---
Extra system prompt for this agent type.
```

**List running agents:** `/agents`

Sub-agents have independent conversation history, share the file system, and are limited to 3 levels of nesting.

---

## MCP (Model Context Protocol)

MCP lets you connect any external tool server — local subprocess or remote HTTP — and Claude can use its tools automatically. This is the same protocol Claude Code uses to extend its capabilities.

### Supported transports

| Transport | Config `type` | Description |
|---|---|---|
| **stdio** | `"stdio"` | Spawn a local subprocess (most common) |
| **SSE** | `"sse"` | HTTP Server-Sent Events stream |
| **HTTP** | `"http"` | Streamable HTTP POST (newer servers) |

### Configuration

Place a `.mcp.json` file in your project directory **or** edit `~/.pycc/mcp.json` for user-wide servers.

```json
{
  "mcpServers": {
    "git": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-server-git"]
    },
    "filesystem": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-server-filesystem", "/tmp"]
    },
    "my-remote": {
      "type": "sse",
      "url": "http://localhost:8080/sse",
      "headers": {"Authorization": "Bearer my-token"}
    }
  }
}
```

Config priority: `.mcp.json` (project) overrides `~/.pycc/mcp.json` (user) by server name.

### Quick start

```bash
# Install a popular MCP server
pip install uv        # uv includes uvx
uvx mcp-server-git --help   # verify it works

# Add to user config via REPL
/mcp add git uvx mcp-server-git

# Or create .mcp.json in your project dir, then:
/mcp reload
```

### REPL commands

```
/mcp                          # list servers + their tools + connection status
/mcp reload                   # reconnect all servers, refresh tool list
/mcp reload git               # reconnect a single server
/mcp add myserver uvx mcp-server-x   # add stdio server
/mcp remove myserver          # remove from user config
```

### How Claude uses MCP tools

Once connected, Claude can call MCP tools directly:

```
You: What files changed in the last git commit?
AI: [calls mcp__git__git_diff_staged()]
    → shows diff output from the git MCP server
```

Tool names follow the pattern `mcp__<server_name>__<tool_name>`. All characters
that are not alphanumeric or `_` are automatically replaced with `_`.

### Popular MCP servers

| Server | Install | Provides |
|---|---|---|
| `mcp-server-git` | `uvx mcp-server-git` | git operations (status, diff, log, commit) |
| `mcp-server-filesystem` | `uvx mcp-server-filesystem <path>` | file read/write/list |
| `mcp-server-fetch` | `uvx mcp-server-fetch` | HTTP fetch tool |
| `mcp-server-postgres` | `uvx mcp-server-postgres <conn-str>` | PostgreSQL queries |
| `mcp-server-sqlite` | `uvx mcp-server-sqlite --db-path x.db` | SQLite queries |
| `mcp-server-brave-search` | `uvx mcp-server-brave-search` | Brave web search |

> Browse the full registry at [modelcontextprotocol.io/servers](https://modelcontextprotocol.io/servers)

## AskUserQuestion Tool

Claude can pause mid-task and interactively ask you a question before proceeding.

**Example invocation by Claude:**
```json
{
  "tool": "AskUserQuestion",
  "question": "Which database should I use?",
  "options": [
    {"label": "SQLite", "description": "Simple, file-based"},
    {"label": "PostgreSQL", "description": "Full-featured, requires server"}
  ],
  "allow_freetext": true
}
```

**What you see in the terminal:**
```
❓ Question from assistant:
   Which database should I use?

  [1] SQLite — Simple, file-based
  [2] PostgreSQL — Full-featured, requires server
  [0] Type a custom answer

Your choice (number or text):
```

- Select by number or type free text directly
- Claude receives your answer and continues the task
- 5-minute timeout (returns "(no answer — timeout)" if unanswered)

---

## Task Management

The `task/` package gives Claude (and you) a structured task list for tracking multi-step work within a session.

### Tools available to Claude

| Tool | Parameters | What it does |
|------|-----------|--------------|
| `TaskCreate` | `subject`, `description`, `active_form?`, `metadata?` | Create a task; returns `#id created: subject` |
| `TaskUpdate` | `task_id`, `subject?`, `description?`, `status?`, `owner?`, `metadata?` | Update any field; `status='deleted'` removes the task |
| `TaskGet` | `task_id` | Return full details of one task |
| `TaskList` | _(none)_ | List all tasks with status icons |

**Valid statuses:** `pending` → `in_progress` → `completed` / `cancelled` / `deleted`

### Persistence

Tasks are saved to `.pycc/tasks.json` in the current working directory after every mutation and reloaded on first access.

### REPL commands

```
/tasks                    list all tasks
/tasks create <subject>   quick-create a task
/tasks start <id>         mark in_progress
/tasks done <id>          mark completed
/tasks cancel <id>        mark cancelled
/tasks delete <id>        remove a task
/tasks get <id>           show full details
/tasks clear              delete all tasks
```

### Typical Claude workflow

```
User: implement the login feature

Claude:
  TaskCreate(subject="Design auth schema", description="JWT vs session")  → #1
  TaskCreate(subject="Write login endpoint", description="POST /auth/login") → #2
  TaskCreate(subject="Write tests", description="Unit + integration") → #3

  TaskUpdate(task_id="1", status="in_progress", active_form="Designing schema")
  ... (does the work) ...
  TaskUpdate(task_id="1", status="completed")
  ...
```

## Plan Mode

Plan mode is a structured workflow for tackling complex, multi-file tasks: Claude first analyses the codebase in a read-only phase and writes an explicit plan, then the user approves before implementation begins.

### How it works

In plan mode:
- **Only reads** are permitted (`Read`, `Glob`, `Grep`, `WebFetch`, `WebSearch`, safe `Bash` commands).
- **Writes are blocked** everywhere **except** the dedicated plan file (`.nano_claude/plans/<session_id>.md`).
- Blocked write attempts produce a helpful message rather than prompting the user.
- The system prompt is augmented with plan mode instructions.
- After compaction, the plan file context is automatically restored.

### Slash command workflow

```
[myproject] ❯ /plan add WebSocket support
  Plan mode activated.
  Plan file: .nano_claude/plans/a3f9c1b2.md
  Reads allowed. All other writes blocked (except plan file).

[myproject] ❯ <describe your task>
  [Claude reads files, builds understanding, writes plan to plan file]

[myproject] ❯ /plan
  # Plan: Add WebSocket support

  ## Phase 1: Create ws_handler.py
  ## Phase 2: Modify server.py to mount the handler
  ## Phase 3: Add tests

[myproject] ❯ /plan done
  Plan mode exited. Permission mode restored to: auto
  Review the plan above and start implementing when ready.

[myproject] ❯ /plan status
  Plan mode: INACTIVE  (permission mode: auto)
```

### Agent tool workflow (autonomous)

Claude can autonomously enter and exit plan mode using the `EnterPlanMode` and `ExitPlanMode` tools — both are auto-approved in all permission modes:

```
User: Refactor the authentication module

Claude: [calls EnterPlanMode(task_description="Refactor auth module")]
  → reads auth.py, users.py, tests/test_auth.py ...
  → writes plan to .nano_claude/plans/...
  [calls ExitPlanMode()]
  → "Here is my plan. Please review and approve before I begin."

User: Looks good, go ahead.
Claude: [implements the plan]
```

### Commands

| Command | Description |
|---|---|
| `/plan <description>` | Enter plan mode with a task description |
| `/plan` | Print the current plan file contents |
| `/plan done` | Exit plan mode, restore previous permissions |
| `/plan status` | Show whether plan mode is active |

---

## Context Compression

Long conversations are automatically compressed to stay within the model's context window.

**Two layers:**

1. **Snip** — Old tool outputs (file reads, bash results) are truncated after a few turns. Fast, no API cost.
2. **Auto-compact** — When token usage exceeds 70% of the context limit, older messages are summarized by the model into a concise recap.

This happens transparently. You don't need to do anything.

**Manual compaction** — You can also trigger compaction at any time with `/compact`. An optional focus string tells the summarizer what context to prioritize:

```
[myproject] ❯ /compact
  Compacted: ~12400 → ~3200 tokens (~9200 saved)

[myproject] ❯ /compact keep the WebSocket implementation details
  Compacted: ~11800 → ~3100 tokens (~8700 saved)
```

If plan mode is active, the plan file context is automatically restored after any compaction.

---

## Diff View

When the model edits or overwrites a file, you see a git-style diff:

```diff
  Changes applied to config.py:

--- a/config.py
+++ b/config.py
@@ -12,7 +12,7 @@
     "model": "claude-opus-4-6",
-    "max_tokens": 8192,
+    "max_tokens": 16384,
     "permission_mode": "auto",
```

Green lines = added, red lines = removed. New file creations show a summary instead.

---

## CLAUDE.md Support

Place a `CLAUDE.md` file in your project to give the model persistent context about your codebase. Pycc automatically finds and injects it into the system prompt.

```
~/.claude/CLAUDE.md          # Global — applies to all projects
/your/project/CLAUDE.md      # Project-level — found by walking up from cwd
```

**Example `CLAUDE.md`:**

```markdown
# Project: FastAPI Backend

## Stack
- Python 3.12, FastAPI, PostgreSQL, SQLAlchemy 2.0, Alembic
- Tests: pytest, coverage target 90%

## Conventions
- Format with black, lint with ruff
- Full type annotations required
- New endpoints must have corresponding tests

## Important Notes
- Never hard-code credentials — use environment variables
- Do not modify existing Alembic migration files
- The `staging` branch deploys automatically to staging on push
```

---

## Session Management

### Storage layout

Every exit automatically saves to three places:

```
~/.pycc/sessions/
├── history.json                          ← master: all sessions ever (capped)
├── mr_sessions/
│   └── session_latest.json              ← always the most recent (/resume)
└── daily/
    ├── 2026-04-05/
    │   ├── session_110523_a3f9.json     ← per-day files, newest kept
    │   └── session_143022_b7c1.json
    └── 2026-04-04/
        └── session_183100_3b4c.json
```

Each session file includes metadata:

```json
{
  "session_id": "a3f9c1b2",
  "saved_at": "2026-04-05 11:05:23",
  "turn_count": 8,
  "messages": [...]
}
```

### Autosave on exit

Every time you exit — via `/exit`, `/quit`, `Ctrl+C`, or `Ctrl+D` — the session is saved automatically:

```
✓ Session saved → /home/.../.pycc/sessions/mr_sessions/session_latest.json
✓              → /home/.../.pycc/sessions/daily/2026-04-05/session_110523_a3f9.json  (id: a3f9c1b2)
✓   history.json: 12 sessions / 87 total turns
```

### Quick resume

To continue where you left off:

```bash
pycc
[myproject] ❯ /resume
✓  Session loaded from …/mr_sessions/session_latest.json (42 messages)
```

Resume a specific file:

```bash
/resume session_latest.json          # loads from mr_sessions/
/resume /absolute/path/to/file.json  # loads from absolute path
```

### Manual save / load

```bash
/save                          # save with auto-name (session_TIMESTAMP_ID.json)
/save debug_auth_bug           # named save to ~/.pycc/sessions/

/load                          # interactive list grouped by date
/load debug_auth_bug           # load by filename
```

**`/load` interactive list:**

```
  ── 2026-04-05 ──
  [ 1] 11:05:23  id:a3f9c1b2  turns:8   session_110523_a3f9.json
  [ 2] 09:22:01  id:7e2d4f91  turns:3   session_092201_7e2d.json

  ── 2026-04-04 ──
  [ 3] 22:18:00  id:3b4c5d6e  turns:15  session_221800_3b4c.json

  ── Complete History ──
  [ H] Load ALL history  (3 sessions / 26 total turns)  /home/.../.pycc/sessions/history.json

  Enter number(s) (e.g. 1 or 1,2,3), H for full history, or Enter to cancel >
```

- Enter a single number to load one session
- Enter comma-separated numbers (e.g. `1,3`) to merge multiple sessions in order
- Enter `H` to load the entire history — shows message count and token estimate before confirming

### Configurable limits

| Config key | Default | Description |
|---|---|---|
| `session_daily_limit` | `5` | Max session files kept per day in `daily/` |
| `session_history_limit` | `100` | Max sessions kept in `history.json` |

```bash
/config session_daily_limit=10
/config session_history_limit=200
```

### history.json — full conversation history

`history.json` accumulates every session in one place, making it possible to search your complete conversation history or analyze usage patterns:

```json
{
  "total_turns": 150,
  "sessions": [
    {"session_id": "a3f9c1b2", "saved_at": "2026-04-05 11:05:23", "turn_count": 8, "messages": [...]},
    {"session_id": "7e2d4f91", "saved_at": "2026-04-05 09:22:01", "turn_count": 3, "messages": [...]}
  ]
}
```

---

## Project Structure

```
pycc/
├── pycc.py        # Entry point: REPL + slash commands + diff rendering + Rich Live streaming
├── agent.py              # Agent loop: streaming, tool dispatch, compaction
├── providers.py          # Multi-provider: Anthropic, OpenAI-compat streaming
├── tools.py              # Core tools (Read/Write/Edit/Bash/Glob/Grep/Web/NotebookEdit/GetDiagnostics) + registry wiring
├── tool_registry.py      # Tool plugin registry: register, lookup, execute
├── compaction.py         # Context compression: snip + auto-summarize
├── context.py            # System prompt builder: CLAUDE.md + git + memory
├── config.py             # Config load/save/defaults; DAILY_DIR, SESSION_HIST_FILE paths
│
├── multi_agent/          # Multi-agent package
│   ├── __init__.py       # Re-exports
│   ├── subagent.py       # AgentDefinition, SubAgentManager, worktree helpers
│   └── tools.py          # Agent, SendMessage, CheckAgentResult, ListAgentTasks, ListAgentTypes
│
├── memory/               # Memory package
│   ├── __init__.py       # Re-exports
│   ├── types.py          # MEMORY_TYPES and format guidance
│   ├── store.py          # save/load/delete/search, MEMORY.md index rebuilding
│   ├── scan.py           # MemoryHeader, age/freshness helpers
│   ├── context.py        # get_memory_context(), truncation, AI search
│   └── tools.py          # MemorySave, MemoryDelete, MemorySearch, MemoryList
├── memory.py             # Backward-compat shim → memory/
│
├── skill/                # Skill package
│   ├── __init__.py       # Re-exports; imports builtin to register built-ins
│   ├── loader.py         # SkillDef, parse, load_skills, find_skill, substitute_arguments
│   ├── builtin.py        # Built-in skills: /commit, /review
│   ├── executor.py       # execute_skill(): inline or forked sub-agent
│   └── tools.py          # Skill, SkillList
│
├── mcp/                  # MCP (Model Context Protocol) package
│   ├── __init__.py       # Re-exports
│   ├── types.py          # MCPServerConfig, MCPTool, MCPServerState, JSON-RPC helpers
│   ├── client.py         # StdioTransport, HttpTransport, MCPClient, MCPManager
│   ├── config.py         # Load .mcp.json (project) + ~/.pycc/mcp.json (user)
│   └── tools.py          # Auto-discover + register MCP tools into tool_registry
│
├── hooks/                # Hook system: pre/post tool execution callbacks
│
├── security/             # Security analyzer: permission checks, sandboxing
│
└── tests/                # 263+ unit tests
    ├── test_mcp.py
    ├── test_memory.py
    ├── test_skills.py
    ├── test_subagent.py
    ├── test_tool_registry.py
    ├── test_compaction.py
    ├── test_diff_view.py
    ├── e2e_plan_mode.py      # 10-step plan mode permission test
    ├── e2e_plan_tools.py     # 8-step EnterPlanMode/ExitPlanMode tool test
    ├── e2e_compact.py        # 9-step compaction test
    └── e2e_commands.py       # 9-step /init /export /copy /status test
```

> **For developers:** Each feature package (`multi_agent/`, `memory/`, `skill/`, `mcp/`, `hooks/`, `security/`) is self-contained. Add custom tools by calling `register_tool(ToolDef(...))` from any module imported by `tools.py`.

---

## FAQ

**Q: How do I add an MCP server?**

Option 1 — via REPL (stdio server):
```
/mcp add git uvx mcp-server-git
```

Option 2 — create `.mcp.json` in your project:
```json
{
  "mcpServers": {
    "git": {"type": "stdio", "command": "uvx", "args": ["mcp-server-git"]}
  }
}
```

Then run `/mcp reload` or restart. Use `/mcp` to check connection status.

**Q: An MCP server is showing an error. How do I debug it?**

```
/mcp                    # shows error message per server
/mcp reload git         # try reconnecting
```

If the server uses stdio, make sure the command is in your `$PATH`:
```bash
which uvx               # should print a path
uvx mcp-server-git      # run manually to see errors
```

**Q: Can I use MCP servers that require authentication?**

For HTTP/SSE servers with a Bearer token:
```json
{
  "mcpServers": {
    "my-api": {
      "type": "sse",
      "url": "https://myserver.example.com/sse",
      "headers": {"Authorization": "Bearer sk-my-token"}
    }
  }
}
```

For stdio servers with env-based auth:
```json
{
  "mcpServers": {
    "brave": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-server-brave-search"],
      "env": {"BRAVE_API_KEY": "your-key"}
    }
  }
}
```

**Q: Tool calls don't work with my local Ollama model.**

Not all models support function calling. Use one of the recommended tool-calling models: `qwen2.5-coder`, `llama3.3`, `mistral`, or `phi4`.

```bash
ollama pull qwen2.5-coder
pycc --model ollama/qwen2.5-coder
```

**Q: How do I connect to a remote GPU server running vLLM?**

```
/config custom_base_url=http://your-server-ip:8000/v1
/config custom_api_key=your-token
/model custom/your-model-name
```

**Q: How do I check my API cost?**

```
/cost

  Input tokens:  3,421
  Output tokens:   892
  Est. cost:     $0.0648 USD
```

**Q: Can I use multiple API keys in the same session?**

Yes. Set all the keys you need upfront (via env vars or `/config`). Then switch models freely — each call uses the key for the active provider.

**Q: How do I make a model available across all projects?**

Add keys to `~/.bashrc` or `~/.zshrc`. Set the default model in `~/.pycc/config.json`:

```json
{ "model": "claude-sonnet-4-6" }
```

**Q: Qwen / Zhipu returns garbled text.**

Ensure your `DASHSCOPE_API_KEY` / `ZHIPU_API_KEY` is correct and the account has sufficient quota. Both providers use UTF-8 and handle Chinese well.

**Q: Can I pipe input to pycc?**

```bash
echo "Explain this file" | pycc --print --accept-all
cat error.log | pycc -p "What is causing this error?"
```

**Q: How do I run it as a CLI tool from anywhere?**

Use `uv tool install` — it creates an isolated environment and puts `pycc` on your PATH:

```bash
cd pycc
uv tool install .
```

After that, just run `pycc` from any directory. To update after pulling changes, run `uv tool install . --reinstall`.
