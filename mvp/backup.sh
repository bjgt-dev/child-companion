#!/bin/bash
# 学习档案备份 / 恢复（V1.1 13-17：生产升级失败需回滚）
# 用法：./backup.sh            → 备份 data/ 到 backups/<时间戳>/
#       ./backup.sh restore <时间戳> → 从备份恢复（先自动再备一份当前）
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
TS="$(date +%Y%m%d-%H%M%S)"

if [ "$1" = "restore" ]; then
    [ -n "$2" ] || { echo "用法：./backup.sh restore <时间戳>"; exit 1; }
    [ -d "$DIR/backups/$2" ] || { echo "备份不存在：$2"; exit 1; }
    ./backup.sh >/dev/null  # 恢复前先备当前
    rm -rf "$DIR/data"
    cp -r "$DIR/backups/$2" "$DIR/data"
    chmod 700 "$DIR/data"; chmod 600 "$DIR"/data/*.db 2>/dev/null || true
    echo "已从 $2 恢复"
    exit 0
fi

mkdir -p "$DIR/backups/$TS"
cp -r "$DIR/data/." "$DIR/backups/$TS/"
echo "已备份到 backups/$TS/"
ls "$DIR/backups/"
