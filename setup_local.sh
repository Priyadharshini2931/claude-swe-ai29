#!/bin/bash
# Local testing setup script for SWE-bench hackathon

set -e

echo "🔧 Setting up local testing environment..."

# Check if running as root (needed for /testbed symlink)
if [ "$EUID" -eq 0 ]; then 
    TESTBED_PATH="/testbed"
    echo "Running as root, will use /testbed directly"
else
    TESTBED_PATH="/tmp/testbed"
    echo "Running as user, will use $TESTBED_PATH (can't create /testbed without sudo)"
fi

# Clone repository if not exists
if [ ! -d "$TESTBED_PATH" ]; then
    echo "📥 Cloning OpenLibrary repository..."
    git clone https://github.com/internetarchive/openlibrary.git "$TESTBED_PATH"
else
    echo "✅ Repository already exists at $TESTBED_PATH"
fi

cd "$TESTBED_PATH"

# Configure git
echo "🔧 Configuring git..."
git config --global --add safe.directory "$TESTBED_PATH" 2>/dev/null || true

# Apply setup commands from task.yaml
echo "🔄 Resetting to base commit..."
git reset --hard 84cc4ed5697b83a849e9106a09bfed501169cc20
git clean -fd

echo "📝 Checking out test file..."
git checkout c4eebe6677acc4629cb541a98d5e91311444f5d4 -- openlibrary/tests/core/test_imports.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "Repository location: $TESTBED_PATH"
echo ""

# If we're not using /testbed, create a symlink if possible
if [ "$TESTBED_PATH" != "/testbed" ]; then
    if [ ! -e "/testbed" ]; then
        echo "💡 To run the script without modification, create a symlink:"
        echo "   sudo ln -s $TESTBED_PATH /testbed"
        echo ""
        echo "Or modify run_claude.py to use '$TESTBED_PATH' instead of '/testbed'"
    fi
fi

echo "Now run: python run_claude.py"
