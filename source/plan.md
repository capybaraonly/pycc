# 详细执行计划

**参考文档**：`source/rerwrite.md`（改写目标与规格）
**项目路径**：`/Users/capybara/Documents/pycc`（即 pycc 项目，rerwrite.md 里写的 `pycc-main` 路径已过时）

---

## 执行原则

- 每步独立可完成，不跨步骤依赖未完成的代码
- 每步开始前先读相关文件，再动手
- 步骤间可单独开新窗口，窗口内上下文可控

---

## ✅ Step 1：删除整目录级功能（纯删除，最安全）

**目标**：物理删除与 Claude Code 无关的整目录，不动 pycc.py。

**操作**：
```
rm -rf checkpoint/
rm -rf plugin/
rm -rf voice/
rm -rf video/
rm -rf demos/         # 如存在
rm demo.py            # 如存在
rm cloudsave.py
```

**验证**：`ls` 确认目录已消失，项目可 import（`python -c "import agent"`）。

---

## ✅ Step 2：清理 pycc.py —— 删除被删目录的调用（上半部分）

**目标**：移除 pycc.py 中所有引用已删模块的代码，防止 ImportError。

**先读文件**：`pycc.py`（建议分段读，每次 200 行，从头到尾扫一遍找 import 和引用）

**具体删除内容**：
1. 所有 `from checkpoint` / `import checkpoint` 相关 import
2. 所有 `from plugin` / `import plugin` 相关 import
3. 所有 `from voice` / `import voice` 相关 import
4. 所有 `from video` / `import video` 相关 import
5. `from cloudsave import` 相关 import
6. `import demo` 相关 import
7. 以下函数整体删除（搜索函数定义位置后删除）：
   - `cmd_checkpoint()` / `cmd_rewind()`
   - `cmd_plugin()`
   - `cmd_voice()`
   - `cmd_video()`
   - `cmd_cloudsave()` / `_build_session_data()`
   - `cmd_brainstorm()` / `_generate_personas()` / `_interactive_ollama_picker()` / `_save_synthesis()`
   - `cmd_ssj()`
   - `cmd_worker()`
   - `cmd_proactive()` / `_proactive_watcher_loop()`
8. slash 命令分发处删除对应的 `/checkpoint`、`/rewind`、`/plugin`、`/voice`、`/video`、`/cloudsave`、`/brainstorm`、`/ssj`、`/worker`、`/proactive` 分支
9. 退出时自动 cloudsave 上传逻辑（约原第 1209-1221 行区域，搜索 `cloudsave_auto` 或 `_build_session_data`）
10. 后台线程启动 proactive watcher 的代码（搜索 `_proactive_thread` 或 `threading.Thread` + proactive）

**验证**：`python -m py_compile pycc.py` 无语法错误。

---

## ✅ Step 3：清理 tools.py —— 删除 Telegram 和 checkpoint 钩子

**先读文件**：`tools.py`（完整读）

**操作**：
1. 删除文件底部 `from checkpoint.hooks import install_hooks as _install_checkpoint_hooks` 及 `_install_checkpoint_hooks()` 调用
2. 删除 Telegram 相关工具定义（搜索 `telegram` / `Telegram`，删除对应 `ToolDef` 和实现函数）

**验证**：`python -m py_compile tools.py`

---

## ✅ Step 4：简化 task/ —— 删除 DAG 字段

**先读文件**：`task/types.py`、`task/store.py`

**操作**：
1. `task/types.py`：从 `Task` dataclass 删除 `blocks: list` 和 `blocked_by: list` 字段
2. `task/store.py`：删除依赖解析逻辑（搜索 `blocks`、`blocked_by`，删除相关函数和代码段）

**验证**：`python -m py_compile task/types.py task/store.py`

---

## ~~Step 5：简化 providers.py —— 只保留 Anthropic~~ ⏭️ 跳过

> **决策变更（2026-04-14）**：保留多 provider 支持，用户仍需要 OpenAI / Ollama 等接入能力。providers.py 不做修改。

---

## ✅ Step 6：简化 skill/ —— 删除 fork 模式；简化 memory/ 字段

**先读文件**：`skill/executor.py`、`skill/loader.py`、`memory/store.py`、`memory/consolidator.py`

