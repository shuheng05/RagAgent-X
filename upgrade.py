import os
import sys
import ctypes
import shutil
import locale
import logging
import platform
import subprocess
import time
from datetime import datetime
from merge_configs import merge_configs, compare_configs

USER_CONF = "conf.yaml"
BACKUP_CONF = "conf.yaml.backup"
CURRENT_SCRIPT_VERSION = "0.2.0"


# Remove Colors class and configure logging
def configure_logging():
    if not os.path.exists("logs"):
        os.makedirs("logs")
    log_filename = f"./logs/upgrade_{datetime.now().strftime('%Y-%m-%d-%H-%M')}.log"
    logger = logging.getLogger("upgrade")
    logger.setLevel(logging.DEBUG)

    # File handler (no colors)
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("[%(asctime)s][%(levelname)s] %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Colored console handler
    class ColoredFormatter(logging.Formatter):
        COLORS = {
            logging.DEBUG: "\033[96m",  # cyan
            logging.INFO: "\033[92m",  # green
            logging.WARNING: "\033[93m",  # yellow
            logging.ERROR: "\033[91m",  # red
            logging.CRITICAL: "\033[95m",  # magenta
        }
        RESET = "\033[0m"

        def format(self, record):
            color = self.COLORS.get(record.levelno, self.RESET)
            message = super().format(record)
            return f"{color}{message}{self.RESET}"

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.DEBUG)
    stream_formatter = ColoredFormatter("[%(levelname)s] %(message)s")
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)

    return logger


