# qq-notify

长任务跑完了，QQ 上弹一条：

```
来自 Qoder 的提示：任务 登录重构 已完成，请注意查看
```

一个单文件命令行工具 + 各 agent 的 skill 封装，让 Qoder / WorkBuddy / DeepSeek harness 这类 agent 软件在完成任务时把提醒发到你的 QQ。只用 Python 标准库，没有第三方依赖，能访问 NapCat 的 HTTP 端口就能跑。

## 前提

需要一个能替你发消息的 QQ 机器人，本项目走 **NapCat**（OneBot v11 协议）。LangBot 之类的框架不是必需的——发消息只用到 NapCat 自己的 HTTP 接口。

1. NapCat 已登录一个机器人号，并在 WebUI 中启用 OneBot11 的 **HTTP 服务**（端口默认 `3000`）
2. 该机器人号已把你的目标 QQ 加为**好友**（`send_private_msg` 要求好友关系）
3. 如果 HTTP 服务设置了 access token，记下它

## 快速开始

```bash
git clone https://github.com/ChangAkira/qq-notify.git
cd qq-notify
```

配置只有一项必填。写入本机共享配置 `~/.config/qq-notify/.env`：

```ini
TARGET_QQ=你的QQ号
```

其余字段（远端 NapCat、token）见 [`.env.example`](.env.example)。然后验证：

```bash
python3 notify.py --source Qoder --task "自检" --dry-run   # 只看文案和发送目标，不真发
python3 notify.py --source Qoder --task "自检"             # 真发一条
```

输出 `✅ 已推送到 QQ ...` 且 QQ 收到消息即成功。

### 配置解析顺序

同一份配置可以来自多个位置，**按 key 合并，靠前的来源优先**；真实环境变量始终最高：

1. 环境变量 `TARGET_QQ` / `NAPCAT_HOST` / `NAPCAT_PORT` / `NAPCAT_TOKEN`
2. `--env-file` 或 `QQNOTIFY_ENV` 指定的文件（指定后就只用这一个）
3. 当前运行目录的 `.env`
4. `notify.py` 同级目录的 `.env`
5. `~/.config/qq-notify/.env` ← 推荐，一台机器上所有 agent 共用一份

缺省值：`NAPCAT_HOST=127.0.0.1`、`NAPCAT_PORT=3000`，所以本机部署时只填 `TARGET_QQ` 就够。

## 命令行

```bash
python3 notify.py --source Qoder --task "登录重构"
```

| 参数 | 说明 |
| --- | --- |
| `--source` | 来源软件名，进入文案的「来自 xxx」。默认 `Agent` |
| `--task` | 任务概括，建议 20 字以内，别塞文件路径和敏感信息 |
| `--status` | 状态短语，默认 `已完成`；异常结束可写 `失败`、`未完成，需要确认` |
| `--note` | 追加一行 `备注：xxx`，放关键结果 |
| `--text` | 完全自定义全文，忽略上面四个拼装参数 |
| `--env-file` | 指定配置文件 |
| `--timeout` | 单次请求超时秒数，默认 `5` |
| `--dry-run` | 只打印将要发送的内容 |

示例：

```bash
python3 notify.py --source Qoder --task "跑测试" --note "27 通过 3 跳过"
python3 notify.py --source WorkBuddy --task "周报生成" --status "失败" --note "接口 500"
python3 notify.py --text "备份完成，dump 在 /data/backup"
```

退出码：`0` 已发送、`1` 配置错误、`2` 发送失败（内部已退避重试 3 次）。

## 在自己的设备上配置

**机器人和 agent 同一台机器**：什么都不用填，默认就是 `127.0.0.1:3000`。

**机器人在另一台服务器**：填 `NAPCAT_HOST=<服务器地址>`。这个 HTTP 接口本身没有强鉴权，**不要把它裸露在公网**，走 SSH 隧道并把 host 保持为 `127.0.0.1`：

```bash
ssh -N -L 3000:127.0.0.1:3000 user@你的服务器
```

**Windows**：脚本可直接 `python notify.py ...` 调用；配置文件放在 `%USERPROFILE%\.config\qq-notify\.env`，或和 `notify.py` 放同一个目录取名 `.env`。

## 在 agent 上配置

用 `install_skill.sh` 安装，它会把 `notify.py` 拷进目标 skill 目录，并把 `skill/SKILL.md` 里的 `__SOURCE__`、`__SKILL_DIR__` 渲染成实际值：

```bash
./install_skill.sh Qoder                          # -> ~/.qoder-cn/skills/qq-notify
./install_skill.sh WorkBuddy ~/workbuddy/skills   # 其他支持 skill 目录的 agent
./install_skill.sh DeepSeekHarness --print        # 只渲染到 stdout
```

- **Qoder**：装完 `重启会话或 /skills reload`，`/skills list` 能看到 `qq-notify`。之后对话里说「做完告诉我」，任务结束时它会自己调用；也可以手动 `/qq-notify 登录重构`。
- **其他有 skill 机制的 agent**：把第二个参数换成该 agent 的 skills 根目录即可，`--source` 会渲染成你传的名字，QQ 上就能分清是谁发的。
- **没有 skill 机制的 agent**：用 `--print` 渲染出说明文本，粘进该 agent 的规则文件（`AGENTS.md`、系统提示、自定义 prompt 均可），再把里面的脚本路径改成实际位置。

## 常见问题

| 输出 | 原因与处理 |
| --- | --- |
| `缺少 TARGET_QQ` | 按上面的解析顺序检查配置，报错会列出它实际读过哪些文件 |
| `Connection refused` | NapCat 没在跑，或 HTTP 服务未启用 / 端口不对 |
| `鉴权失败（HTTP 401）` | `NAPCAT_TOKEN` 不对；NapCat 没设 token 时把该项留空，脚本就不会带 `Authorization` 头 |
| `接口拒绝（retcode=200）` | 逻辑失败，后面会附 NapCat 的原话。常见是机器人没加你好友 —— 那就改用群消息：把接口换成 `send_group_msg`、参数换成 `group_id` |

NapCat 即使发送失败也返回 HTTP 200，只看状态码会误判成功，所以本脚本解析 `retcode` 来判定。

## 项目来源

从 `ChangAkira/tiaoji_Monitor` 分离而来（GitHub 不允许 fork 自己的仓库，因此保留了它的完整提交历史而非 fork 关系）。原仓库负责高校研招网调剂监控，本项目只做「通知」这一件事，不包含任何抓取逻辑与监控目标。
