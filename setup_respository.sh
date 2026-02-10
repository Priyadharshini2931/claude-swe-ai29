cat << 'EOF' > setup_repository.sh
#!/bin/bash
set -e
set -o pipefail

echo "Setting up repository..."

rm -rf /testbed
git clone https://github.com/internetarchive/openlibrary.git /testbed
cd /testbed

git config --global --add safe.directory /testbed

BASE_COMMIT=84cc4ed5697b83a849e9106a09bfed501169cc20
TEST_COMMIT=c4eebe6677acc4629cb541a98d5e91311444f5d4
TEST_FILE=openlibrary/tests/core/test_imports.py

git reset --hard "$BASE_COMMIT"
git clean -fd

if git cat-file -e "$TEST_COMMIT:$TEST_FILE"; then
    git checkout "$TEST_COMMIT" -- "$TEST_FILE"
else
    echo "ERROR: File not found in commit"
    exit 1
fi

echo "Setup complete."
EOF
