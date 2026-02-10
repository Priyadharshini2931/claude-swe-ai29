import os
import sys
import json
import time
import subprocess
import requests
import yaml
import re

# ================= CONFIGURATION =================
API_KEY = os.environ.get("ANTHROPIC_API_KEY")

MODELS = [
    "claude-3-haiku-20240307",
    "claude-3-5-sonnet-20240620",
    "claude-3-sonnet-20240229",
    "claude-3-opus-20240229",
]

TASK_FILE = "task.yaml"
ARTIFACTS_DIR = "."

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

# ================= UTILITIES =================
def log(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def run_command(command, log_file=None, check=False, cwd=None):
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
            raise subprocess.CalledProcessError(
                result.returncode, command, output
            )

        return result.returncode, result.stdout, result.stderr

    except Exception as e:
        log(f"Command execution error: {e}")
        if check:
            raise
        return -1, "", str(e)

# ================= ANTHROPIC CALL =================
def call_anthropic(task_context, logs):
    if not API_KEY:
        log("ANTHROPIC_API_KEY not set.")
        return None

    headers = {
        "x-api-key": API_KEY.strip(),
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    system_prompt = f"""
You are an expert Python developer tasked with fixing a bug.

Task:
{task_context.get('title')}
{task_context.get('description')}

Requirements:
{task_context.get('requirements', '')}

Interface:
{task_context.get('interface', '')}

Return ONLY a git diff in a ```diff``` code block.
Paths must be repo-relative.
"""

    user_text = f"""
Here are the failing logs:

{logs[-8000:]}
"""

    for model in MODELS:
        log(f"Trying model: {model}")

        payload = {
            "model": model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text}
                    ],
                }
            ],
        }

        try:
            resp = requests.post(ANTHROPIC_URL, headers=headers, json=payload)
            if resp.status_code != 200:
                log(f"Model {model} failed ({resp.status_code})")
                log(resp.text)
                continue

            data = resp.json()

            text = data["content"][0]["text"]

            with open("prompts.log", "a") as f:
                f.write(json.dumps({
                    "time": time.time(),
                    "model": model,
                    "response": text
                }) + "\n")

            return text

        except Exception as e:
            log(f"Model {model} exception: {e}")

    return None

# ================= PATCH EXTRACTION =================
def extract_patch(response_text):
    match = re.search(r"```diff\n(.*?)```", response_text, re.DOTALL)
    if match:
        return match.group(1)

    if "diff --git" in response_text:
        return response_text

    return None

# ================= MAIN WORKFLOW =================
def main():
    log("=== STARTING AGENT WORKFLOW ===")

    if not API_KEY:
        log("CRITICAL: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    try:
        with open(TASK_FILE, "r") as f:
            task_config = yaml.safe_load(f)
    except Exception as e:
        log(f"Failed to load task.yaml: {e}")
        sys.exit(1)

    target_dir = "/testbed"
    verification_cmd = task_config["tests"]["test_command"]

    if not os.path.exists(target_dir):
        log("Target directory missing")
        sys.exit(1)

    run_command("git config --global --add safe.directory /testbed")

    # ===== PRE-VERIFICATION =====
    pre_log = "pre_verification.log"
    if os.path.exists(pre_log):
        os.remove(pre_log)

    ret, out, err = run_command(verification_cmd, pre_log, cwd=target_dir)

    logs = ""
    if os.path.exists(pre_log):
        with open(pre_log) as f:
            logs = f.read()
    else:
        logs = out + err

    # ===== AGENT =====
    response = call_anthropic(task_config, logs)

    if not response:
        log("Agent produced no response")
        sys.exit(1)

    patch = extract_patch(response)
    if not patch:
        log("No patch found in response")
        with open("agent_response_raw.txt", "w") as f:
            f.write(response)
        sys.exit(1)

    patch_file = "changes.patch"
    with open(patch_file, "w") as f:
        f.write(patch)

    # ===== APPLY PATCH =====
    ret, _, _ = run_command(f"git apply {patch_file}", cwd=target_dir)
    if ret != 0:
        log("git apply failed, trying patch")
        run_command(f"patch -p1 < {patch_file}", cwd=target_dir)

    # ===== POST-VERIFICATION =====
    post_log = "post_verification.log"
    if os.path.exists(post_log):
        os.remove(post_log)

    ret, _, _ = run_command(verification_cmd, post_log, cwd=target_dir)

    if ret == 0:
        log("✅ POST-VERIFICATION PASSED")
    else:
        log("❌ POST-VERIFICATION FAILED")

    log("=== WORKFLOW COMPLETE ===")

if __name__ == "__main__":
    main()
