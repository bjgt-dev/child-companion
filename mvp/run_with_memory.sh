#!/bin/bash
# 经 omemo 记忆代理运行陪伴主流程
# 用法：./run_with_memory.sh python3 teach_loop.py
# 回滚：直接 python3 teach_loop.py（不经过 omemo）
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$DIR/omemo.env" ]; then
  set -a; . "$DIR/omemo.env"; set +a
fi
exec "$@"
