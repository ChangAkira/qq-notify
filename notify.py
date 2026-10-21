#!/usr/bin/env python3
"""向 QQ 推送任务完成提醒（NapCat / OneBot v11 HTTP 接口）。"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

CONFIG_FILE = Path.home() / ".config" / "qq-notify" / ".env"
MAX_RETRIES = 3

VALID_KEYS = {"TARGET_QQ", "NAPCAT_HOST", "NAPCAT_PORT", "NAPCAT_TOKEN"}
DEFAULTS = {"NAPCAT_HOST": "127.0.0.1", "NAPCAT_PORT": "3000"}


def parse_env_file(path):
    values = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return values
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key in VALID_KEYS and value:
            values[key] = value
    return values


def resolve_config(explicit_path):
    """真实环境变量优先，其次配置文件；多个配置文件按 key 合并，靠前的来源优先。"""
    override = explicit_path or os.getenv("QQNOTIFY_ENV")
    if override:
        candidates = [Path(override).expanduser()]
    else:
        candidates = [
            Path.cwd() / ".env",
            Path(__file__).resolve().parent / ".env",
            CONFIG_FILE,
        ]

    merged = {}
    used = []
    for candidate in candidates:
        if not candidate.is_file():
            continue
        used.append(candidate)
        for key, value in parse_env_file(candidate).items():
            merged.setdefault(key, value)

    config = {}
    for key in VALID_KEYS:
        config[key] = os.getenv(key) or merged.get(key) or DEFAULTS.get(key, "")
    return config, used


def build_message(args):
    if args.text:
        message = args.text
    else:
        message = f"来自 {args.source} 的提示：任务 {args.task} {args.status}，请注意查看"
    if args.note:
        message += f"\n备注：{args.note}"
    return message


def send_message(config, message, timeout):
    url = f"http://{config['NAPCAT_HOST']}:{config['NAPCAT_PORT']}/send_private_msg"
    payload = {"user_id": int(config["TARGET_QQ"]), "message": message}
    headers = {"Content-Type": "application/json"}
    if config["NAPCAT_TOKEN"]:
        headers["Authorization"] = f"Bearer {config['NAPCAT_TOKEN']}"

    data = json.dumps(payload).encode("utf-8")
    last_error = ""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            request = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8", "replace")
            try:
                result = json.loads(body)
                retcode = result.get("retcode", result.get("status", ""))
            except json.JSONDecodeError:
                retcode = ""
            if str(retcode) in ("0", "ok"):
                return True, ""
            detail = body.strip()[:200] or "响应无法解析"
            last_error = f"接口拒绝（retcode={retcode}）：{detail}"
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace").strip()[:200]
            last_error = f"HTTP {exc.code}：{detail}"
            if exc.code in (401, 403):
                return False, f"鉴权失败，请检查 NAPCAT_TOKEN（HTTP {exc.code}）"
        except Exception as exc:  # 网络超时、拒连等
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt < MAX_RETRIES:
            time.sleep(attempt * 2)
    return False, last_error


def main():
    parser = argparse.ArgumentParser(description="推送任务提醒到 QQ")
    parser.add_argument("--source", default="Agent", help="来源软件名，如 Qoder")
    parser.add_argument("--task", default="", help="任务名称")
    parser.add_argument("--status", default="已完成", help="任务状态，默认「已完成」")
    parser.add_argument("--note", default="", help="附加备注")
    parser.add_argument("--text", default="", help="直接发送自定义全文，忽略其他拼装参数")
    parser.add_argument("--env-file", default="", help="指定配置文件路径")
    parser.add_argument("--timeout", type=float, default=5.0, help="单次请求超时秒数")
    parser.add_argument("--dry-run", action="store_true", help="只打印将要发送的内容")
    args = parser.parse_args()

    if not args.text and not args.task:
        print("❌ 配置错误：需要 --task（或直接给 --text）")
        return 1

    config, used = resolve_config(args.env_file or None)
    sources = "、".join(str(p) for p in used) or "无配置文件"
    if not config["TARGET_QQ"]:
        print("❌ 配置错误：缺少 TARGET_QQ")
        print(f"   请在 {CONFIG_FILE} 中填写（已读取：{sources}）")
        return 1
    for key in ("TARGET_QQ", "NAPCAT_PORT"):
        if not config[key].isdigit():
            print(f"❌ 配置错误：{key} 必须是纯数字，当前为「{config[key]}」（来源：{sources}）")
            return 1

    message = build_message(args)

    if args.dry_run:
        print(f"[dry-run] POST http://{config['NAPCAT_HOST']}:{config['NAPCAT_PORT']}/send_private_msg")
        print(f"[dry-run] user_id={config['TARGET_QQ']} token={'已设置' if config['NAPCAT_TOKEN'] else '未设置'}")
        print("[dry-run] 消息内容：")
        print(message)
        return 0

    ok, error = send_message(config, message, args.timeout)
    if ok:
        print(f"✅ 已推送到 QQ {config['TARGET_QQ']}：{message.splitlines()[0]}")
        return 0
    print(f"❌ 推送失败：{error}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