**操作 - skill**：
1. `skill/executor.py`：删除 `context == "fork"` 分支（约 34、65 行区域），只保留 inline 执行
2. `skill/loader.py`：删除 `SkillDef` 中的 `context` 字段（或设为被忽略）

**操作 - memory**：
1. `memory/store.py`：从 `MemoryEntry` 删除字段：`confidence`、`source`、`last_used_at`、`conflict_group`
2. 删除文件 `memory/consolidator.py`（整文件）
3. 删除文件 `memory/scan.py`（如仅服务于 consolidator，则整文件删除；否则先读再判断）
4. `memory/` 下其他文件：搜索 `consolidat` / `confidence` / `conflict_group`，删除相关引用

**验证**：`python -m py_compile skill/executor.py memory/store.py`

---

## ✅ Step 7：清理 config.py

**先读文件**：`config.py`

**删除以下 key 的默认值和相关代码**（搜索 key 名）：
- `_proactive_enabled`、`_proactive_interval`、`_last_interaction_time`、`_proactive_thread`、`_run_query_callback`
- `gist_token`、`cloudsave_auto`、`cloudsave_last_gist_id`
- checkpoint 相关 key（如有）

**保留**：`model`、`max_tokens`、`permission_mode`、`thinking_budget`、`max_agent_depth`、API key 相关

**验证**：`python -m py_compile config.py`

---

## ✅ Step 8：新建 hooks/ 目录（Hooks 系统核心）

**目标**：新建完整的外部 hooks 系统。参考 rerwrite.md §二 的规格。

**新建文件**（4 个）：

### `hooks/types.py`
```python
from dataclasses import dataclass, field
from typing import Literal

@dataclass
class HookCommand:
    type: str          # "command"
    command: str

@dataclass
class HookMatcher:
    matcher: str       # "" 或 "*" 匹配所有，否则 startswith 匹配
    hooks: list[HookCommand]

@dataclass
class HooksConfig:
    pre_tool_use: list[HookMatcher] = field(default_factory=list)
    post_tool_use: list[HookMatcher] = field(default_factory=list)
    stop: list[HookMatcher] = field(default_factory=list)
    notification: list[HookMatcher] = field(default_factory=list)
    pre_compact: list[HookMatcher] = field(default_factory=list)

@dataclass
class HookDecision:
    decision: Literal["block", "approve", "ask"] = "ask"
    reason: str = ""
```

### `hooks/loader.py`
- `load_settings_json(cwd: str) -> dict`：从 cwd 向上找 `.claude/settings.json`，合并 `~/.claude/settings.json`（项目级优先）
- `parse_hooks_config(raw: dict) -> HooksConfig`：解析 JSON 的 `hooks` 字段
- `get_hooks_config(cwd: str) -> HooksConfig`：加了 `functools.lru_cache` 的缓存版本

### `hooks/executor.py`
- `run_hook(command: str, stdin_data: dict, timeout: int = 10) -> dict | None`
- 用 `subprocess.run(command, shell=True, input=json.dumps(stdin_data).encode(), capture_output=True, timeout=timeout)`
- 非零退出码：打印警告，返回 None
- 超时/异常：打印警告，返回 None
- 否则：尝试解析 stdout 为 JSON 返回

### `hooks/dispatcher.py`
- `_matches(matcher: str, tool_name: str) -> bool`
- `fire_pre_tool(tool_name, tool_input, session_id, cwd) -> HookDecision`：遍历匹配的 PreToolUse，首个 block 立即返回，有 approve 返回 approve，否则 ask
- `fire_post_tool(tool_name, tool_input, tool_response, session_id, cwd) -> None`
- `fire_stop(stop_reason, session_id, cwd) -> None`
- `fire_notification(message, session_id, cwd) -> None`
- `fire_pre_compact(messages_count, token_count, session_id, cwd) -> None`

### `hooks/__init__.py`
```python
from .dispatcher import fire_pre_tool, fire_post_tool, fire_stop, fire_notification, fire_pre_compact
```

**验证**：`python -c "from hooks import fire_pre_tool"`

---

## ✅ Step 9：集成 hooks 到 agent.py

**先读文件**：`agent.py`（完整读）

**操作**（参考 rerwrite.md §二 Step 2）：

