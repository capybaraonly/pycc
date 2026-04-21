# 改写计划：对齐 Claude Code

**目标**：删除 pycc 自行扩展的功能，补充缺失的外部 hooks 系统，使整体架构与 Claude Code 一致。语言层面（同步/异步）不改。

**项目路径**：`/Users/capybara/Documents/pycc-main`

## 一、删除项

### 1. Checkpoint / 文件版本系统

**原因**：Claude Code 无此功能，属于 pycc 自行扩展。

删除以下内容：

- 删除整个 `checkpoint/` 目录（`hooks.py`、`store.py`、`types.py`、`init.py`）
- `tools.py` 底部有 `from checkpoint.hooks import install_hooks as _install_checkpoint_hooks` + `_install_checkpoint_hooks()`，删除这两行
- `pycc.py` 中搜索 `checkpoint`、`make_snapshot`、`get_tracked_edits`、`reset_tracked`、`session_id` 相关调用，全部删除
- `pycc.py` 中的 `/checkpoint`、`/rewind` 斜杠命令处理函数，删除
- `config.py` 中若有 checkpoint 相关 key，删除

### 2. Plugin 系统

**原因**：Claude Code 无 plugin manifest 机制。

删除以下内容：

- 删除整个 `plugin/` 目录
- `pycc.py` 中的 `/plugin` 斜杠命令处理函数，删除
- 搜索 `plugin` 相关 import 和调用，全部删除

### 3. Task DAG（`blocks` / `blocked_by` 依赖边）

**原因**：Claude Code 有 TodoWrite，但是简单列表，无依赖图。

操作：

- `task/types.py` 中删除 `blocks`、`blocked_by` 字段
- `task/store.py` 中删除依赖解析逻辑
- 保留基础 `TaskCreate` / `TaskUpdate` / `TaskGet` / `TaskList` 工具
- 保留 `pending` / `in_progress` / `completed` / `cancelled` 状态
- 保留 `active_form` 字段
- `pycc.py` 中删除依赖相关的展示逻辑

### ~~4. 多 Provider 支持~~ ⏭️ 跳过

> **决策变更（2026-04-14）**：保留多 provider 支持，`providers.py` 不做改动。

### 5. Skill fork 模式

**原因**：Claude Code skill 只有 inline 执行，无 fork（子 agent）模式。

操作：

- `skill/executor.py` 中删除 `context == "fork"` 分支（约第 34、65 行区域），只保留 inline 执行
- `skill/loader.py` 中 `SkillDef` 删除 `context` 字段（或忽略该字段）

### 6. Memory 增强字段

**原因**：Claude Code memory 是简单文件，无 `consolidation`、`confidence`、`conflict_group`。

操作：

- `memory/store.py` 中 `MemoryEntry` 删除字段：`confidence`、`source`、`last_used_at`、`conflict_group`
- 删除整个 `memory/consolidator.py`（AI 驱动的记忆整合）
- 删除 `memory/scan.py`（如果仅服务于 consolidator）
- 保留：`name`、`description`、`type`、`content`、`file_path`、`created`、`scope`
- 保留 user/project 双作用域、`MEMORY.md` 索引、`MemorySave` / `MemoryDelete` / `MemorySearch` / `MemoryList` 工具

### 7. Voice / Video

**原因**：与 coding agent 无关，Claude Code 无此功能。

操作：

- 删除整个 `voice/` 目录
- 删除整个 `video/` 目录
- `pycc.py` 中删除 `/voice`、`/video` 斜杠命令处理函数及相关 import

### 8. Telegram 集成

**原因**：Claude Code 无此功能。

操作：

- `tools.py` 中删除 Telegram 相关工具
- 删除 `demos/make_telegram_demo.py`（如存在）

### 9. Proactive 后台监控

**原因**：Claude Code 无 inactivity watcher。

操作：

- `pycc.py` 中删除 `_proactive_watcher_loop()` 函数（约 351-372 行）
- 删除 `pycc.py` 约 4099-4105 行的后台线程启动代码
- `config.py` 中删除 `_proactive_enabled`、`_proactive_interval`、`_last_interaction_time`、`_proactive_thread`、`_run_query_callback` 相关 key
- `pycc.py` 中删除 `/proactive` 斜杠命令

