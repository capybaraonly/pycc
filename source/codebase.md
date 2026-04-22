# pycc 代码库地图

## 顶层核心文件

### `pycc.py`
整个项目的入口和交互层，约 2100+ 行。

用户启动后进入 REPL 主循环，负责：读取用户输入（支持多行粘贴）、渲染流式 Markdown 输出、显示工具执行动画、处理权限询问弹框、分发所有 `/slash` 命令。

主要内容：
- **REPL 主循环**：`readline` + bracketed paste，Ctrl+C 三连退出
- **流式渲染**：Rich 的 Markdown 渲染，逐 token 打印，thinking block 折叠显示
- **权限弹框**：工具执行前弹出 y/n/always/never，三种权限模式（auto / manual / accept-all）
- **Slash 命令**：`/help` `/clear` `/model` `/config` `/save` `/load` `/history` `/context` `/cost` `/verbose` `/thinking` `/permissions` `/cwd` `/memory` `/skills` `/agents` `/mcp` `/tasks` `/exit` 等约 20 个命令
- **Diff 渲染**：Edit/Write 工具结果显示 unified diff，带语法高亮
- **后台任务追踪**：子代理任务状态轮询、打印完成通知
- **会话存取**：JSON 序列化整个对话历史到 `~/.pycc/sessions/`

入口函数 `main()` 解析 `--model`、`--version`、`--help`、`-p`（直接传 prompt）等命令行参数，然后进 REPL。

---

### `agent.py`
Agent 核心循环，约 280 行。

一次 `run()` 调用代表一个完整的"用户发消息 → LLM 回复 → 执行工具 → 继续直到 stop_reason=end_turn"的过程。返回值是一个生成器，持续 yield 事件对象供 `pycc.py` 渲染。

事件类型：`TextChunk` / `ThinkingChunk` / `ToolStart` / `ToolEnd` / `TurnDone` / `PermissionRequest`

主要逻辑：
1. 调用 `build_system_prompt()` 拼系统提示
2. 调用 `apply_context_collapse()` 做读时压缩
3. 调用 `providers.stream()` 流式拿 LLM 回复
4. 遇到 tool_use → 检查权限（三模式）→ 触发 pre_tool hooks → `execute_tool()` → 触发 post_tool hooks → 把结果塞回消息列表
5. stop_reason=end_turn 时 yield `TurnDone`，退出循环

Plan 模式下每 5 轮自动插一条提醒消息，只读工具白名单强制执行。

---

### `providers.py`
多 Provider 统一流式接口，约 680 行。

把 10+ 个 LLM 提供商（Anthropic、OpenAI、Gemini、Kimi、Qwen、智谱、DeepSeek、Minimax、Ollama、LM Studio 及自定义端点）封装成同一个 `stream()` 函数。调用方不需要知道底层是哪家。

核心设计：
- `PROVIDERS` 字典：每个 provider 的 base_url、支持的模型列表、context 窗口大小、API key 环境变量名
- `detect_provider(model_name)`：根据模型名前缀自动判断是哪家，或解析 `"provider/model"` 格式
- `stream_anthropic()`：用 Python SDK，支持 extended thinking（budget_tokens）
- `stream_openai_compat()`：用 JSON-RPC HTTP，兼容所有 OpenAI 协议的服务（Gemini、Kimi 等都走这个）
- `stream_ollama()`：用 `urllib`，工具调用不支持时自动降级重试（剥掉 tools 参数再发一次）
- 消息格式转换：中立格式 ↔ Anthropic 格式、OpenAI 格式互转
- `calc_cost()`：按模型名查 input/output token 单价，算一次调用花了多少钱

所有 provider 都 yield 同类型的事件：`TextChunk` / `ThinkingChunk` / `Response`（含工具调用列表和 token 用量）。

---

### `config.py`
配置加载与保存，约 80 行。

从 `~/.pycc/config.json` 读取用户配置，合并默认值和环境变量。

- `DEFAULTS`：默认 model、max_tokens、permission_mode 等
- `load_config()`：读文件 → 合并 DEFAULTS → 覆盖 env vars（如 `ANTHROPIC_API_KEY`）
- `save_config()`：写回文件，过滤掉运行时内部字段（如 `_session_id`）
- 路径常量：`CONFIG_DIR`（`~/.pycc/`）、`SESSIONS_DIR`、`DAILY_DIR`

---

### `context.py`
系统提示构建器，约 275 行。

