---
name: qq-notify
description: 任务完成后向用户的 QQ 推送一条提醒消息（NapCat / OneBot v11 私聊）。当用户说「做完告诉我」「跑完发我 QQ」「结束后提醒我」，或当一个耗时任务（构建、测试、部署、批量改动、长脚本）在你这边结束或异常中断需要用户介入时使用。也能把任意内容发给指定 QQ 号或群。
when_to_use: 用户交代的任务已完成或异常结束、且用户要求过完成时通知；或用户要求把某条内容发到某个 QQ
argument-hint: <任务概括>
---

# QQ 消息推送

## Overview

捆绑脚本 `qqsend.py` 走 NapCat 的 OneBot11 HTTP 接口，有两个子命令：

- `task` —— 发固定格式的任务提醒：`来自 __SOURCE__ 的提示：任务 <概括> 已完成，请注意查看`
- `send` —— 发任意内容给任意对象（`--to` 私聊，`--group` 发群）

## 何时用哪个

任务结束、用户此前要求过「做完告诉我」→ 用 `task`。
用户临时指定内容或收件人（「把这段日志发给 xxx」「在群里说一声」）→ 用 `send`。

不要在以下情况主动发送：单步问答或闲聊；任务中途停下来等用户补充信息；同一任务重复发送。一次任务只发一条。

## 用法

```bash
# 任务完成提醒，收件人取配置里的 TARGET_QQ
python3 __SKILL_DIR__/scripts/qqsend.py task \
  --source __SOURCE__ --task "<不超过 20 字的任务概括>"

# 异常结束
python3 __SKILL_DIR__/scripts/qqsend.py task \
  --source __SOURCE__ --task "跑测试" --status "失败" --note "3 个用例未过"

# 任意内容 → 指定 QQ 号或群；多行内容用管道，避免转义问题
python3 __SKILL_DIR__/scripts/qqsend.py send --to 123456789 --text "构建通过了"
git -C /path/to/repo log --oneline -5 | python3 __SKILL_DIR__/scripts/qqsend.py send --group 987654321
```

`task` 的 `--text` 可完全自定义全文（跳过文案拼装），`--to` / `--group` 可覆盖默认收件人。

内容里**不要**放文件路径、密钥、token、内网地址。`--dry-run` 只打印不发送，用来确认文案。

## 结果处理

- 退出码 0：stdout 就是已发送的文本，不必在回复里重复一遍
- 退出码 1（配置或参数错误）：把脚本列出的缺失项转告用户，让其在 `~/.config/qq-notify/.env` 填写。没有收件人时脚本会要求 `--to` 或配置里的 `TARGET_QQ`。不要自己去猜收件人和值，也不要代读或代写凭据文件
- 退出码 2（发送失败）：告知用户推送失败及脚本给出的原因，最多再重试一次

## Resources

`scripts/qqsend.py`：零第三方依赖，POST `http://{NAPCAT_HOST}:{NAPCAT_PORT}/{send_private_msg|send_group_msg}`，设了 token 时带 `Authorization: Bearer {NAPCAT_TOKEN}`，失败退避重试 3 次。配置解析顺序：环境变量 > `--env-file`/`QQNOTIFY_ENV` > 运行目录 `.env` > 脚本同级 `.env` > `~/.config/qq-notify/.env`。
