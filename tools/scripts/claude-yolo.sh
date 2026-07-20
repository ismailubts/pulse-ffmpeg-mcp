#!/bin/bash

# Claude YOLO Mode - Start Claude Code with dangerous permissions skipped
# WARNING: This skips all permission prompts - use with extreme caution!

echo "🚀 Starting Claude Code in YOLO mode..."
echo "⚠️  WARNING: Skipping all permission prompts!"
echo ""

$HOME/.claude/local/claude \
  --dangerously-skip-permissions \
  --allowedTools "Bash" "Edit" "Write" "Read" "Grep" "Glob" "MultiEdit" "TodoWrite" "Task" \
  "$@"