每次 API 调用前动态拼出完整的 system prompt，分静态和动态两部分。

- **静态部分** `SYSTEM_PROMPT_STATIC`：工具列表、行为准则、格式要求——这部分内容固定，走 Anthropic prompt cache 节省费用
- **动态部分** `_DYNAMIC_TEMPLATE`：当前日期、工作目录、git 分支和状态、CLAUDE.md 内容——每次调用刷新
- `get_git_info()`：拿 branch 名、`git status --short`、最近 3 条 commit
- `get_claude_md()`：从当前目录向上找 `CLAUDE.md`，加上用户 `~/.claude/CLAUDE.md`
- `build_system_prompt()`：把静态 + 动态 + memory 索引 + plan mode 附加说明拼在一起

---

### `compaction.py`
五层上下文压缩策略，约 520 行。

对话越来越长时，context 窗口会撑满。这个文件实现了从轻到重五种压缩手段：

| 层级 | 触发时机 | 手段 |
|------|----------|------|
| Layer 1 | 工具返回大结果时 | 结果写磁盘，context 里只放摘要（在 tool_registry.py） |
| Layer 2 | 主动调用 | 删除早期完整 turn（user + assistant + tool result），只保留最近 N 轮 |
| Layer 3 | 空闲 60 分钟后 | 把可重新获取的工具结果（Read/Glob/Grep）内容清空 |
| Layer 4 | 每次 API 调用前 | 超过 90% 阈值 → 只保留最近 40% 消息，旧的折叠成一行 |
| Layer 5 | 显式 /compact 命令 | 调 LLM 生成 9 段结构化摘要，替换旧消息 |

关键函数：
- `snip_old_messages(messages, preserve_last_n_turns)`：删除旧 turn，返回释放的 token 估算数
- `micro_compact(messages)`：Layer 3，只清空可再拉取的工具结果
- `apply_context_collapse(messages, limit)`：Layer 4，读时投影
- `compact_messages(messages, config)`：Layer 5，LLM 摘要，有 3 次失败熔断

---

### `tool_registry.py`
工具注册表和调度器，约 170 行。

所有工具（内置 + MCP）统一在这里注册和调用。

- `ToolDef` dataclass：name、schema（给 LLM 看的 JSON Schema）、func（实际执行函数）、read_only 标志、concurrent_safe 标志
- `register_tool()` / `get_tool()` / `get_all_tools()` / `get_tool_schemas()`：注册表增删查
- `execute_tool(name, params, config)`：
  1. 查表找 ToolDef
  2. 调 func 执行
  3. 结果 > 50KB → 写到 `~/.pycc/tool_results/<session_id>/xxx.txt`，context 里只放文件路径预览
  4. 如果磁盘写失败 → 硬截断 + 加 `[truncated]` 标记
  5. 顺便记录文件访问日志，供 compaction 恢复用

`DISK_OFFLOAD_THRESHOLD = 50_000`（字节），是触发磁盘卸载的阈值。

---

### `tools.py`
所有内置工具的实现，约 1300+ 行。

每个工具是一个函数 + 一份 JSON Schema，注册到 `tool_registry`。

主要工具：

| 工具 | 功能 |
|------|------|
| `Read` | 读文件，支持 offset/limit 行号范围 |
| `Write` | 写文件，返回 unified diff |
| `Edit` | 精确字符串替换，支持 replace_all |
| `Bash` | 执行 shell 命令，带超时，先过安全检查 |
| `Glob` | 文件名模式匹配 |
| `Grep` | 正则搜索文件内容（封装 ripgrep） |
| `WebFetch` | 抓网页内容 |
| `WebSearch` | 搜索引擎查询 |
| `NotebookEdit` | 编辑 Jupyter .ipynb 单元格 |
| `GetDiagnostics` | 调 pyright/mypy/flake8 做静态检查 |
| `AskUserQuestion` | 暂停等用户输入 |
| `SleepTimer` | 后台定时器 |

`TOOL_SCHEMAS` 列表：所有工具的 schema 合集，发给 LLM 告知可用工具。

`_is_safe_bash(cmd)`：调 `bash_analyzer` 分析命令风险等级，决定是否需要用户确认。

---

## `hooks/` — 钩子系统

允许外部 shell 脚本或 webhook 介入 agent 的生命周期事件。