### 10. CloudSave 云同步

**原因**：Claude Code 无此功能，属于 pycc 自行扩展。

操作：

- 删除整个 `cloudsave.py`
- `pycc.py` 中删除 `cmd_cloudsave()`（第 1088 行）、`_build_session_data()`（第 1068 行）、退出时自动上传逻辑（约第 1209-1221 行）
- `config.py` 中删除 `gist_token`、`cloudsave_auto`、`cloudsave_last_gist_id`

### 11. Brainstorm 多 persona 辩论

**原因**：Claude Code 无此功能。

操作：

- `pycc.py` 中删除 `cmd_brainstorm()`（第 494 行）、`_generate_personas()`（第 408 行）、`_interactive_ollama_picker()`（第 460 行）、`_save_synthesis()`（第 645 行）
- 删除 `demos/make_brainstorm_demo.py`

### 12. SSJ 超级开发者菜单

**原因**：OpenClaw 功能聚合入口，其子功能均已删除。

操作：

- `pycc.py` 中删除 `cmd_ssj()` 整个函数（第 1674-约 1900 行）
- 删除 `demos/make_ssj_demo.py`

### 13. Worker 自动任务执行器

**原因**：读取 `todo_list.txt` 自动派发子 agent 批量执行，非 Claude Code 标准功能。

操作：

- `pycc.py` 中删除 `cmd_worker()`（第 1903 行）

### 14. `demos/` 目录和 `demo.py`

**原因**：全为 OpenClaw 演示脚本，无代码价值。

操作：

- 删除整个 `demos/` 目录
- 删除根目录 `demo.py`

## 二、新增项：外部 Hooks 系统

**目标行为**：对齐 Claude Code 规格。

### 配置文件读取路径

两处均读，合并，项目级优先：

- 项目级：从当前目录向上查找 `.claude/settings.json`
- 全局：`~/.claude/settings.json`

### 配置格式

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "your_script.sh" }]
      }
    ],
    "PostToolUse": [...],
    "Stop": [...],
    "Notification": [...],
    "PreCompact": [...]
  }
}
```

`matcher` 规则：空字符串或 `"*"` 匹配所有；否则判断 `tool_name.startswith(matcher) or tool_name == matcher`。

### Hook stdin（JSON）

```jsonc
// PreToolUse / PostToolUse
{"session_id": "...", "tool_name": "Bash", "tool_input": {...}}

// PostToolUse 额外包含：
{"tool_response": {...}}

// Stop
{"session_id": "...", "stop_reason": "end_turn"}

// PreCompact
{"session_id": "...", "messages_count": 42, "token_count": 95000}
```

### Hook stdout（仅 `PreToolUse` 有效）

```jsonc
{"decision": "block", "reason": "原因"}   // 阻断，reason 展示给用户
{"decision": "approve"}                   // 跳过权限询问直接执行
// 无输出 / {"decision": "ask"} = 走原有权限逻辑
```

非零退出码：记录警告，不阻断执行。

### 实现步骤

#### Step 1：新建 `hooks/` 目录

包含四个文件：

- `hooks/types.py`
  定义 `HookCommand`、`HookMatcher`、`HooksConfig`、`HookDecision` dataclass（字段见上文规格）。
- `hooks/loader.py`
  - `load_settings_json(cwd) -> dict`：从 `cwd` 向上查找 `.claude/settings.json`，合并全局 `~/.claude/settings.json`，返回合并后的 hooks 配置
  - `parse_hooks_config(raw: dict) -> HooksConfig`：解析 JSON 为 dataclass
  - `get_hooks_config(cwd) -> HooksConfig`：缓存，session 内只加载一次
- `hooks/executor.py`
  - `run_hook(command: str, stdin_data: dict, timeout: int = 10) -> dict | None`
  - 用 `subprocess.run(command, shell=True, input=json.dumps(stdin_data).encode(), capture_output=True, timeout=timeout)`
  - 返回解析后的 stdout JSON，失败返回 `None`
- `hooks/dispatcher.py`
  - `fire_pre_tool(tool_name, tool_input, session_id, cwd) -> HookDecision`：遍历匹配的 `PreToolUse` hooks，第一个 `block` 立即返回，有 `approve` 返回 `approve`，否则返回 `ask`
  - `fire_post_tool(tool_name, tool_input, tool_response, session_id, cwd) -> None`
  - `fire_stop(stop_reason, session_id, cwd) -> None`
  - `fire_notification(message, session_id, cwd) -> None`
  - `fire_pre_compact(messages_count, token_count, session_id, cwd) -> None`
- `hooks/init.py`
  导出上述 `fire_*` 函数。

#### Step 2：修改 `agent.py`

在工具执行前（约 127 行区域），原有 `_check_permission()` 调用之前插入：

```python
from hooks.dispatcher import fire_pre_tool, fire_post_tool

