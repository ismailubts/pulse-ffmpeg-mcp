#!/bin/bash
#
# Install Build Detective Git Hooks
# Copies BD hooks to .git/hooks/ and makes them executable
#

set -e

PROJECT_ROOT=$(git rev-parse --show-toplevel)
HOOKS_DIR="$PROJECT_ROOT/.git/hooks"

echo "🔧 Installing Build Detective Git Hooks..."

# Create pre-push hook
cat > "$HOOKS_DIR/pre-push" << 'EOF'
#!/bin/bash
#
# Git pre-push hook - Run BD local CI verification
#
# This hook calls Build Detective local CI to verify changes before pushing
# Prevents pushing broken code that would fail in remote CI
#

echo "🔍 Pre-push: Running Build Detective local CI verification..."

# Change to project root
cd "$(git rev-parse --show-toplevel)"

# Run BD local CI (fast mode by default)
python3 scripts/bd_local_ci.py

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "✅ BD local CI passed - proceeding with push"
    exit 0
else
    echo "❌ BD local CI failed - push blocked"
    echo ""
    echo "💡 Fix the issues above, or run with --docker for full validation:"
    echo "   python3 scripts/bd_local_ci.py --docker"
    echo ""
    echo "⚠️  To bypass this check (not recommended):"
    echo "   git push --no-verify"
    exit 1
fi
EOF

# Make executable
chmod +x "$HOOKS_DIR/pre-push"

echo "✅ BD pre-push hook installed successfully!"
echo ""
echo "Usage:"
echo "  • Hook runs automatically on 'git push'"
echo "  • Bypass with 'git push --no-verify' if needed"
echo "  • Manual run: python3 scripts/bd_local_ci.py"
echo "  • Docker mode: python3 scripts/bd_local_ci.py --docker"