1. 在文件顶部加 import：
   ```python
   from hooks.dispatcher import fire_pre_tool, fire_post_tool, fire_stop
   ```

2. 在工具执行循环中，`_check_permission()` 调用**之前**插入 pre_tool hook：
   ```python
   hook_decision = fire_pre_tool(
       tc["name"], tc.get("input", {}),
       config.get("_session_id", ""), config.get("_cwd", ".")
   )
   if hook_decision.decision == "block":
       yield ToolEnd(tool_call_id=tc["id"], name=tc["name"],
                     result=f"[Blocked by hook: {hook_decision.reason}]", is_error=True)
       continue
   elif hook_decision.decision == "approve":
       permitted = True
   else:
       permitted = _check_permission(tc, config)
       # ... 原有逻辑不变
   ```

3. 工具执行完成、产出 `ToolEnd` 之后插入 post_tool hook：
   ```python
   fire_post_tool(tc["name"], tc.get("input", {}), result_dict,
                  config.get("_session_id", ""), config.get("_cwd", "."))
   ```

4. `TurnDone` 产出后插入 stop hook：
   ```python
   fire_stop(finish_reason, config.get("_session_id", ""), config.get("_cwd", "."))
   ```

**验证**：`python -m py_compile agent.py`

---

## ✅ Step 10：注入 session_id / cwd + Notification hook

**先读文件**：`pycc.py`（找 session 初始化位置，约在 run_query 或 main 入口区域）

**操作**：
1. session 初始化处加入：
   ```python
   import os, uuid
   config.setdefault("_session_id", str(uuid.uuid4()))
   config.setdefault("_cwd", os.getcwd())
   ```
2. 权限询问弹出时（`PermissionRequest` 处理处）加入：
   ```python
   from hooks.dispatcher import fire_notification
   fire_notification(message, config.get("_session_id", ""), config.get("_cwd", "."))
   ```

**验证**：`python -m py_compile pycc.py`

---

## ✅ Step 11：集成 hooks 到 compaction.py（PreCompact hook）

**先读文件**：`compaction.py`（完整读）

**操作**：在 `maybe_compact()` 执行压缩之前插入：
```python
from hooks.dispatcher import fire_pre_compact
fire_pre_compact(
    len(messages),
    estimated_tokens,
    config.get("_session_id", ""),
    config.get("_cwd", "."),
)
```

**验证**：`python -m py_compile compaction.py`

---

## ✅ Step 12：重写压缩第 1 层——大结果存磁盘

**先读文件**：`tool_registry.py`（完整读）

**目标**：替换现有 32000 字符硬截断为磁盘存储 + 2KB 预览。参考 rerwrite.md §三 第 1 层。

**操作**：
1. 在 `execute_tool()` 中，工具返回结果后：
   - 结果超过 ~50KB（50000 字节）：写入 `~/.pycc/tool_results/<session_id>/<tool_use_id>.txt`
   - 上下文中替换为前 2KB 内容 + 说明文字
2. 同一条消息内所有工具结果超 200KB：循环找最大的存磁盘
3. 删除现有 `[:32000]` 或类似的硬截断
4. 添加 `_file_access_log` 记录：每次文件相关工具执行后更新 `config["_file_access_log"][file_path] = time.time()`

**验证**：`python -m py_compile tool_registry.py`

---

## ✅ Step 13：重写压缩第 2 层——移除远古消息

**先读文件**：`compaction.py`（已在 Step 11 读过，此步直接操作）

**目标**：把 `snip_old_tool_results()` 改为直接移除整条消息 + 插入边界标记。

**操作**：
1. 重写 `snip_old_tool_results()` → 改名 `snip_old_messages()`：
   - 找最早的一批完整消息（工具结果消息）
   - 整条删除（不是截断内容）
   - 在删除位置插入：`{"role": "user", "content": "[Earlier conversation history has been removed. N tokens freed.]"}`
   - 返回 freed token 数量（整型）
2. 更新 `maybe_compact()` 调用处使用新函数名和返回值

**验证**：`python -m py_compile compaction.py`

---

## ✅ Step 14：新增压缩第 3 层——Micro-compact

**在 compaction.py 中新增** `micro_compact(messages, config)` 函数：

