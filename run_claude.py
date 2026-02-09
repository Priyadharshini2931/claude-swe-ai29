import os
import sys
import json
import time
import subprocess
import requests
import yaml
import re

# Configuration
API_KEY = os.environ.get("ANTHROPIC_API_KEY")
MODELS = [
    "claude-3-haiku-20240307",     # Haiku (Fast) - Try this first since it worked
    "claude-3-5-sonnet-20240620",  # Sonnet 3.5
    "claude-3-sonnet-20240229",    # Sonnet 3
    "claude-3-opus-20240229",      # Opus
]
TASK_FILE = "task.yaml"
ARTIFACTS_DIR = "."

def log(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def run_command(command, log_file=None, check=False, cwd=None):
    """Run a shell command and optionally log output to a file."""
    log(f"Running command: {command} (cwd={cwd or '.'})")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd
        )
        
        output = result.stdout + result.stderr
        
        if log_file:
            with open(log_file, "a") as f:
                f.write(f"\nCommand: {command}\n")
                f.write(f"Return Code: {result.returncode}\n")
                f.write("--- OUTPUT ---\n")
                f.write(output)
                f.write("\n--------------\n")
        
        if check and result.returncode != 0:
            log(f"Command failed with RC {result.returncode}: {command}")
            log(output)
            raise subprocess.CalledProcessError(result.returncode, command, output)

        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        log(f"Error executing command: {e}")
        if check:
            raise e
        return -1, "", str(e)