### `hooks/types.py`
数据类定义：`HookCommand`（type + command）、`HookMatcher`（匹配条件 + hook 列表）、`HooksConfig`（所有事件的 matcher 列表）、`HookDecision`（block / approve / ask）。

### `hooks/loader.py`
从 `.claude/settings.json` 加载 hooks 配置。搜索顺序：用户级 `~/.claude/settings.json` → 项目级（从当前目录向上找）。两份配置合并。

配置格式（与 Claude Code 兼容）：
```json
{
  "hooks": {
    "PreToolUse": [{ "matcher": "Bash", "hooks": [{ "type": "command", "command": "my-script.sh" }] }]
  }
}
```

### `hooks/executor.py`
执行单个 hook 命令：`subprocess` 启动、把事件 JSON 写入 stdin、读 stdout 解析 JSON 结果。超时 10 秒，失败打 warning 不中断主流程。

### `hooks/dispatcher.py`
触发各类事件对应的 hooks：
- `fire_pre_tool(tool_name, params)`：运行匹配的 PreToolUse hooks，收集 block/approve/ask 决定
- `fire_post_tool(tool_name, result)`：fire-and-forget，不等结果
- `fire_stop()`：turn 结束后触发
- `fire_notification(msg)`：权限弹框时触发（可用于发手机通知）
- `fire_pre_compact()`：压缩前触发

---

## `mcp/` — MCP 服务器集成

Model Context Protocol，让外部进程作为工具服务器给 agent 提供工具。

### `mcp/types.py`
数据类：`MCPServerConfig`（name、type、command/url/env）、`MCPTool`（server_name + 工具 schema）、`MCPServerState` 枚举。

工具函数：`make_request()` / `make_notification()` 构造 JSON-RPC 2.0 消息体，`MCPTool.to_tool_schema()` 把 MCP 工具描述转成 Claude API 格式。

### `mcp/config.py`
加载 MCP 服务器配置，来源：
1. `~/.pycc/mcp.json`（用户级，全局生效）
2. `.mcp.json`（项目级，覆盖同名服务器）

`add_server_to_user_config()` / `remove_server_from_user_config()`：`/mcp add` 和 `/mcp remove` 命令的底层实现。

### `mcp/client.py`
MCP 客户端，约 350 行。实现两种传输：

- **StdioTransport**：subprocess 方式，stdin 写 JSON-RPC，stdout 读响应，独立线程跑读循环
- **HttpTransport**：SSE（Server-Sent Events）收流，`httpx` POST 发请求

`MCPClient`：单服务器的完整生命周期（connect → JSON-RPC initialize → list_tools → call_tool）。请求和响应按 ID 匹配，用 `threading.Event` 做同步等待。

`MCPManager`：单例，管理所有已连接的 MCPClient，提供统一的 `call_tool(server, tool, params)` 入口。

### `mcp/tools.py`
把 MCP 工具注册进 `tool_registry`：
- `initialize_mcp()`：加载配置 → 连接所有服务器 → 拿工具列表 → 注册（幂等，有锁）
- 模块导入时启动后台线程做异步初始化，不阻塞启动速度
- 工具名格式：`mcp__<server_name>__<tool_name>`

---

## `memory/` — 持久记忆

跨会话保存和检索信息。

### `memory/types.py`
定义记忆类型分类（`MEMORY_TYPES`：user / feedback / project / reference）、每种类型的用途说明、以及 `WHAT_NOT_TO_SAVE` 列表（代码片段、git 历史、调试过程等不适合存的东西）。

### `memory/store.py`
文件系统级 CRUD，约 300 行。

存储位置：用户级 `~/.pycc/memory/`，项目级 `.pycc/memory/`。每条记忆是一个 `.md` 文件，文件头是 YAML frontmatter（name、description、type、scope），正文是内容。

同时维护一个 `MEMORY.md` 索引文件，列出所有记忆的摘要，用于注入系统提示。

`parse_frontmatter()`：手写的简单 YAML 解析（不依赖 pyyaml）。

### `memory/context.py`
把记忆内容格式化进系统提示，约 200 行。

- `get_memory_context()`：读 user + project 两份 `MEMORY.md`，合并，超出 1000 行 / 100KB 截断（与 Claude Code 兼容）
- `find_relevant_memories()`：关键词搜索，可选用 AI 排序
- `_ai_select_memories()`：调 claude-haiku 做轻量排序（失败时降级为按时间排序）

### `memory/retriever.py`
后台异步检索，约 235 行。设计思路是：在等 LLM 回复的时候，同时在后台扫描相关记忆，下一轮再用。