hook_decision = fire_pre_tool(
    tc["name"], tc.get("input", {}),
    config.get("_session_id", ""), config.get("_cwd", ".")
)

if hook_decision.decision == "block":
    yield ToolEnd(
        tool_call_id=tc["id"],
        name=tc["name"],
        result=f"[Blocked by hook: {hook_decision.reason}]",
        is_error=True,
    )
    continue
elif hook_decision.decision == "approve":
    permitted = True
else:
    # 原有 _check_permission 逻辑不变
    permitted = _check_permission(tc, config)
    ...
```

工具执行完成后，在产出 `ToolEnd` 事件之后插入：

```python
fire_post_tool(
    tc["name"],
    tc.get("input", {}),
    result_dict,
    config.get("_session_id", ""),
    config.get("_cwd", "."),
)
```

在 agent turn 结束（`TurnDone` 产出）后插入：

```python
from hooks.dispatcher import fire_stop

fire_stop(finish_reason, config.get("_session_id", ""), config.get("_cwd", "."))
```

#### Step 3：修改 `compaction.py`

在 `maybe_compact()` 执行压缩之前：

```python
from hooks.dispatcher import fire_pre_compact

fire_pre_compact(
    len(messages),
    estimated_tokens,
    config.get("_session_id", ""),
    config.get("_cwd", "."),
)
```

#### Step 4：注入 `session_id` 和 `cwd`

`pycc.py` session 初始化位置（删除 checkpoint 代码后的同一区域）：

```python
import os
import uuid

config.setdefault("_session_id", str(uuid.uuid4()))
config.setdefault("_cwd", os.getcwd())
```

#### Step 5：触发 `Notification` hook

`pycc.py` 中向用户展示通知的位置（权限询问弹出时、长时间等待提示时）：

```python
from hooks.dispatcher import fire_notification

