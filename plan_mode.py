import os

def enter_plan_mode(config: dict, task_description: str = "") ->tuple[str, str]:
    if is_plan_mode(config):
        message = "已经在计划模式中！"
        return [message, get_plan_file(config)]
    
    # 生成计划文件路径
    session_id = config.get("_session_id", "default")
    base_dir = ".nano_claude/plans"
    plan_path = os.path.join(base_dir, f"{session_id}.md")
    # 自动创建目录（不存在就创建）
    os.makedirs(base_dir, exist_ok=True)
    # 写入标题和任务
    with open(plan_path, "w", encoding="utf-8") as f:
            f.write(f"# Plan for session: {session_id}\n\n")
            if task_description:
                f.write(f"## Task\n{task_description}\n\n")
    # 保存之前的权限模式
    config["_plan_prev_permission_mode"] = config.get("permission_mode")
    
    # 开启计划模式
    config["_plan_mode_active"] = True
    config["_plan_file"] = str(plan_path)
    config["_plan_task"] = task_description
    
    return ("成功进入计划模式！", str(plan_path))

def exit_plan_mode(config: dict, require_nonempty: bool = True) -> tuple[str, str]:
    if not is_plan_mode(config):
        return ["未在计划模式中！", ""]
    
    plan_path = get_plan_file(config)
    plan_content = read_plan_file(plan_path)
   
    # 如果计划md为空 → 直接返回错误，不退出
    if plan_content.startswith("Error:"):
        return plan_content, ""
    
    # 关闭计划模式
    config["_plan_mode_active"] = False
    config.pop("_plan_task", None)

    return ("已退出计划模式！", plan_content)

#---------辅助函数----------
def is_plan_mode(config: dict) -> bool:
    return bool(config.get("_plan_mode_active", ""))

def get_plan_file(config: dict) -> str:
    return config.get("_plan_file", "")

def read_plan_file(plan_path: str) -> str:
    """
    读取 plan 文件内容
    - 如果文件不存在 → 返回空
    - 如果 require_non_empty=True 且内容为空 → 返回错误消息
    - 否则返回真实内容
    """
    # 文件不存在 → 空内容
    if not os.path.exists(plan_path):
        content = ""
    else:
        # 读取内容并去除首尾空白
        with open(plan_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

    # 内容真的为空 → 返回错误信息
    if not content:
        return "Error: Plan file is empty. Please write your plan first."

    # 正常返回内容
    return content  