- `scan_memory_headers()`：只读每个文件前 30 行（拿 frontmatter），不加载正文，很快
- `select_relevant_memories()`：把 header 列表发给 Sonnet，让它返回相关记忆的序号 JSON
- `load_selected_memories()`：只加载被选中的记忆全文，附加过期警告（超过 1 天）
- `retrieve_for_query(query)`：一步完成（scan → select → load）

### `memory/scan.py`
扫描记忆目录生成可读报告，约 250 行。

- `scan_memory_dir()` / `scan_all_memories()`：glob `.md` 文件（排除 `MEMORY.md`）
- `format_memory_manifest()`：格式化成人读的文本，`/memory` 命令的显示内容
- `memory_age_str()` / `memory_freshness_text()`：计算记忆新鲜度（"3 天前" / "⚠️ 可能过期"）

---

## `multi_agent/` — 子代理系统

允许主 agent 派生后台子代理并行处理任务。

### `multi_agent/subagent.py`
子代理的定义和运行时，约 400 行。

内置 4 种代理类型，各有专属系统提示：
- `general-purpose`：通用，全工具访问
- `coder`：专注代码实现
- `reviewer`：代码审查，只读工具
- `researcher`：信息收集，只读 + web

支持从 `.md` 文件（YAML frontmatter）加载自定义代理定义，用户级（`~/.pycc/agents/`）或项目级（`.pycc/agents/`）。

`SubAgentTask`：一个任务的完整状态（id、prompt、status、result、depth、inbox 消息队列、取消标志）。

`SubAgentManager`：`ThreadPoolExecutor` 管理并发，限制最大深度（防止无限嵌套），支持 worktree 隔离（每个任务在独立 git worktree 里跑）。

`_agent_run()`：延迟 import `agent` 避免循环依赖，然后跑完整 agent 循环。

### `multi_agent/tools.py`
实现 5 个工具，约 200 行：

| 工具 | 功能 |
|------|------|
| `Agent` | 派生子代理，返回 task_id；`isolation=worktree` 时在独立分支跑 |
| `SendMessage` | 向指定名称的子代理发消息（异步） |
| `CheckAgentResult` | 查任务状态和结果（轮询或等待） |
| `ListAgentTasks` | 列出所有后台任务 |
| `ListAgentTypes` | 列出可用代理类型 |

---

## `security/` — 安全分析

### `security/bash_analyzer.py`
三级 Bash 命令风险分析，约 260 行。

`analyze_bash(cmd)` 返回 `(BashRiskLevel, reason_str)`：

- **DANGEROUS**（必须确认）：`rm -rf /`、`pipe curl | sh`、`dd if=... of=/dev/sd*`、`sudo rm -r`、`chmod 777 /etc`
- **SAFE**（自动放行）：`git log/diff/status`、`ls/cat/find/grep`、`python/node -c`、`pytest`、`pip list`、`make`、`cargo build` 等只读或安全前缀命令
- **WARN**（显示警告但允许）：`rm -r`（非根目录）、`chmod/chown`、`curl/wget`、`git push`、`pip/npm install`、命令替换 `$(...)`

优先级：dangerous > safe prefix > warn > 默认 warn。

---

## `skill/` — 可复用提示模板

### `skill/types.py` / `skill/loader.py`
`SkillDef` dataclass：name、description、prompt 模板、arguments 列表（支持默认值和选项枚举）、触发词列表、允许的工具集等。

`_parse_skill_file()`：读 `.md` 文件，可选 YAML frontmatter（name、description、arguments…），正文是 prompt 模板。

`substitute_arguments(prompt, args)`：把 `$ARGUMENTS` 或 `$VAR_NAME` 替换成实际值。

加载顺序：内置 → 用户级（`~/.pycc/skills/`）→ 项目级（`.pycc/skills/`），同名时后者覆盖。

### `skill/builtin.py`
注册两个内置 skill：
- `commit`：复查 staged 变更，写规范 commit message
- `review`：代码审查，支持传 PR 号

### `skill/executor.py`
`execute_skill(skill_def, args, messages, config)`：把 skill prompt（替换参数后）作为用户消息注入，然后跑 `agent.run()`，yield 全部事件。skill 执行是 inline 的，不开新会话。

### `skill/tools.py`
注册 `SkillExecute` 工具，让 agent 自己能触发 skill（而不是只有用户能触发）。

