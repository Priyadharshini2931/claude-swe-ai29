#!/bin/bash
set -e

echo "Setting up repository..."
rm -rf /testbed
git clone https://github.com/internetarchive/openlibrary.git /testbed
cd /testbed
git config --global --add safe.directory /testbed

# Specific commit requirements from task.yaml
git reset --hard 84cc4ed5697b83a849e9106a09bfed501169cc20
git clean -fd
git checkout c4eebe6677acc4629cb541a98d5e91311444f5d4 -- openlibrary/tests/core/test_imports.py

echo "Setup complete."
