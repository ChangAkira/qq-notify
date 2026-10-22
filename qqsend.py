#!/usr/bin/env python3
"""通用 QQ 消息发送（NapCat / OneBot v11）。

send  给任意对象发任意内容
task  发固定格式的「任务完成」提醒
"""

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


def build_task_message(args):
    if args.raw:
        message = args.raw
    else:
        message = f"来自 {args.source} 的提示：任务 {args.task} {args.status}，请注意查看"
    if args.note:
        message += f"\n备注：{args.note}"
    return message


def read_stdin_text():
    if sys.stdin.isatty():
        return ""
    return sys.stdin.read().strip("\n")


def deliver(config, used, endpoint, payload, message, timeout, dry_run):
    if dry_run:
        print(f"[dry-run] POST http://{config['NAPCAT_HOST']}:{config['NAPCAT_PORT']}/{endpoint}")
        print(f"[dry-run] payload={json.dumps(payload, ensure_ascii=False)}")
        print("[dry-run] 消息内容：")
        print(message)
        return 0

    url = f"http://{config['NAPCAT_HOST']}:{config['NAPCAT_PORT']}/{endpoint}"
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
                target = payload.get("user_id") or payload.get("group_id")
                kind = "QQ" if "user_id" in payload else "群"
                print(f"✅ 已推送到 {kind} {target}：{message.splitlines()[0]}")
                return 0
            last_error = f"接口拒绝（retcode={retcode}）：{body.strip()[:200] or '响应无法解析'}"
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace").strip()[:200]
            last_error = f"HTTP {exc.code}：{detail}"
            if exc.code in (401, 403):
                print(f"❌ 推送失败：鉴权失败，请检查 NAPCAT_TOKEN（HTTP {exc.code}）")
                return 2
        except Exception as exc:  # 网络超时、拒连等
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt < MAX_RETRIES:
            time.sleep(attempt * 2)
    print(f"❌ 推送失败：{last_error}")
    return 2


def as_id(value, field, sources):
    if not value.isdigit():
        print(f"❌ 参数错误：{field} 必须是纯数字，当前为「{value}」（配置来源：{sources}）")
        return None
    return int(value)


def common_args(parser):
    parser.add_argument("--env-file", default="", help="指定配置文件路径")
    parser.add_argument("--timeout", type=float, default=5.0, help="单次请求超时秒数")
    parser.add_argument("--dry-run", action="store_true", help="只打印将要发送的内容")


def main(argv=None):
    parser = argparse.ArgumentParser(description="发送 QQ 消息（NapCat / OneBot v11）")
    common = argparse.ArgumentParser(add_help=False)
    common_args(common)

    sub = parser.add_subparsers(dest="cmd", required=True)

    send_p = sub.add_parser("send", parents=[common], help="给任意对象发任意内容")
    send_p.add_argument("--to", default="", help="接收者 QQ 号（私聊）。省略则用配置里的 TARGET_QQ")
    send_p.add_argument("--group", default="", help="群号，改为发群消息")
    send_p.add_argument("--text", default="", help='消息内容；传 "-" 或省略则读标准输入')

    task_p = sub.add_parser("task", parents=[common], help="发送任务完成提醒")
    task_p.add_argument("--source", default="Agent", help="来源软件名，如 Qoder")
    task_p.add_argument("--task", default="", help="任务概括")
    task_p.add_argument("--status", default="已完成", help="状态短语，默认「已完成」")
    task_p.add_argument("--note", default="", help="追加一行备注")
    task_p.add_argument("--text", dest="raw", default="", help="自定义全文，跳过文案拼装")
    task_p.add_argument("--to", default="", help="接收者 QQ 号，覆盖配置默认值")
    task_p.add_argument("--group", default="", help="群号，改为发群消息")

    args = parser.parse_args(argv)
    config, used = resolve_config(args.env_file or None)
    sources = "、".join(str(p) for p in used) or "无配置文件"

    if not config["NAPCAT_PORT"].isdigit():
        print(f"❌ 配置错误：NAPCAT_PORT 必须是纯数字，当前为「{config['NAPCAT_PORT']}」（来源：{sources}）")
        return 1

    if args.cmd == "send":
        text = sys.stdin.read().strip("\n") if args.text == "-" else args.text
        if not text and args.text != "-":
            text = read_stdin_text()
        if not text:
            print('❌ 参数错误：没有消息内容。用 --text "..."，或把内容通过标准输入管道传进来')
            return 1
        message = text
    else:
        if not args.task and not args.raw:
            print("❌ 参数错误：需要 --task（或直接给 --text）")
            return 1
        message = build_task_message(args)

    if args.to and args.group:
        print("❌ 参数错误：--to 和 --group 只能给一个，避免发错对象")
        return 1

    if args.group:
        group_id = as_id(args.group, "--group", sources)
        if group_id is None:
            return 1
        endpoint, payload = "send_group_msg", {"group_id": group_id, "message": message}
    else:
        target = args.to or config["TARGET_QQ"]
        if not target:
            print(f"❌ 参数错误：没有收件人。给 --to <QQ号>，或在 {CONFIG_FILE} 里设 TARGET_QQ")
            return 1
        user_id = as_id(target, "收件人 QQ 号", sources)
        if user_id is None:
            return 1
        endpoint, payload = "send_private_msg", {"user_id": user_id, "message": message}

    return deliver(
        config, used, endpoint, payload, message,
        timeout=args.timeout, dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
