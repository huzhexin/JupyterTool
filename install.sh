#!/bin/bash
# JupyterTool 安装脚本
set -e

SKILL_DIR="$HOME/.claude/skills/jupyter-notebook"
TOOLS_DIR="$(cd "$(dirname "$0")/jupyter_tools" && pwd)"

echo "安装 Skill 到 $SKILL_DIR ..."
mkdir -p "$SKILL_DIR"
cp -r skill/* "$SKILL_DIR/"

echo "记录工具路径: $TOOLS_DIR"
echo "$TOOLS_DIR" > "$SKILL_DIR/.tools_path"

echo ""
echo "✅ 安装完成！"
echo ""
echo "下一步：编辑 config.ini 填入你的 Jupyter 服务器信息："
echo "  host = <your-host>"
echo "  port = <your-port>"
echo "  token = <your-token>"
