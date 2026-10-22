# qq-notify

给 QQ 发消息的一条命令。核心是收件人无关的通用发送器，「任务完成提醒」只是它上面的一层预设。

```bash
python3 qqsend.py task --source Qoder --task "登录重构"    # 来自 Qoder 的提示：任务 登录重构 已完成，请注意查看
python3 qqsend.py send --to 123456789 --text "构建通过了"   # 任意内容发给任意对象
```

单文件、只用 Python 标准库，没有第三方依赖；能访问 NapCat 的 HTTP 端口就能跑。

## 前提

需要一个能替你发消息的 QQ 机器人，本项目走 **NapCat**（OneBot v11 协议）。LangBot 之类的框架不是必需的——发消息只用到 NapCat 自己的 HTTP 接口。

1. NapCat 已登录一个机器人号，并在 WebUI 中启用 OneBot11 的 **HTTP 服务**（端口默认 `3000`）
2. 私聊要求机器人号把收件人加为**好友**（发群没有这个限制）
3. 如果 HTTP 服务设置了 access token，记下它

## 快速开始

```bash
git clone https://github.com/ChangAkira/qq-notify.git
cd qq-notify
```

写入本机共享配置 `~/.config/qq-notify/.env`，只有一行是必要的：

```ini
TARGET_QQ=你的QQ号
```

其余字段（远端 NapCat、token）见 [`.env.example`](.env.example)。然后验证：

```bash
python3 qqsend.py task --source Qoder --task "自检" --dry-run   # 只看文案和目标，不真发
python3 qqsend.py task --source Qoder --task "自检"             # 真发一条
```

输出 `✅ 已推送到 QQ ...` 且 QQ 收到消息即成功。

## 两个子命令

### `send` —— 通用发送

| 参数 | 说明 |
| --- | --- |
| `--to` | 接收者 QQ 号（私聊）。省略时用配置里的 `TARGET_QQ` |
| `--group` | 群号，改为发群消息，与 `--to` 互斥 |
| `--text` | 消息内容；传 `-` 或省略则从标准输入读取 |

多行、带引号的内容用管道传，省掉转义麻烦：

```bash
git -C /path/to/repo log --oneline -5 | python3 qqsend.py send --group 987654321
python3 qqsend.py send --to 123456789 --text - < 报告.txt
```

### `task` —— 任务完成提醒

| 参数 | 说明 |
| --- | --- |
| `--source` | 来源软件名，进入「来自 xxx」。默认 `Agent` |
| `--task` | 任务概括，建议 20 字以内，别塞文件路径和敏感信息 |
| `--status` | 状态短语，默认 `已完成`；异常结束可写 `失败`、`未完成，需要确认` |
| `--note` | 追加一行 `备注：xxx`，放关键结果 |
| `--text` | 自定义全文，跳过文案拼装 |
| `--to` / `--group` | 覆盖默认收件人 |

```bash
python3 qqsend.py task --source WorkBuddy --task "周报生成" --status "失败" --note "接口 500"
```

两个子命令共有：`--env-file` 指定配置、`--timeout` 单次超时（默认 `5` 秒）、`--dry-run` 只打印。

退出码：`0` 已发送、`1` 配置或参数错误、`2` 发送失败（内部已退避重试 3 次）。

收件人由调用方决定，程序不做限制；QQ 消息是明文，所以内容里不要放密钥、token、内网地址。

## 配置解析顺序

同一份配置可以来自多个位置，**按 key 合并，靠前的来源优先**；真实环境变量始终最高：

1. 环境变量 `TARGET_QQ` / `NAPCAT_HOST` / `NAPCAT_PORT` / `NAPCAT_TOKEN`
2. `--env-file` 或 `QQNOTIFY_ENV` 指定的文件（指定后就只用这一个）
3. 当前运行目录的 `.env`
4. `qqsend.py` 同级目录的 `.env`
5. `~/.config/qq-notify/.env` ← 推荐，一台机器上所有 agent 共用一份

缺省值 `NAPCAT_HOST=127.0.0.1`、`NAPCAT_PORT=3000`，所以本机部署只填 `TARGET_QQ` 就够；`TARGET_QQ` 留空则每次必须在命令行给 `--to` 或 `--group`。

## 在自己的设备上配置

**机器人和 agent 同一台机器**：什么都不用填，默认就是 `127.0.0.1:3000`。

**机器人在另一台服务器**：填 `NAPCAT_HOST=<服务器地址>`。这个 HTTP 接口本身没有强鉴权，**不要把它裸露在公网**，走 SSH 隧道并把 host 保持为 `127.0.0.1`：

```bash
ssh -N -L 3000:127.0.0.1:3000 user@你的服务器
```

**Windows**：脚本可直接 `python qqsend.py ...` 调用；配置文件放 `%USERPROFILE%\.config\qq-notify\.env`，或和 `qqsend.py` 放同一目录取名 `.env`。

## 在 agent 上配置

用 `install_skill.sh` 安装，它把 `qqsend.py` 拷进目标 skill 目录，并把 `skill/SKILL.md` 里的 `__SOURCE__`、`__SKILL_DIR__` 渲染成实际值：

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
| `没有收件人` | 给 `--to`/`--group`，或在配置里设 `TARGET_QQ` |
| `缺少 TARGET_QQ` | 按上面的解析顺序检查配置，报错会列出它实际读过哪些文件 |
| `Connection refused` | NapCat 没在跑，或 HTTP 服务未启用 / 端口不对 |
| `鉴权失败（HTTP 401）` | `NAPCAT_TOKEN` 不对；NapCat 没设 token 时把该项留空，脚本就不会带 `Authorization` 头 |
| `接口拒绝（retcode=200）` | 逻辑失败，后面会附 NapCat 的原话。常见是机器人没加你好友 —— 那就改用 `--group` 发到群里 |

NapCat 即使发送失败也返回 HTTP 200，只看状态码会误判成功，所以本脚本解析 `retcode` 来判定。

## 项目来源

从 `ChangAkira/tiaoji_Monitor` 分离而来（GitHub 不允许 fork 自己的仓库，因此保留了它的完整提交历史而非 fork 关系）。原仓库负责高校研招网调剂监控，本项目只做「发 QQ 消息」这一件事，不包含任何抓取逻辑与监控目标。