# Language dictionaries and other constants
TEXTS = {
    "zh": {
        "welcome_message": f"Auto-Upgrade Script {CURRENT_SCRIPT_VERSION}\nOpen-LLM-VTuber 升级脚本 - 此脚本仍在实验阶段，可能无法按预期工作。",
        "lang_select": "请选择语言/Please select language (zh/en):",
        "invalid_lang": "无效的语言选择，使用英文作为默认语言",
        "not_git_repo": "错误：当前目录不是git仓库。请进入 Open-LLM-VTuber 目录后再运行此脚本。\n当然，更有可能的是你下载的Open-LLM-VTuber不包含.git文件夹 (如果你是透过下载压缩包而非使用 git clone 命令下载的话可能会造成这种情况)，这种情况下目前无法用脚本升级。",
        "backup_user_config": "正在备份 {user_conf} 到 {backup_conf}",
        "configs_up_to_date": "[DEBUG] 用户配置已是最新。",
        "no_config": "警告：未找到conf.yaml文件",
        "copy_default_config": "正在从模板复制默认配置",
        "uncommitted": "发现未提交的更改，正在暂存...",
        "stash_error": "错误：无法暂存更改",
        "changes_stashed": "更改已暂存",
        "pulling": "正在从远程仓库拉取更新...",
        "pull_error": "错误：无法拉取更新",
        "restoring": "正在恢复暂存的更改...",
        "conflict_warning": "警告：恢复暂存的更改时发生冲突",
        "manual_resolve": "请手动解决冲突",
        "stash_list": "你可以使用 'git stash list' 查看暂存的更改",
        "stash_pop": "使用 'git stash pop' 恢复更改",
        "upgrade_complete": "升级完成！",
        "check_config": "1. 请检查conf.yaml是否需要更新",
        "resolve_conflicts": "2. 如果有配置文件冲突，请手动解决",
        "check_backup": "3. 检查备份的配置文件以确保没有丢失重要设置",
        "git_not_found": "错误：未检测到 Git。请先安装 Git:\nWindows: https://git-scm.com/download/win\nmacOS: brew install git\nLinux: sudo apt install git",
        "operation_preview": """
此脚本将执行以下操作：
1. 备份当前的 conf.yaml 配置文件
2. 暂存所有未提交的更改 (git stash)
3. 从远程仓库拉取最新代码 (git pull)
4. 尝试恢复之前暂存的更改 (git stash pop)

是否继续？(y/N): """,
        "abort_upgrade": "升级已取消",
        "merged_config_success": "新增配置项已合并:",
        "merged_config_none": "未发现新增配置项。",
        "merge_failed": "配置合并失败: {error}",
        "updating_submodules": "正在更新子模块...",
        "submodules_updated": "子模块更新完成",
        "submodule_error": "更新子模块时出错",
        "no_submodules": "未检测到子模块，跳过更新",
        "env_info": "系统环境: {os_name} {os_version}, Python {python_version}",
        "git_version": "Git 版本: {git_version}",
        "current_branch": "当前分支: {branch}",
        "operation_time": "操作 '{operation}' 完成, 耗时: {time:.2f} 秒",
        "checking_stash": "检查是否有未提交的更改...",
        "detected_changes": "检测到 {count} 个文件有更改",
        "submodule_updating": "正在更新子模块: {submodule}",
        "submodule_updated": "子模块已更新: {submodule}",
        "checking_remote": "正在检查远程仓库状态...",
        "remote_ahead": "本地版本已是最新",
        "remote_behind": "发现 {count} 个新提交可供更新",
        "config_backup_path": "配置备份路径: {path}",
        "start_upgrade": "开始升级流程...",
        "finish_upgrade": "升级流程结束, 总耗时: {time:.2f} 秒",
    },
    "en": {
        "welcome_message": f"Auto-Upgrade Script {CURRENT_SCRIPT_VERSION}\nOpen-LLM-VTuber upgrade script - This script is highly experimental and may not work as expected.",
        "lang_select": "请选择语言/Please select language (zh/en):",
        "invalid_lang": "Invalid language selection, using English as default",
        "not_git_repo": "Error: Current directory is not a git repository. Please run this script inside the Open-LLM-VTuber directory.\nAlternatively, it is likely that the Open-LLM-VTuber you downloaded does not contain the .git folder (this can happen if you downloaded a zip archive instead of using git clone), in which case you cannot upgrade using this script.",
        "backup_user_config": "Backing up {user_conf} to {backup_conf}",
        "configs_up_to_date": "[DEBUG] User configuration is up-to-date.",
        "no_config": "Warning: conf.yaml not found",
        "copy_default_config": "Copying default configuration from template",
        "uncommitted": "Found uncommitted changes, stashing...",
        "stash_error": "Error: Unable to stash changes",
        "changes_stashed": "Changes stashed",
        "pulling": "Pulling updates from remote repository...",
        "pull_error": "Error: Unable to pull updates",
        "restoring": "Restoring stashed changes...",
        "conflict_warning": "Warning: Conflicts occurred while restoring stashed changes",
        "manual_resolve": "Please resolve conflicts manually",
        "stash_list": "Use 'git stash list' to view stashed changes",
        "stash_pop": "Use 'git stash pop' to restore changes",
        "upgrade_complete": "Upgrade complete!",
        "check_config": "1. Please check if conf.yaml needs updating",
        "resolve_conflicts": "2. Resolve any config file conflicts manually",
        "check_backup": "3. Check backup config to ensure no important settings are lost",
        "git_not_found": "Error: Git not found. Please install Git first:\nWindows: https://git-scm.com/download/win\nmacOS: brew install git\nLinux: sudo apt install git",
        "operation_preview": """
This script will perform the following operations:
1. Backup current conf.yaml configuration file
2. Stash all uncommitted changes (git stash)
3. Pull latest code from remote repository (git pull)
4. Attempt to restore previously stashed changes (git stash pop)

Continue? (y/N): """,
        "abort_upgrade": "Upgrade aborted",
        "merged_config_success": "Merged new configuration items:",
        "merged_config_none": "No new configuration items found.",
        "merge_failed": "Configuration merge failed: {error}",
        "updating_submodules": "Updating submodules...",
        "submodules_updated": "Submodules updated successfully",
        "submodule_error": "Error updating submodules",
        "no_submodules": "No submodules detected, skipping update",
        "env_info": "Environment: {os_name} {os_version}, Python {python_version}",
        "git_version": "Git version: {git_version}",
        "current_branch": "Current branch: {branch}",
        "operation_time": "Operation '{operation}' completed in {time:.2f} seconds",
        "checking_stash": "Checking for uncommitted changes...",
        "detected_changes": "Detected changes in {count} files",
        "submodule_updating": "Updating submodule: {submodule}",
        "submodule_updated": "Submodule updated: {submodule}",
        "checking_remote": "Checking remote repository status...",
        "remote_ahead": "Local version is up to date",
        "remote_behind": "Found {count} new commits to pull",
        "config_backup_path": "Config backup path: {path}",
        "start_upgrade": "Starting upgrade process...",
        "finish_upgrade": "Upgrade process completed, total time: {time:.2f} seconds",
    },
}