---

## `task/` — 任务列表

### `task/types.py`
`TaskStatus` 枚举：PENDING / IN_PROGRESS / COMPLETED / CANCELLED。

`Task` dataclass：id、subject、description、status、owner、metadata（任意 KV）、created_at、updated_at。

`to_dict()` / `from_dict()`：序列化，`from_dict` 遇到未知 status 值时默认 PENDING。

`status_icon()`：返回 `·` / `→` / `✓` / `✗`。

`one_line()`：`#1 · Write tests` 格式，用于列表显示。

### `task/store.py`
JSON 文件持久化，约 150 行。存到 `~/.pycc/tasks.json`。

- `create_task(subject, description, **kwargs)`：自增 ID（字符串 "1"、"2"…），保存到磁盘
- `update_task(id, **fields)`：只更新传入的字段，metadata 做 merge（None 值删 key），返回 `(Task, changed_fields)`
- `delete_task(id)` / `clear_all_tasks()`：删除
- `_load()`：懒加载，第一次操作时从磁盘读，之后内存缓存
- 用 `threading.Lock` 保证并发安全

### `task/tools.py`
注册 4 个工具：`TaskCreate` / `TaskUpdate` / `TaskGet` / `TaskList`。所有工具返回人读字符串。

`_task_update` 特殊逻辑：`status="deleted"` 时实际调 `delete_task()`，让 agent 用一个工具就能删任务。

---

## `tests/` — 测试

### 单元测试

| 文件 | 测什么 |
|------|--------|
| `test_compaction.py` | token 估算、snip_old_messages、context collapse 阈值、split point 查找 |
| `test_task.py` | Task 类型、store CRUD、持久化轮回、并发唯一 ID、tool 函数字符串输出 |
| `test_tool_registry.py` | 注册/查找工具、小结果不截断、磁盘卸载失败时的兜底截断 |
| `test_memory.py` | store CRUD、MEMORY.md 索引维护、context 构建、检索关键词过滤 |
| `test_skills.py` | 文件解析、frontmatter 字段、参数替换、未知 frontmatter 字段忽略 |
| `test_subagent.py` | AgentDefinition 加载、内置类型、.md 自定义代理解析 |
| `test_mcp.py` | MCPServerConfig 解析、MCPTool schema 转换、MCPManager 状态机 |
| `test_diff_view.py` | diff 渲染输出格式 |

### E2E 测试

| 文件 | 测什么 |
|------|--------|
| `e2e_commands.py` | `/init`、`/export`、`/copy`、`/status` 等 slash 命令完整流程 |
| `e2e_compact.py` | 长对话触发压缩、压缩后内容完整性 |
| `e2e_plan_mode.py` | Plan 模式下只读限制、turn 提醒注入 |
| `e2e_plan_tools.py` | Plan 模式工具白名单执行 |

---

## 项目配置文件

### `pyproject.toml`
setuptools 构建配置。关键字段：
- `name = "pycc"`，`version = "3.05.6"`，`requires-python = ">=3.10"`
- 依赖：anthropic、openai、httpx、rich
- 可选：`vision`（Pillow）、`dev`（pytest）
- 入口点：`pycc = "pycc:main"`
- py-modules（单文件模块）：pycc、agent、compaction、config、context、providers、tool_registry、tools
- packages（目录包）：hooks、mcp、memory、multi_agent、security、skill、task

### `requirements.txt`
锁定版本的依赖列表，包含 sounddevice / faster-whisper / numpy（保留的语音相关依赖，功能已删但 requirements 里还留着）。

### `LICENSE`
Apache 2.0 许可证全文。

---

## 系统调用链（一次用户输入的完整路径）

```
用户按回车
  → pycc.py REPL 主循环
    → agent.py run() 生成器
      → context.py build_system_prompt()   # 拼系统提示
      → compaction.py apply_context_collapse()  # 必要时压缩
      → providers.py stream()              # 调 LLM
        ↳ stream_anthropic() 或 stream_openai_compat() 或 stream_ollama()
      → 遇到 tool_use
        → hooks/dispatcher.py fire_pre_tool()
        → tool_registry.py execute_tool()
          ↳ tools.py 里的具体函数
          ↳ 或 mcp/tools.py 转发到外部服务器
        → hooks/dispatcher.py fire_post_tool()
      → stop_reason=end_turn → yield TurnDone
  → pycc.py 打印最终结果
```