- 可清理工具集合：`{"Read", "Bash", "Glob", "Grep", "WebFetch", "WebSearch", "Edit", "Write"}`
- 不可清理：`Agent`、Task 相关工具结果永不清理
- 触发条件：`config.get("_last_api_call_time")` 距今超过 60 分钟
- 逻辑：收集所有可清理工具结果，保留最近 5 个，其余内容替换为 `[Old tool result content cleared]`
- 在 `maybe_compact()` 中作为第 3 层调用（第 2 层之后）

另在 `agent.py` 中每次 API 调用前更新 `config["_last_api_call_time"] = time.time()`。

**验证**：`python -m py_compile compaction.py`

---

## ✅ Step 15：新增压缩第 4 层——读时投影 Context Collapse

**在 compaction.py 中新增** `apply_context_collapse(messages, config) -> list`：

- 不修改 `state.messages`，返回压缩视图
- 90% 阈值：对旧消息段做分段摘要（每段独立压缩）
- 95% 阈值：更激进，压缩更多
- 返回的是供本次 API 调用用的消息列表

**在 agent.py 中**，API 调用前单独调用：
```python
messages_for_api = apply_context_collapse(state.messages, config)
# 用 messages_for_api 而非 state.messages 传给 API
```

**验证**：`python -m py_compile compaction.py agent.py`

---

## ✅ Step 16：重写压缩第 5 层——全量摘要

**改动 compaction.py 的 `compact_messages()`**：

1. 删除 `content[:500]` 截断，传完整内容给摘要模型
2. 替换 prompt 为结构化九维摘要（见 rerwrite.md §三 第 5 层）：
   - 用户意图、关键决策、涉及文件及内容、工具执行结果、错误及修复、用户所有消息（不遗漏）、待完成任务、当前工作状态、建议下一步
3. Post-Compact Restoration：
   - 从 `config["_file_access_log"]` 取最近访问的最多 5 个文件
   - 预算 50K token，重新注入上下文
   - 活跃 skill 内容恢复（25K token 预算）
   - plan 文件恢复逻辑保留
4. 新增熔断：连续失败 3 次放弃（`config["_compact_failures"]` 计数）

**验证**：`python -m py_compile compaction.py`

---

## ✅ Step 17：重构 System Prompt（context.py）

**先读文件**：`context.py`（完整读）

**目标**：在 `build_system_prompt()` 中加入静态/动态分割线。参考 rerwrite.md §四。

**操作**：
1. 将系统提示内容分成静态区（`SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 以上）和动态区（以下）：
   - **静态区**（对所有用户相同，可被 Prompt Cache 共享）：
     - 角色定义
     - 安全红线（不生成/猜测 URL；安全测试边界）
     - 行为准则（先读再改；失败先诊断；少即是多）
     - 操作安全（可逆性 × 影响范围判断）
     - 工具使用指南（有专用工具不用 Bash）
     - Git 安全协议
     - 输出风格约束（工具调用间 ≤25 词；最终回复 ≤100 词）
   - **动态区**（实时生成）：
     - 环境信息（cwd、OS、Shell、模型、知识截止日期）
     - `CLAUDE.md` 内容
     - 记忆索引（`MEMORY.md`）
     - MCP 配置说明

**验证**：`python -m py_compile context.py`

---

## ✅ Step 18：重构 memory/ ——严格四类型 + 排除规则

**先读文件**：`memory/store.py`、`memory/tools.py`、`memory/types.py`

**操作**：
1. `memory/store.py` 中 `MemoryEntry`：
   - `type` 限制为 `Literal["user", "feedback", "project", "reference"]`
   - 删除字段：`confidence`、`source`、`last_used_at`、`conflict_group`
   - `feedback` 类型：在工具 description 中要求必须记录 `why` 和 `how_to_apply`
   - `project` 类型：在工具 description 中要求将相对日期转换为绝对日期
2. `memory/tools.py` 中 `MemorySave` 工具的 description 加入排除规则（明确禁止存储代码结构/文件位置/git历史/CLAUDE.md已有内容/临时任务）

**验证**：`python -m py_compile memory/store.py memory/tools.py`

---

## ✅ Step 19：新增 memory/retriever.py —— Sonnet 并行检索

**新建文件 `memory/retriever.py`**：

- `scan_memory_headers(memory_dir) -> list[MemoryHeader]`：
  - 遍历所有 `.md` 记忆文件，只读每个文件前 30 行提取 frontmatter
  - 按修改时间倒序，最多 200 个
- `select_relevant_memories(query, headers, tool_in_use=None) -> list[str]`：
  - 把 headers 拼成清单 + 用户输入发给 `claude-3-5-sonnet`（`max_tokens=256`）
  - 返回最相关的最多 5 个文件名
- `load_selected_memories(filenames, memory_dir) -> str`：
  - 读取选中文件完整内容
  - 对每条附加陈旧度警告（>1 天则警告）
  - 返回拼装好的 `<system-reminder>` 字符串
- `memory_freshness_warning(mtime: float) -> str`（见 rerwrite.md §五 改动四）

**在 pycc.py 中**的 `run_query()` 里：
- 用户消息提交后，用 `threading.Thread` 启动记忆检索（与主模型 API 调用并行）
- 主模型响应前将检索结果注入下一轮系统提示

**验证**：`python -m py_compile memory/retriever.py`

---

## ✅ Step 20：Plan Mode 每 5 轮提醒注入

**先读文件**：`agent.py`（已熟悉）

**在 agent.py 主循环中**（参考 rerwrite.md §六）：
```python
if config.get("permission_mode") == "plan" and state.turn_count % 5 == 0 and state.turn_count > 0:
    state.messages.append({
        "role": "user",
        "content": "[System Reminder] You are currently in Plan Mode. "
                   "You may only use read-only tools. Do not write files or execute commands."
    })
    # 标记为临时消息，在下一轮响应后移除
