---
name: qq-notify
description: 任务完成后向用户的 QQ 推送一条提醒消息（NapCat / OneBot v11 私聊）。当用户说「做完告诉我」「跑完发我 QQ」「结束后提醒我」，或当一个耗时任务（构建、测试、部署、批量改动、长脚本）在你这边结束或异常中断需要用户介入时使用。
when_to_use: 用户交代的任务已完成或异常结束、且用户要求过完成时通知
argument-hint: <任务概括>
---

# QQ 任务提醒

## Overview

用捆绑脚本给用户的 QQ 发一条固定格式提醒：`来自 __SOURCE__ 的提示：任务 <概括> 已完成，请注意查看`。

## 触发时机

- 用户明确要求完成时通知（「做完告诉我」「跑完发我 QQ」）
- 用户交代的有实际工作量的任务刚结束：实现、修复、测试、构建、部署、数据处理
- 长任务异常终止、需要用户回来介入

不要在以下情况发送：单步问答或闲聊；任务中途停下来等用户补充信息；同一任务重复发送。一次任务只发一条。

## 用法

```bash
python3 __SKILL_DIR__/scripts/notify.py \
  --source __SOURCE__ --task "<不超过 20 字的任务概括>"
```

- `--task`：用用户原话概括任务，**不要**包含文件路径、密钥、token、内网地址
- `--status`：默认「已完成」；异常结束可改成「未完成，需要确认」或「失败」
- `--note`：可选，一行关键结果，如「27 个用例通过，3 个跳过」
- `--text`：完全自定义全文，忽略上面几个拼装参数
- `--dry-run`：只打印将要发送的内容，用于确认文案

## 结果处理

- 退出码 0：stdout 就是已发送的文本，不必在回复里重复一遍
- 退出码 1（配置错误）：把脚本列出的缺失项转告用户，让其在 `~/.config/qq-notify/.env` 填写 `TARGET_QQ`（远端部署还要填 `NAPCAT_HOST` / `NAPCAT_PORT` / `NAPCAT_TOKEN`）。不要自己去猜值，也不要代读或代写凭据文件
- 退出码 2（发送失败）：告知用户推送失败及脚本给出的原因，最多再重试一次

## Resources

`scripts/notify.py`：零第三方依赖，POST `http://{NAPCAT_HOST}:{NAPCAT_PORT}/send_private_msg`，设了 token 时带 `Authorization: Bearer {NAPCAT_TOKEN}`，失败退避重试 3 次。