def get_system_language():
    """Get system language using a combination of methods."""

    os_name = platform.system()

    if os_name == "Windows":
        try:
            # Use Windows API to get the UI language
            windll = ctypes.windll.kernel32
            ui_lang = windll.GetUserDefaultUILanguage()
            lang_code = locale.windows_locale.get(ui_lang)
            if lang_code:
                lang = lang_code.split("_")[0]
                if lang.startswith("zh"):
                    return "zh"
        except Exception:
            pass

    elif os_name == "Darwin":  # macOS
        try:
            # Use defaults command to get the AppleLocale
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleLocale"],
                capture_output=True,
                text=True,
            )
            lang = result.stdout.strip().split("_")[0]
            if lang.startswith("zh"):
                return "zh"
        except Exception:
            pass

    elif os_name == "Linux":
        # Check the LANG environment variable
        lang = os.environ.get("LANG")
        if lang:
            lang = lang.split("_")[0]
            if lang.startswith("zh"):
                return "zh"

    # Fallback to using locale.getpreferredencoding()
    encoding = locale.getpreferredencoding()
    if encoding.lower() in ("cp936", "gbk", "big5"):
        return "zh"

    return "en"


def select_language():
    """Select language based on command-line argument or system language"""
    if len(sys.argv) > 1 and sys.argv[1].lower() in ["zh", "en"]:
        return sys.argv[1].lower()
    return get_system_language()


