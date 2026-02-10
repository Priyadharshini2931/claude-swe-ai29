#!/bin/bash
set -e

echo "Setting up repository..."

rm -rf /testbed
git clone https://github.com/internetarchive/openlibrary.git /testbed
cd /testbed

git config --global --add safe.directory /testbed

# Reset repository to required base commit
BASE_COMMIT=84cc4ed5697b83a849e9106a09bfed501169cc20
TEST_COMMIT=c4eebe6677acc4629cb541a98d5e91311444f5d4
TEST_FILE=openlibrary/tests/core/test_imports.py

git reset --hard "$BASE_COMMIT"
git clean -fd

# Ensure the file exists in the source commit before checkout
if git cat-file -e "$TEST_COMMIT:$TEST_FILE"; then
    git checkout "$TEST_COMMIT" -- "$TEST_FILE"
else
    echo "ERROR: $TEST_FILE does not exist in commit $TEST_COMMIT"
    exit 1
fi

echo "Setup complete."
