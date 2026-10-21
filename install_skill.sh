#!/usr/bin/env bash
# 把 qq-notify skill 安装到某个 agent 的 skills 目录。
set -euo pipefail

usage() {
  cat <<'EOF'
用法: install_skill.sh <agent名> [目标]
  ./install_skill.sh Qoder                # 装到 ~/.qoder-cn/skills/qq-notify
  ./install_skill.sh WorkBuddy ~/workbuddy/skills
  ./install_skill.sh DeepSeekHarness --print   # 只渲染到 stdout，用于粘进该 agent 的规则/系统提示文件
EOF
  exit 1
}

[ $# -ge 1 ] || usage
agent="$1"
target="${2:-$HOME/.qoder-cn/skills}"
src_dir="$(cd "$(dirname "$0")" && pwd)"

render() {
  sed -e "s|__SOURCE__|$agent|g" -e "s|__SKILL_DIR__|$1|g" "$src_dir/skill/SKILL.md"
}

if [ "$target" = "--print" ]; then
  render "<该 agent 的 skill 目录>"
  exit 0
fi

skill_dir="$target/qq-notify"
mkdir -p "$skill_dir/scripts"
install -m 755 "$src_dir/notify.py" "$skill_dir/scripts/notify.py"
render "$skill_dir" >"$skill_dir/SKILL.md"

echo "✅ 已为 $agent 安装 skill：$skill_dir"
echo "   测试：python3 $skill_dir/scripts/notify.py --source $agent --task \"自检\" --dry-run"
