#!/bin/zsh
# Enable Docker BuildKit for macOS
# Run this script once to enable BuildKit permanently

set -e

echo "🚀 Enabling Docker BuildKit for macOS..."
echo ""

# Detect shell and config file
CURRENT_SHELL=$(basename "$SHELL")
SHELL_RC=""

case "$CURRENT_SHELL" in
    zsh)
        SHELL_RC="$HOME/.zshrc"
        ;;
    bash)
        SHELL_RC="$HOME/.bash_profile"
        if [[ ! -f "$SHELL_RC" ]]; then
            SHELL_RC="$HOME/.bashrc"
        fi
        ;;
    fish)
        SHELL_RC="$HOME/.config/fish/config.fish"
        ;;
    *)
        SHELL_RC="$HOME/.zshrc"  # Default to zsh on macOS
        ;;
esac

echo "Detected shell: $CURRENT_SHELL"
echo "Config file: $SHELL_RC"
echo ""

# Ensure config file exists
if [[ ! -f "$SHELL_RC" ]]; then
    echo "Creating $SHELL_RC..."
    touch "$SHELL_RC"
fi

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

# Verify Docker and BuildKit
if command -v docker &> /dev/null; then
    echo "Verifying Docker BuildKit..."
    
    # Check if Docker Desktop is running
    if ! docker info &> /dev/null; then
        echo "⚠️  Docker is not running. Please start Docker Desktop."
        exit 1
    fi
    
    # Check BuildKit availability
    if docker buildx version &> /dev/null; then
        echo "✅ Docker BuildKit is available!"
        docker buildx version
    else
        echo "⚠️  Docker BuildKit (buildx) not found"
        echo "    You may need to update Docker Desktop to version 19.03+"
        echo "    Download: https://www.docker.com/products/docker-desktop"
    fi
else
    echo "⚠️  Docker not found. Please install Docker Desktop first."
    echo "    Download: https://www.docker.com/products/docker-desktop"
    exit 1
fi

echo ""
echo "📋 Next Steps:"
echo "  1. Restart your terminal (or run: source $SHELL_RC)"
echo "  2. Verify: echo \$DOCKER_BUILDKIT (should show: 1)"
echo "  3. Build: make macos-build"
echo ""
echo "Benefits:"
echo "  ✅ 95% faster rebuilds with cached dependencies"
echo "  ✅ Parallel build execution"
echo "  ✅ Better build progress output"
echo ""
echo "See BUILDKIT_GUIDE.md for more information."
