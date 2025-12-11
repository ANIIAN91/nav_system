#!/bin/bash
set -e

# 初始化数据文件（如果不存在）
if [ ! -f /app/data/links.json ]; then
    echo "初始化 links.json..."
    cp /app/defaults/links.json /app/data/links.json
fi

if [ ! -f /app/data/settings.json ]; then
    echo "初始化 settings.json..."
    cp /app/defaults/settings.json /app/data/settings.json
fi

# 执行传入的命令
exec "$@"