def run_command(command):
    """Run shell command and return result"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return (
            False,
            f"Command failed with error code {e.returncode}\nError: {e.stderr}",
        )
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def check_git_installed():
    """Check if Git is installed"""
    command = "where git" if sys.platform == "win32" else "which git"
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0
    except subprocess.SubprocessError:
        return False


def log_system_info(logger, lang):
    """Log detailed system information"""
    texts = TEXTS[lang]

    # Log OS info
    os_name = platform.system()
    os_version = platform.version()
    python_version = platform.python_version()
    logger.info(
        texts["env_info"].format(
            os_name=os_name, os_version=os_version, python_version=python_version
        )
    )

    # Log Git version
    success, git_version = run_command("git --version")
    if success:
        logger.info(texts["git_version"].format(git_version=git_version.strip()))

    # Log current branch
    success, branch = run_command("git branch --show-current")
    if success:
        logger.info(texts["current_branch"].format(branch=branch.strip()))


def time_operation(func, *args, **kwargs):
    """Time an operation and return result with timing information"""
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    elapsed = end_time - start_time
    return result, elapsed


def get_submodule_list():
    """Get a list of submodules"""
    if not os.path.exists(".gitmodules"):
        return []

    success, output = run_command("git config --file .gitmodules --get-regexp path")
    if not success:
        return []

    submodules = []
    for line in output.strip().split("\n"):
        if line:
            parts = line.strip().split(" ", 1)
            if len(parts) >= 2:
                submodules.append(parts[1])

    return submodules


def sync_user_config(logger, lang: str = "en") -> None:
    texts = TEXTS[lang]
    default_template = (
        "config_templates/conf.ZH.default.yaml"
        if lang == "zh"
        else "config_templates/conf.default.yaml"
    )

    if os.path.exists(USER_CONF):
        # Compare configurations and only merge if necessary.
        if not compare_configs(
            user_path=USER_CONF, default_path=default_template, lang=lang
        ):
            try:
                # backup first
                backup_path = os.path.abspath(BACKUP_CONF)
                logger.info(
                    texts["backup_user_config"].format(
                        user_conf=USER_CONF, backup_conf=BACKUP_CONF
                    )
                )
                logger.debug(texts["config_backup_path"].format(path=backup_path))
                shutil.copy2(USER_CONF, BACKUP_CONF)

                # merge
                new_keys = merge_configs(
                    user_path=USER_CONF, default_path=default_template, lang=lang
                )
                if new_keys:
                    logger.info(texts["merged_config_success"])
                    for key in new_keys:
                        logger.info(f"  - {key}")
                else:
                    logger.info(texts["merged_config_none"])
            except Exception as e:
                logger.error(texts["merge_failed"].format(error=e))
        else:
            logger.info(texts["configs_up_to_date"])
    else:
        logger.warning(texts["no_config"])
        logger.warning(texts["copy_default_config"])
        shutil.copy2(default_template, USER_CONF)


def has_submodules():
    """Check if the repository has submodules by looking for .gitmodules file"""
    return os.path.exists(".gitmodules")


def perform_upgrade(custom_logger=None):
    logger = custom_logger or configure_logging()
    start_time = time.time()

    logger.info(TEXTS["en"]["welcome_message"])
    lang = select_language()
    texts = TEXTS[lang]

    logger.info(texts["start_upgrade"])
    log_system_info(logger, lang)

    if not check_git_installed():
        logger.error(texts["git_not_found"])
        return

    response = input("\033[93m" + texts["operation_preview"] + "\033[0m").lower()
    if response != "y":
        logger.warning(texts["abort_upgrade"])
        return

    success, error_msg = run_command("git rev-parse --is-inside-work-tree")
    if not success:
        logger.error(texts["not_git_repo"])
        logger.error(f"Error details: {error_msg}")
        return

    # Check for uncommitted changes
    logger.info(texts["checking_stash"])
    success, changes = run_command("git status --porcelain")
    if not success:
        logger.error(f"Failed to check git status: {changes}")
        return

    has_changes = bool(changes.strip())
    if has_changes:
        change_count = len([line for line in changes.strip().split("\n") if line])
        logger.debug(texts["detected_changes"].format(count=change_count))
        logger.warning(texts["uncommitted"])

        operation, elapsed = time_operation(run_command, "git stash")
        success, output = operation
        logger.debug(
            texts["operation_time"].format(operation="git stash", time=elapsed)
        )

        if not success:
            logger.error(texts["stash_error"])
            logger.error(f"Error details: {output}")
            return
        logger.info(texts["changes_stashed"])

    # Check remote status
    logger.info(texts["checking_remote"])
    operation, elapsed = time_operation(run_command, "git fetch")
    success, output = operation
    logger.debug(texts["operation_time"].format(operation="git fetch", time=elapsed))

    if success:
        success, ahead_behind = run_command(
            "git rev-list --left-right --count HEAD...@{upstream}"
        )
        if success:
            ahead, behind = ahead_behind.strip().split()
            if int(behind) > 0:
                logger.info(texts["remote_behind"].format(count=behind))
            else:
                logger.info(texts["remote_ahead"])

    # Pull updates
    logger.info(texts["pulling"])
    operation, elapsed = time_operation(run_command, "git pull")
    success, output = operation
    logger.debug(texts["operation_time"].format(operation="git pull", time=elapsed))

    if not success:
        logger.error(texts["pull_error"])
        logger.error(f"Error details: {output}")
        if has_changes:
            logger.warning(texts["restoring"])
            success, restore_output = run_command("git stash pop")
            if not success:
                logger.error(f"Failed to restore changes: {restore_output}")
        return

    # Update submodules
    submodules = get_submodule_list()
    if submodules:
        logger.info(texts["updating_submodules"])

        # First update all submodules
        operation, elapsed = time_operation(
            run_command, "git submodule update --init --recursive"
        )
        success, output = operation
        logger.debug(
            texts["operation_time"].format(operation="submodule update", time=elapsed)
        )

        if not success:
            logger.error(texts["submodule_error"])
            logger.error(f"Error details: {output}")
        else:
            logger.info(texts["submodules_updated"])

            # Log individual submodule details
            for submodule in submodules:
                logger.debug(texts["submodule_updated"].format(submodule=submodule))
    else:
        logger.info(texts["no_submodules"])

    # Update config
    sync_user_config(logger=logger, lang=lang)  # merge user config

    if has_changes:
        logger.warning(texts["restoring"])
        operation, elapsed = time_operation(run_command, "git stash pop")
        success, output = operation
        logger.debug(
            texts["operation_time"].format(operation="git stash pop", time=elapsed)
        )

        if not success:
            logger.error(texts["conflict_warning"])
            logger.error(f"Error details: {output}")
            logger.warning(texts["manual_resolve"])
            logger.info(texts["stash_list"])
            logger.info(texts["stash_pop"])
            return

    end_time = time.time()
    total_elapsed = end_time - start_time
    logger.info(texts["finish_upgrade"].format(time=total_elapsed))

    logger.info("\n" + texts["upgrade_complete"])
    logger.info(texts["check_config"])
    logger.info(texts["resolve_conflicts"])
    logger.info(texts["check_backup"])


if __name__ == "__main__":
    perform_upgrade()