fire_notification(message, config.get("_session_id", ""), config.get("_cwd", "."))
```

## 三、重写上下文窗口管理（对齐 Claude Code 五层压缩）

现状：`compaction.py` 只有简化的两层实现，且两层均有缺陷。需要重写为五层递进压缩架构。

### 第 1 层：大结果存磁盘

改动位置：`tool_registry.py` 的 `execute_tool()`，现在是直接截断到 32,000 字符。

改为：

- 单个工具结果超过约 `50KB`：写入磁盘（路径如 `~/.pycc/tool_results/<session_id>/<tool_use_id>.txt`），上下文中替换为 `2KB` 预览（文件前 `2KB` + 说明“完整内容已存磁盘，如需可重新读取”）
- 新增消息级总量控制：同一条消息内所有工具结果超 `200KB`，挑最大的存磁盘，循环直到达标
- 删除现有的硬截断逻辑

### 第 2 层：砍掉远古消息

改动位置：`compaction.py` 的 `snip_old_tool_results()`，现在是裁剪消息内容而非移除消息。

改为：

- 直接移除最老的一批完整消息（而不是裁剪其内容）
- 在移除位置插入边界标记消息：`[Earlier conversation history has been removed. N tokens freed.]`
- 记录释放的 token 数，传给第 5 层用于判断是否需要触发全量摘要

### 第 3 层：Micro-compact

新增函数 `micro_compact(messages, config)` in `compaction.py`：

- 定义可清理工具集合（可重新获取的）：`Read`、`Bash`、`Glob`、`Grep`、`WebFetch`、`WebSearch`、`Edit`、`Write`
- 不可清理工具：`Agent`、Task 相关工具结果永不清理
- 触发条件：距上次 API 调用超过 60 分钟（prompt cache 大概率已过期）
- 逻辑：收集所有可清理工具的结果，保留最近 5 个，其余替换为 `[Old tool result content cleared]`
- 在 `maybe_compact()` 中作为第 3 层调用，位于第 2 层之后

### 第 4 层：读时投影 Context Collapse

新增函数 `apply_context_collapse(messages, config) -> list` in `compaction.py`：

- 不修改 `state.messages`，只返回一个压缩后的视图用于本次 API 调用
- `90%` 阈值：对旧消息段做分段摘要（每段独立压缩，非全量）
- `95%` 阈值：压缩更激进，缩减更多
- 在 `agent.py` 的 API 调用前执行，用压缩视图替代原始消息传给 API，但 `state.messages` 保持不变

### 第 5 层：全量摘要

改动位置：`compaction.py` 的 `compact_messages()`。

改动点：

- 删除 `content[:500]` 截断，将完整旧消息内容传给摘要模型
- 替换现有简单 prompt，改为结构化 prompt，要求模型按九个维度摘要：用户意图、关键决策、涉及文件及内容、工具执行结果、遇到的错误及修复、用户所有消息（不遗漏）、待完成任务、当前工作状态、建议下一步
- 压缩完成后新增 Post-Compact Restoration：从 `config` 中维护的 `_file_access_log`（记录每个文件最后访问时间）里挑最近访问的最多 5 个文件，预算 `50K token`，重新注入上下文；同时恢复活跃 skill 内容（`25K token` 预算）；plan 文件恢复逻辑已有，保留
- 新增熔断：连续失败 3 次后放弃，不再重试

配套改动：在 `agent.py` 或 `tools.py` 中，每次工具执行后记录文件访问日志到 `config["_file_access_log"]`（`dict`，key 为文件路径，value 为访问时间戳），供第 5 层恢复使用。

### `maybe_compact()` 最终调用顺序

```python
def maybe_compact(state, config):
    # 第 2 层：先砍远古消息，记录释放量
    snip_tokens_freed = snip_old_messages(state.messages)

    # 第 3 层：Micro-compact（时间衰减触发）
    micro_compact(state.messages, config)

    # 第 4 层：读时投影（返回压缩视图，不改原始消息）
    # 注意：此函数在 agent.py 调用 API 前单独调用，不在这里

    # 第 5 层：全量摘要（仅当前四层不够用时）
    if estimate_tokens(state.messages) > threshold - snip_tokens_freed:
        compact_messages(state.messages, config)