```

实现临时消息移除：在 API 响应后，移除最后一条带 `[System Reminder]` 标记的 user 消息（如果存在）。

**验证**：`python -m py_compile agent.py`

---

## ✅ Step 21：Bash 语法级安全分析模块

**新建文件 `security/bash_analyzer.py`** 和 `security/__init__.py`：

参考 rerwrite.md §七，检测以下危险模式：
- 命令注入：`;`、`&&`、`||`、`$()` 拼接（注意：需允许 git 等合法使用）
- 路径逃逸：`../../` 访问工作目录外
- 危险操作：`rm -rf /`、`chmod 777`、`> /dev/sda` 等
- 网络外传：`curl ... | bash`、`wget` 下载后执行
- 环境变量篡改：修改 `PATH`、`LD_PRELOAD`

返回 `BashRiskLevel`：`safe`（自动放行）/ `warn`（提示用户）/ `dangerous`（要求确认）

**在 agent.py / tools.py 的 `_check_permission()`** 中替换原有白名单逻辑，调用此分析器。

**验证**：`python -m py_compile security/bash_analyzer.py`

---

## 最终验证

完成所有步骤后：
```bash
python -m py_compile pycc.py agent.py compaction.py context.py tools.py tool_registry.py config.py providers.py
python -c "from hooks import fire_pre_tool; from memory.retriever import scan_memory_headers; from security.bash_analyzer import BashRiskLevel"
# 如有测试文件：
python -m pytest tests/ -x -q
```

---

## 步骤依赖关系

```
Step 1-3 → Step 4-7（并行）
Step 8 → Step 9 → Step 10 → Step 11（hooks 链条，需顺序）
Step 12 → Step 13 → Step 14 → Step 15 → Step 16（压缩五层，需顺序）
Step 17（独立）
Step 18 → Step 19（memory，需顺序）
Step 20（独立，依赖 Step 9 完成）
Step 21（独立）
```

可以并行开展的分组：
- **组 A（删除清理）**：Step 1 → Step 2 → Step 3 → Step 4 → Step 5 → Step 6 → Step 7
- **组 B（Hooks 系统）**：Step 8 → Step 9 → Step 10 → Step 11（需 A 完成后开始）
- **组 C（压缩重写）**：Step 12 → Step 13 → Step 14 → Step 15 → Step 16（可与 B 并行）
- **组 D（其余独立）**：Step 17、Step 18 → Step 19、Step 20、Step 21（可与 B/C 并行）

---

## 组 E：Bug 修复（修复 21 步重构后的残留问题）

**背景**：21 步重构代码完成后，项目无法运行。发现 6 类问题：启动崩溃、测试引用已删模块、pyproject.toml 残留、README 过时、Python 版本无保护。

---

## ✅ E1（关键）：修复启动崩溃 — `skill/builtin.py` 传递已删除的 `context` 参数

**问题**：`skill/builtin.py` 在两处 `register_builtin_skill(SkillDef(..., context="inline", ...))` 调用中传入了 `context="inline"`，但 Step 6 已从 `SkillDef` 中移除了 `context` 字段，导致 `TypeError: SkillDef.__init__() got an unexpected keyword argument 'context'`。

**操作**：
- 读 `skill/builtin.py`，找到两处 `context="inline"` 参数，删除它们

**验证**：
```bash
/opt/miniconda3/bin/python3.13 -c "from skill.builtin import register_all_builtins; print('OK')"
```

---

## ✅ E2：修复 `pyproject.toml` — 删除已不存在的包，添加新包

**问题**：
- `packages` 列表仍含已删除的 `plugin`、`voice`、`checkpoint`
- `py-modules` 仍含已删除的 `cloudsave`
- 缺少新增的 `hooks`、`security` 包
- `[project.optional-dependencies]` 中仍有 `voice = ["sounddevice"]`

**操作**：
- 读 `pyproject.toml`
- 从 `packages` 删除 `{include = "plugin"}`、`{include = "voice"}`、`{include = "checkpoint"}`
- 从 `py-modules` 删除 `"cloudsave"`（如有）
- 添加 `{include = "hooks"}`、`{include = "security"}` 到 packages
- 删除 `voice = ["sounddevice"]` 可选依赖
- 在 `[project.optional-dependencies]` 或 `[project]` 的 dev-dependencies 中添加 `pytest`

**验证**：
```bash
/opt/miniconda3/bin/python3.13 -m pip install -e . --dry-run 2>&1 | head -20
```

---

## ✅ E3：删除无效测试文件（引用已删模块）

**问题**：以下测试文件 import 已删除的模块，会导致 pytest 收集阶段崩溃：
- `tests/test_checkpoint.py` → `import checkpoint.store`, `checkpoint.hooks`
- `tests/test_plugin.py` → `import plugin`
- `tests/test_voice.py` → `import voice`
- `tests/e2e_checkpoint.py` → `import checkpoint.store`, `checkpoint.hooks`

**操作**：
```bash
rm tests/test_checkpoint.py tests/test_plugin.py tests/test_voice.py tests/e2e_checkpoint.py
```

**验证**：
```bash
ls tests/
```

---

## ✅ E4：修复 `tests/test_compaction.py` — 更新为新的 `snip_old_messages` 接口

**问题**：
- `from compaction import snip_old_tool_results` — 函数已重命名为 `snip_old_messages`，签名完全不同
- `TestSnipOldToolResults` 类测试旧的截断（truncation）行为；新函数改为整条消息删除

**操作**：
- 读 `tests/test_compaction.py` 和 `compaction.py`（确认新签名）
- 将 import 改为 `from compaction import snip_old_messages`
- 重写 `TestSnipOldToolResults` → `TestSnipOldMessages`，测试消息删除行为而非截断

**验证**：
```bash
/opt/miniconda3/bin/python3.13 -m pytest tests/test_compaction.py -x -q 2>&1 | tail -20
```

---

## ✅ E5：修复 `tests/test_task.py` — 删除 DAG 相关测试

**问题**：
- Task 构造函数中的 `blocks=["2"]`, `blocked_by=["1"]` 字段已删除（Step 4）
- `test_update_add_blocks`、`test_update_add_blocked_by` 测试已删除的功能
- `_task_update("2", add_blocked_by=["1"])` 调用使用已删除的参数

**操作**：
- 读 `tests/test_task.py`
- 删除所有引用 `blocks`、`blocked_by`、`add_blocks`、`add_blocked_by` 的测试方法和构造参数

**验证**：
```bash
/opt/miniconda3/bin/python3.13 -m pytest tests/test_task.py -x -q 2>&1 | tail -20
```

---

## ✅ E6：修复 `tests/test_tool_registry.py` — 更新输出截断测试

**问题**：`test_output_truncation` 使用 `max_output=40` 参数对 100 字符结果测试截断，但新的磁盘卸载逻辑仅在 `len(result) > 50_000` 时触发，100 字符的结果根本不会被截断或卸载，测试期望 `"truncated" in result` 会失败。

**操作**：
- 读 `tests/test_tool_registry.py` 和 `tool_registry.py`（确认磁盘卸载阈值）
- 更新 `test_output_truncation`：验证小结果（<50K）直接透传，不被截断
- 可选：添加一个磁盘卸载路径的 mock 测试

**验证**：
```bash
/opt/miniconda3/bin/python3.13 -m pytest tests/test_tool_registry.py -x -q 2>&1 | tail -20
```

---

## ✅ E7：检查并修复 `tests/test_memory.py`

**问题**：可能存在 `get_project_memory_dir` 引用（已重命名为 `get_memory_dir`）或其他已更名符号。

**操作**：
- 读 `tests/test_memory.py`
- 搜索 `get_project_memory_dir`、`confidence`、`check_conflict` 等已删除的符号
- 按需修复

**验证**：
```bash
/opt/miniconda3/bin/python3.13 -m pytest tests/test_memory.py -x -q 2>&1 | tail -20
```

---

## ✅ E8：在入口处添加 Python 版本保护 + 修复 pytest 可用性

**问题**：
- 系统 Python 是 3.9.6，项目需要 ≥ 3.10（使用了 `match`/`case`、`X | Y` 类型联合等语法）
- 当前没有明确的版本检查，用系统 Python 运行时报语法错误
- `pyproject.toml` 中没有 `pytest` 作为开发依赖

**操作**：
- 在 `pycc.py` 入口最顶部（`__future__` import 之后）添加版本检查：
  ```python
  import sys
  if sys.version_info < (3, 10):
      sys.exit("Pycc requires Python 3.10+. Detected: " + sys.version)
  ```
- 在 `pyproject.toml` 的 `requires-python` 字段确认为 `">=3.10"`
- 在开发依赖中添加 `pytest>=7.0`

**验证**：
```bash
python -c "import pycc" 2>&1  # 应提示版本错误（系统 Python 3.9）
/opt/miniconda3/bin/python3.13 -c "import sys; print(sys.version)"
```

---

## ✅ E9：更新 README.md — 删除已删功能的描述

**问题**：README 仍描述已删除的功能（checkpoint、plugin、voice、brainstorm、proactive、cloudsave、SSJ worker）。

**操作**：
- 读 `README.md`
- 删除或替换以下内容的描述段落：
  - Checkpoint / 会话恢复
  - Plugin 系统
  - Voice / 语音模式
  - Brainstorm 模式
  - Proactive / 主动模式
  - CloudSave / SSJ Worker
- 更新功能列表，反映当前实际功能（Hooks、Security Analyzer、5 层压缩、Memory 检索、Plan Mode 等）

**验证**：目视确认 README 中无已删除功能的描述。

---

## 最终全量验证（组 E 完成后）

```bash
cd /Users/capybara/Documents/pycc

# 1. 启动无崩溃
/opt/miniconda3/bin/python3.13 -c "
from skill.builtin import register_all_builtins
from hooks.dispatcher import fire_pre_tool
from memory.retriever import scan_memory_headers
from security.bash_analyzer import BashRiskLevel
print('All imports OK')
"

# 2. 语法检查
/opt/miniconda3/bin/python3.13 -m py_compile pycc.py agent.py compaction.py context.py tools.py tool_registry.py config.py providers.py

# 3. 测试套件
/opt/miniconda3/bin/python3.13 -m pytest tests/ -x -q --ignore=tests/e2e_checkpoint.py 2>&1 | tail -30
```

---

## 步骤依赖关系（组 E）

```
E1（启动崩溃）→ 最优先，独立
E2（pyproject）→ 独立
E3（删除测试）→ 独立
E4（test_compaction）→ 独立
E5（test_task）→ 独立
E6（test_tool_registry）→ 独立
E7（test_memory）→ 独立
E8（版本保护）→ 独立
E9（README）→ 独立，可最后做
```

所有步骤彼此独立，可按任意顺序执行。建议顺序：E1 → E2 → E3 → E4 → E5 → E6 → E7 → E8 → E9。
