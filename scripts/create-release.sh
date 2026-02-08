#!/bin/bash
# GitHub Release 作成スクリプト
# ⚠️ 全PRがマージされてから実行すること
#
# 使い方:
#   chmod +x scripts/create-release.sh
#   ./scripts/create-release.sh

set -euo pipefail

TAG="v1.1.0"
TITLE="jltsql v1.1.0 — 初回安定リリース 🏇"
NOTES_FILE="RELEASE_NOTES.md"

echo "=== jltsql Release: ${TAG} ==="
echo ""

# 前提チェック
if ! command -v gh &> /dev/null; then
    echo "❌ gh CLI が必要です: https://cli.github.com/"
    exit 1
fi

if [ ! -f "$NOTES_FILE" ]; then
    echo "❌ ${NOTES_FILE} が見つかりません"
    exit 1
fi

# masterブランチか確認
BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "master" ]; then
    echo "❌ masterブランチで実行してください (現在: ${BRANCH})"
    exit 1
fi

# 未コミットの変更がないか
if ! git diff --quiet; then
    echo "❌ 未コミットの変更があります"
    exit 1
fi

echo "📋 リリース内容:"
echo "  タグ: ${TAG}"
echo "  タイトル: ${TITLE}"
echo ""
read -p "リリースを作成しますか? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "キャンセルしました"
    exit 0
fi

gh release create "${TAG}" \
    --title "${TITLE}" \
    --notes-file "${NOTES_FILE}" \
    --target master

echo ""
echo "✅ リリース ${TAG} を作成しました!"
echo "   https://github.com/miyamamoto/jrvltsql/releases/tag/${TAG}"
