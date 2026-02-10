#!/usr/bin/env python3
"""
Wrapper script to run the agent with /tmp/testbed instead of /testbed
"""
import os
import sys

# Set the testbed path before importing run_claude
os.environ['TESTBED_PATH'] = '/tmp/testbed'

# Temporarily patch the target_dir in run_claude
import run_claude

# Replace the hardcoded path
original_main = run_claude.main

def patched_main():
    # Monkey patch the target_dir
    import run_claude
    original_code = run_claude.__file__
    
    # Just run with modified target_dir
    run_claude.main()

if __name__ == "__main__":
    # Quick hack: replace /testbed with /tmp/testbed in the module
    target_dir = "/tmp/testbed"
    
    # Update the path in run_claude module before running
    import importlib.util
    spec = importlib.util.spec_from_file_location("run_claude_patched", "run_claude.py")
    module = importlib.util.module_from_spec(spec)
    
    # Read and modify the source
    with open('run_claude.py', 'r') as f:
        source = f.read()
    
    source_modified = source.replace('target_dir = "/testbed"', 'target_dir = "/tmp/testbed"')
    
    # Execute the modified source
    exec(source_modified)