def call_anthropic(prompt, task_context, logs):
    if not API_KEY:
        log("Error: ANTHROPIC_API_KEY not set.")
        return None
        
    cleaned_key = API_KEY.strip()
    url = "https://api.anthropic.com/v1/messages"
    
    # Try models one by one
    for model_name in MODELS:
        log(f"Attempting API call with model: {model_name}")
        
        headers = {
            "x-api-key": cleaned_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        technical_requirements = task_context.get('requirements', '')
        interface_spec = task_context.get('interface', '')
        
        system_prompt = f"""You are an expert Python developer tasked with fixing a bug in the OpenLibrary codebase.

Task Context:
{task_context['title']}
{task_context['description']}

Technical Requirements:
{technical_requirements}

Interface Specification:
{interface_spec}

The initial test run failed with the logs provided below. Your goal is to analyze the failure and provide a Git patch to fix the issue.

Current Working Directory: /testbed

Output Format:
Return ONLY the Git patch content inside a code block, like this:
```diff
diff --git a/path/to/file.py b/path/to/file.py
index ...
--- a/path/to/file.py
+++ b/path/to/file.py
@@ ... @@
- existing line
+ new line
```
Ensure the paths in the diff are relative to the repository root (e.g., openlibrary/core/imports.py).
"""
    
        user_message = f"Here are the failure logs from the pre-verification step:\n\n{logs[-8000:]}"
    
        data = {
            "model": model_name,
            "max_tokens": 4096,
            "messages": [
                {"role": "user", "content": user_message}
            ],
            "system": system_prompt
        }
    
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            
            log(f"Success with model: {model_name}")
            
            # Log prompt and response (JSONL)
            with open(os.path.join(ARTIFACTS_DIR, "prompts.log"), "a") as f:
                entry = {
                    "timestamp": time.time(),
                    "prompt": user_message,
                    "response": result
                }
                f.write(json.dumps(entry) + "\n")
                
            # Log to prompts.md
            with open(os.path.join(ARTIFACTS_DIR, "prompts.md"), "a") as f:
                f.write(f"## Prompt at {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"### Model: {model_name}\n\n")
                f.write("### Request\n")
                f.write("```\n" + user_message[:1000] + "...(truncated)...\n```\n\n")
                f.write("### Response\n")
                text_response = result['content'][0]['text']
                f.write("```\n" + text_response + "\n```\n\n")
                
            return result['content'][0]['text']
            
        except requests.exceptions.RequestException as e:
            log(f"Model {model_name} failed: {e}")
            if e.response is not None:
                 log(f"Response Status: {e.response.status_code}")
                 log(f"Response Body: {e.response.text}")
            continue
            
    log("All models failed.")
    return None

def extract_patch(response_text):
    """Extract the diff content from the response."""
    # Look for diff block
    match = re.search(r"```diff\n(.*?)```", response_text, re.DOTALL)
    if match:
        return match.group(1)
    
    # Fallback: generic code block containing diff
    match = re.search(r"```\n(.*?)```", response_text, re.DOTALL)
    if match:
        content = match.group(1)
        if "diff --git" in content or "--- a/" in content:
            return content
            
    # Fallback: Just the text if it looks like a diff
    if "diff --git" in response_text and "index" in response_text:
        return response_text
        
    return None

def main():
    log("=== STARTING AGENT WORKFLOW ===")
    
    # Check Environment
    if not API_KEY:
        log("CRITICAL ERROR: ANTHROPIC_API_KEY is not set.")
        sys.exit(1)
    else:
        log(f"API Key present (starts with {API_KEY[:4]}...)")

    # Load Task Config
    try:
        with open(TASK_FILE, "r") as f:
            task_config = yaml.safe_load(f)
        log(f"Successfully loaded {TASK_FILE}")
    except FileNotFoundError:
        log(f"CRITICAL ERROR: Config file {TASK_FILE} not found.")
        sys.exit(1)
    except yaml.YAMLError as e:
        log(f"CRITICAL ERROR: Invalid YAML in {TASK_FILE}: {e}")
        sys.exit(1)

    verification_cmd = task_config['tests']['test_command']
    setup_cmds = task_config.get('setup', {}).get('commands', '')

    # Setup
    target_dir = "/testbed"
    
    if os.path.exists(target_dir):
        log(f"Found target directory: {target_dir}")
        run_command("git config --global --add safe.directory /testbed")
        code, out, err = run_command("git status", cwd=target_dir)
        log(f"Git status: OK")
    else:
        log(f"ERROR: Target directory {target_dir} does NOT exist.")
        sys.exit(1)

    if setup_cmds and os.path.exists(target_dir):
        log(f"Running Setup Commands in {target_dir}...")
        for cmd in setup_cmds.splitlines():
            if cmd.strip() and not cmd.strip().startswith('cd '):
                ret, out, err = run_command(cmd, cwd=target_dir)
                if ret != 0:
                    log(f"Setup command warning: {cmd}")
    
    # Pre-Verification
    log("Starting Pre-Verification...")
    
    pre_log_file = os.path.join(ARTIFACTS_DIR, "pre_verification.log")
    if os.path.exists(pre_log_file):
        os.remove(pre_log_file)
    
    ret_code, stdout, stderr = run_command(verification_cmd, pre_log_file)
    
    log(f"Pre-verification completed (RC={ret_code})")
    if stdout:
        log(f"STDOUT preview: {stdout[:300]}")
    if stderr:
        log(f"STDERR preview: {stderr[:300]}")
    
    # Agent Execution
    log("Starting Agent Execution...")
    combined_logs = stdout + "\n" + stderr
    
    # Read the full log file for better context
    if os.path.exists(pre_log_file):
        with open(pre_log_file, 'r') as f:
            combined_logs = f.read()
    
    agent_response = call_anthropic(
        prompt="Fix the bug based on the logs.",
        task_context=task_config,
        logs=combined_logs
    )
    
    if not agent_response:
        log("Agent failed to provide a response.")
        sys.exit(1)

    # Save Agent Log
    with open(os.path.join(ARTIFACTS_DIR, "agent.log"), "w") as f:
        log_entry = {
            "action": "generate_patch",
            "observation": "Analyzed logs and generated patch",
            "response_length": len(agent_response)
        }
        f.write(json.dumps(log_entry) + "\n")

    # Apply Patch
    patch_content = extract_patch(agent_response)
    if patch_content:
        patch_file = os.path.join(ARTIFACTS_DIR, "changes.patch")
        with open(patch_file, "w") as f:
            f.write(patch_content)
        
        log(f"Patch saved to {patch_file}. Applying...")
        
        abs_patch_path = os.path.abspath(patch_file)
        
        apply_ret, _, apply_err = run_command(f"git apply {abs_patch_path}", cwd=target_dir)
        
        if apply_ret != 0:
            log(f"git apply failed, trying patch command...")
            apply_ret, _, apply_err = run_command(f"patch -p1 < {abs_patch_path}", cwd=target_dir)
            
            if apply_ret != 0:
                log("Patch application failed, but continuing to post-verification...")
    else:
        log("No valid patch found in agent response.")
        with open("agent_response_raw.txt", "w") as f:
             f.write(agent_response)

    # Post-Verification
    log("Starting Post-Verification...")
    post_log_file = os.path.join(ARTIFACTS_DIR, "post_verification.log")
    if os.path.exists(post_log_file):
        os.remove(post_log_file)
    
    ret_code, _, _ = run_command(verification_cmd, post_log_file)
    
    if ret_code == 0:
        log("Post-verification passed! Fix successful.")
    else:
        log(f"Post-verification failed (RC={ret_code}).")
    
    log("=== WORKFLOW COMPLETE ===")

if __name__ == "__main__":
    main()