```

第 4 层在 `agent.py` 中独立于 `maybe_compact()` 调用，紧贴 API 调用前执行。

## 四、System Prompt 重构（对齐缓存优化与行为约束）

改动位置：`context.py` 的 `build_system_prompt()`。

### 改动一：加入静态 / 动态分割线

将系统提示内容分成两部分，中间插入分割标记：

```text
SYSTEM_PROMPT_DYNAMIC_BOUNDARY
```

分割线上方（对所有用户完全相同，可被 Prompt Cache 共享）：

- 角色定义（“你是一个交互式 agent，帮助用户完成软件工程任务”）
- 安全红线（不生成 / 猜测 URL；安全测试允许范围与禁止范围）
- 行为准则（修改代码前先阅读；少即是多；失败先诊断再换方案）
- 操作安全（可逆性 × 影响范围两维度判断风险；授权仅对指定范围有效）
- 工具使用指南（有专用工具时不用 Bash；`Read` / `Edit` / `Write` / `Glob` / `Grep` 优先）
- Git 安全协议（不修改 git config；不跳过 hooks；失败后创建新 commit 而非 `--amend`）
- 输出风格约束（见改动二）

分割线下方（因人而异，实时生成）：

- 环境信息（工作目录、操作系统、Shell 类型、模型、知识截止日期）
- `CLAUDE.md` 内容
- 记忆索引
- MCP 配置说明

### 改动二：加入输出风格约束（写入静态区）

## 输出风格

直奔重点。工具调用之间的文字不超过 25 个词。最终回复不超过 100 个词。
先给出答案或行动，而不是推理过程。不要复述用户说过的话。

## 五、记忆系统重构（对齐 Claude Code 检索架构）

当前 pycc 把记忆索引直接注入系统提示，Claude Code 用 Sonnet 并行检索按需加载，两者设计哲学完全不同。需要以下改动：

### 改动一：类型约束为严格四类

`memory/store.py` 中 `MemoryEntry` 的 `type` 字段限制为：

```python
MEMORY_TYPES = {"user", "feedback", "project", "reference"}
```

- `user`：用户画像（角色、偏好、知识水平）
- `feedback`：行为反馈（该做 / 不该做什么），必须同时记录 `why` 和 `how_to_apply` 字段
- `project`：项目动态，相对日期（如“周四”）存入时强制转换为绝对日期（如 `2026-04-17`）
- `reference`：外部指针（去哪找什么信息）

删除 `confidence`、`conflict_group`、`source`、`last_used_at` 字段（pycc 自行扩展的，Claude Code 无此设计）。

### 改动二：新增排除规则

在 `MemorySave` 工具的 prompt/description 中明确禁止存储以下内容：

- 代码结构、文件位置、项目架构（可通过 `grep` / `glob` 实时获取）
- git 历史和最近改动（`git log` / `git blame` 是权威来源）
- `CLAUDE.md` 里已有的内容
- 临时任务状态和当前对话上下文

### 改动三：Sonnet 并行检索替换直接注入

新增 `memory/retriever.py`：

- `scan_memory_headers(memory_dir) -> list[MemoryHeader]`
  遍历所有 `.md` 记忆文件，只读每个文件前 30 行提取 frontmatter（`name`、`description`、`type`、修改时间），按修改时间倒序，最多 200 个
- `select_relevant_memories(query, headers, tool_in_use) -> list[str]`
  把 headers 拼成清单，连同用户当前输入发给 Sonnet（`claude-3-5-sonnet`），要求返回最相关的最多 5 个文件名；若用户正在使用某工具，过滤掉该工具的使用文档类记忆，但保留其已知 bug 类记忆；Sonnet 的 `max_tokens` 设为 256（只返回文件名列表）
- `load_selected_memories(filenames) -> str`
  读取选中文件的完整内容，拼装后作为 `<system-reminder>` 注入

执行时机：在 `pycc.py` 的 `run_query()` 中，用户消息提交后立刻启动记忆检索（用 `threading.Thread` 与主模型 API 调用并行），主模型响应回来前记忆选择已完成，结果注入下一轮系统提示。

### 改动四：陈旧度检测

`memory/retriever.py` 中新增 `memory_freshness_warning(mtime) -> str`：

```python
def memory_freshness_warning(mtime: float) -> str:
    days = (time.time() - mtime) / 86400
    if days <= 1:
        return ""
    return (
        f"此记忆已有 {int(days)} 天。记忆是某时间点的观察，"
        f"关于代码行为或文件位置的断言可能已过时，引用前请对照当前代码验证。"
    )
```

加载每条记忆内容时附加此警告。

系统提示注入方式变更：

- `MEMORY.md` 索引仍注入静态区下方（让模型知道有哪些记忆）
- 各条记忆的完整内容改为由 Sonnet 检索后按需注入，不再全量注入

## 六、Plan Mode 每 5 轮提醒注入

改动位置：`agent.py` 的主循环。

在 `permission_mode == "plan"` 时，每 5 轮（`turn_count % 5 == 0`）向消息列表注入一条 `system-reminder`：

```python
if config.get("permission_mode") == "plan" and state.turn_count % 5 == 0:
    state.messages.append({
        "role": "user",
        "content": "[System Reminder] You are currently in Plan Mode. "
                   "You may only use read-only tools. Do not write files or execute commands."
    })
