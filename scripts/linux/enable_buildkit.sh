#!/bin/bash
# Enable Docker BuildKit for Linux
# Run this script once to enable BuildKit permanently

set -e

echo "🚀 Enabling Docker BuildKit for Linux..."
echo ""

# Detect shell
SHELL_NAME=$(basename "$SHELL")
SHELL_RC=""

case "$SHELL_NAME" in
    bash)
        SHELL_RC="$HOME/.bashrc"
        ;;
    zsh)
        SHELL_RC="$HOME/.zshrc"
        ;;
    fish)
        SHELL_RC="$HOME/.config/fish/config.fish"
        ;;
    *)
        SHELL_RC="$HOME/.profile"
        ;;
esac

echo "Detected shell: $SHELL_NAME"
echo "Config file: $SHELL_RC"
echo ""

# Check if already configured
if grep -q "DOCKER_BUILDKIT=1" "$SHELL_RC" 2>/dev/null; then
    echo "⚠️  BuildKit already configured in $SHELL_RC"
else
    # Add BuildKit environment variables to shell config
    echo "Adding BuildKit environment variables to $SHELL_RC..."
    
    cat >> "$SHELL_RC" << 'EOF'

# Docker BuildKit - Enable next-generation build engine
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
EOF
    
    echo "✅ BuildKit configuration added to $SHELL_RC"
fi

# Set for current session
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

echo "✅ BuildKit enabled for current session"
echo ""

# Verify BuildKit is available
if command -v docker &> /dev/null; then
    echo "Verifying Docker BuildKit..."
    if docker buildx version &> /dev/null; then
        echo "✅ Docker BuildKit is available!"
        docker buildx version
    else
        echo "⚠️  Docker BuildKit (buildx) not found"
        echo "    You may need to update Docker to version 19.03+"
    fi
else
    echo "⚠️  Docker not found. Please install Docker first."
    exit 1
fi

echo ""
echo "📋 Next Steps:"
echo "  1. Restart your terminal (or run: source $SHELL_RC)"
echo "  2. Verify: echo \$DOCKER_BUILDKIT (should show: 1)"
echo "  3. Build: make linux-build"
echo ""
echo "Benefits:"
echo "  ✅ 95% faster rebuilds with cached dependencies"
echo "  ✅ Parallel build execution"
echo "  ✅ Better build progress output"
echo ""
echo "See BUILDKIT_GUIDE.md for more information."