```

注入后在下一轮模型响应前移除（避免污染历史），或标记为临时消息。

## 七、Bash 语法级安全分析模块

改动位置：`agent.py` 的 `_is_safe_bash()` / `tools.py` 的 Bash 工具。

现状：白名单关键词匹配（`ls`、`cat`、`git log` 等）。

改为语法级分析，新增 `security/bash_analyzer.py`：

检测以下危险模式（不依赖关键词，而是解析命令结构）：

- 命令注入：`;`、`&&`、`||`、`$()` 拼接执行其他命令
- 路径逃逸：`../../` 访问工作目录之外的路径
- 危险操作：`rm -rf /`、`chmod 777`、`> /dev/sda` 等破坏性写入
- 网络外传：`curl ... | bash`、`wget` 下载后执行
- 环境变量篡改：修改 `PATH`、`LD_PRELOAD` 等

分析结果返回 `BashRiskLevel`：`safe`（自动放行）/ `warn`（提示用户）/ `dangerous`（要求确认）。在 `_check_permission()` 中替换原有白名单逻辑，调用此分析器。

## 八、改写后保留的完整特性清单

以下是对齐完成后 pycc 应有的功能（与 Claude Code 一致）：

| 模块 | 保留 / 新增内容 |
| --- | --- |
| Tool registry | 核心工具：`Read` / `Write` / `Edit` / `Bash` / `Glob` / `Grep` / `WebFetch` / `WebSearch` / `TodoWrite` / `NotebookEdit` / `GetDiagnostics` / `AskUserQuestion` / `EnterPlanMode` / `ExitPlanMode`；记忆工具：`MemorySave` / `MemoryDelete` / `MemorySearch` / `MemoryList`；Multi-agent 工具：`Agent` / `SendMessage` / `CheckAgentResult` / `ListAgentTasks` / `ListAgentTypes`；Skill 工具：`Skill` / `SkillList`；MCP 动态工具 |
| 权限系统 | `auto` / `manual` / `accept-all` / `plan` 四模式；可逆性 × 影响范围两维度风险判断；授权范围一次性有效不可蔓延 |
| Bash 安全模块 | 语法级分析（命令注入、路径逃逸、危险操作、网络外传、环境变量篡改）；三级风险：`safe` 自动放行 / `warn` 提示 / `dangerous` 要求确认 |
| Plan Mode | `EnterPlanMode` / `ExitPlanMode` 工具；plan 阶段只读锁定；每 5 轮自动注入提醒防模型走神；用户确认后解除限制 |
| 外部 Hooks 系统 | `settings.json` 配置（项目级优先于全局）；五类事件：`PreToolUse` / `PostToolUse` / `Stop` / `Notification` / `PreCompact`；shell 命令执行，JSON stdin/stdout；`PreToolUse` 支持 `block` / `approve` / `ask` 决策；非零退出码只警告不阻断 |
| System Prompt | `__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__` 静态 / 动态分割；静态区：角色定义、安全红线、行为准则、操作安全、工具使用指南、Git 安全协议、输出风格约束（工具调用间 ≤ 25 词，最终回复 ≤ 100 词）；动态区：环境信息、`CLAUDE.md`、记忆索引、MCP 配置；三级 Prompt Cache |
| Skill 系统 | Markdown 定义，inline 执行（移除 fork 模式）；`triggers` / `tools` 白名单 / 参数替换；user / project 两级加载，project 优先；斜杠命令调用 |
| Memory 系统 | 严格四类型：`user` / `feedback` / `project` / `reference`；`feedback` 强制记 `why` + `how_to_apply`；`project` 日期绝对化；明确排除清单；`MEMORY.md` 索引（≤ 200 行 / 25KB）注入系统提示；Sonnet 并行检索（只读前 30 行 header，最多选 5 条，零额外延迟）；陈旧度检测（>1 天自动附加过时警告）；user / project 双作用域 |
| Multi-agent | `Agent` 工具派发子任务；子 agent 在独立 context window 运行，结果摘要返回；git worktree 级别工作区隔离；`SendMessage` / `CheckAgentResult` 跨 agent 异步通信；5 种内置 agent 类型 |
| MCP 集成 | `stdio transport`，`JSON-RPC 2.0`；动态工具注册为 `mcp__<server>__<tool>`；server 状态追踪 |
| `CLAUDE.md` 注入 | 全局（`~/.claude/CLAUDE.md`）+ 项目级（向上查找），注入动态区 |
| 上下文五层压缩 | 第 1 层：大结果存磁盘（>50KB 存磁盘留 2KB 预览，消息级 200KB 上限）；第 2 层：砍掉远古消息（移除整条 + 边界标记 + 释放量通知第 5 层）；第 3 层：Micro-compact（可重获取工具清理，保留最近 5 个，Agent/Task 结果永不清理，缓存过期触发）；第 4 层：Context Collapse 读时投影（90% / 95% 双阈值，不修改原始消息）；第 5 层：全量摘要（结构化九维 prompt + Post-Compact Restoration 最多 5 文件 50K token + 熔断） |
| Task 系统 | 简单列表（移除 DAG），`pending` / `in_progress` / `completed` / `cancelled` 四状态，`TaskCreate` / `TaskUpdate` / `TaskGet` / `TaskList` |
| 上下文构建 | git 信息（branch / status / 近期 commit）；平台信息；memory 索引注入动态区；静态 / 动态分割线 |

---

## 组 E：Bug 修复规格（对齐 21 步重构后的残留问题）

**背景**：21 步重构完成后项目无法运行，发现以下 6 类残留问题需修复。

### E1. skill/builtin.py — 删除已失效的 `context` 参数

**问题根因**：Step 6 从 `SkillDef` 移除了 `context` 字段，但 `skill/builtin.py` 仍在两处 `SkillDef(...)` 调用中传入 `context="inline"`，导致 `TypeError` 启动即崩溃。

**修复规格**：从 `skill/builtin.py` 两处 `register_builtin_skill(SkillDef(...))` 调用中删除 `context="inline"` 关键字参数。不修改其他字段。

### E2. pyproject.toml — 包列表与实际目录对齐

**修复规格**：
- `packages` 列表：删除 `plugin`、`voice`、`checkpoint`；添加 `hooks`、`security`
- `py-modules`：删除 `cloudsave`（已删文件）
- `[project.optional-dependencies]`：删除 `voice = ["sounddevice"]`
- `requires-python = ">=3.10"` 确认存在
- dev 依赖中添加 `pytest>=7.0`

### E3. 删除引用已删模块的测试文件

**修复规格**：物理删除以下 4 个文件：
- `tests/test_checkpoint.py`
- `tests/test_plugin.py`
- `tests/test_voice.py`
- `tests/e2e_checkpoint.py`

### E4. tests/test_compaction.py — 更新为新的 snip_old_messages 接口

**修复规格**：
- 将 `from compaction import snip_old_tool_results` 改为 `from compaction import snip_old_messages`
- 新函数签名：`snip_old_messages(messages, preserve_last_n_turns=6) -> int`（返回删除的消息数）
- 行为：整条消息删除，不截断内容；删除最旧的消息直到满足保留条件
- 重写测试类名为 `TestSnipOldMessages`，验证消息删除而非内容截断

### E5. tests/test_task.py — 删除 DAG 字段相关测试

**修复规格**：
- 从 Task 构造调用中删除 `blocks=[...]`、`blocked_by=[...]` 参数
- 删除方法：`test_update_add_blocks`、`test_update_add_blocked_by`
- 删除任何调用 `add_blocked_by`、`add_blocks` 参数的代码
- 保留所有非 DAG 相关测试不变

### E6. tests/test_tool_registry.py — 更新截断测试为磁盘卸载语义

**修复规格**：
- 当前磁盘卸载阈值：`DISK_OFFLOAD_THRESHOLD = 50_000`
- 100 字符的结果不会触发任何截断或卸载，应直接透传
- 更新 `test_output_truncation`：验证 <50K 的结果原样返回，不含 `"truncated"` 字样
- 如需测试磁盘卸载路径，mock `len(result) > 50_000` 的情况

### E7. tests/test_memory.py — 修复已重命名的符号引用

**修复规格**：
- 检查 `get_project_memory_dir` → 应改为 `get_memory_dir`（如有）
- 检查 `confidence`、`check_conflict` 等 Step 7 移除的字段（如有）
- 其余测试保持不变

### E8. pycc.py — Python 版本保护

**修复规格**：在 `pycc.py` 顶部 `from __future__` 之后、其他 import 之前插入：
```python
import sys
if sys.version_info < (3, 10):
    sys.exit(f"Pycc requires Python ≥ 3.10. Detected: {sys.version}")
```

### E9. README.md — 删除已删功能描述

**修复规格**：
- 删除或替换以下功能的所有描述：Checkpoint、Plugin、Voice、Brainstorm、Proactive、CloudSave、SSJ Worker
- 更新功能列表，添加：外部 Hooks 系统、Bash 安全分析器、5 层上下文压缩、Memory Sonnet 检索、Plan Mode、结构化 System Prompt
