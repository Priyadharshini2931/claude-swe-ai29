import os
import sys
import json
import time
import subprocess
import requests
import yaml

# Configuration
API_KEY = os.environ.get("ANTHROPIC_API_KEY")
TASK_FILE = "task.yaml"

def log_jsonl(entry):
    """Write agent action to agent.log in JSONL format."""
    with open("agent.log", "a") as f:
        f.write(json.dumps(entry) + "\n")

def get_timestamp():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def run_bash(command, cwd="/testbed"):
    timestamp = get_timestamp()
    log_jsonl({"timestamp": timestamp, "type": "tool_use", "tool": "run_bash", "args": {"command": command}})
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=cwd)
        output = result.stdout + result.stderr
        return output, result.returncode
    except Exception as e:
        return str(e), -1

def read_file(path, cwd="/testbed"):
    timestamp = get_timestamp()
    log_jsonl({"timestamp": timestamp, "type": "tool_use", "tool": "read_file", "args": {"path": path}})
    full_path = os.path.join(cwd, path) if not path.startswith("/") else path
    try:
        if not os.path.exists(full_path):
            return None, f"File {path} not found"
        with open(full_path, "r") as f:
            return f.read(), None
    except Exception as e:
        return None, str(e)

def write_file(path, content, cwd="/testbed"):
    timestamp = get_timestamp()
    log_jsonl({"timestamp": timestamp, "type": "tool_use", "tool": "write_file", "args": {"path": path, "content": "[Content hidden]"}})
    full_path = os.path.join(cwd, path) if not path.startswith("/") else path
    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
        return "success", None
    except Exception as e:
        return None, str(e)

def edit_file(path, old_str, new_str, cwd="/testbed"):
    timestamp = get_timestamp()
    log_jsonl({"timestamp": timestamp, "type": "tool_use", "tool": "edit_file", "args": {"path": path, "old_str": old_str, "new_str": new_str}})
    full_path = os.path.join(cwd, path) if not path.startswith("/") else path
    try:
        with open(full_path, "r") as f:
            content = f.read()
        if old_str not in content:
            return None, "Target string not found"
        new_content = content.replace(old_str, new_str)
        with open(full_path, "w") as f:
            f.write(new_content)
        return "success", None
    except Exception as e:
        return None, str(e)

def call_anthropic(messages, system_prompt):
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": API_KEY.strip(),
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    tools = [
        {"name": "run_bash", "description": "Execute bash commands in /testbed.", "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
        {"name": "read_file", "description": "Read contents of a file.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
        {"name": "write_file", "description": "Create or overwrite a file.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
        {"name": "edit_file", "description": "Replace a specific block of text.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_str": {"type": "string"}, "new_str": {"type": "string"}}, "required": ["path", "old_str", "new_str"]}}
    ]

    # Log the request
    last_user_msg = messages[-1]['content'] if isinstance(messages[-1]['content'], str) else "Tool input"
    log_jsonl({"timestamp": get_timestamp(), "type": "request", "content": str(last_user_msg)})

    data = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 4096,
        "system": system_prompt,
        "messages": messages,
        "tools": tools
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    result = response.json()
    
    # Log the response
    resp_text = "".join([c['text'] for c in result['content'] if c['type'] == 'text'])
    log_jsonl({"timestamp": get_timestamp(), "type": "response", "content": resp_text or "[Tool Use Execution]"})
    
    # Log to prompts.log for extraction script
    with open("prompts.log", "a") as f:
        f.write(json.dumps({"req": messages, "res": result}) + "\n")
        
    return result

def main():
    if not API_KEY:
        print("Error: ANTHROPIC_API_KEY not set.")
        sys.exit(1)
        
    if os.path.exists("agent.log"): os.remove("agent.log")
    if os.path.exists("prompts.log"): os.remove("prompts.log")
    
    with open(TASK_FILE, "r") as f:
        task = yaml.safe_load(f)
    
    test_cmd = task['tests']['test_command']

    # Step 1: Pre-Verification
    print("Running pre-verification...")
    out, _ = run_bash(test_cmd)
    with open("pre_verification.log", "w") as f:
        f.write(out)

    system_prompt = f"""You are an expert software engineer fixing a bug in OpenLibrary.
Task: {task['description']}
Requirements: {task['requirements']}
Interface: {task['interface']}
Working Directory: /testbed
 reproduction script: {test_cmd}

Solve the task by exploring the code, reproducing the failure, and applying a fix.
"""

    messages = [{"role": "user", "content": "The test is failing. Please fix the implementation.\nFailure logs:\n" + out}]
    
    # Simple autonomous loop
    for _ in range(12):
        try:
            res = call_anthropic(messages, system_prompt)
            messages.append({"role": "assistant", "content": res['content']})
            
            tool_calls = [c for c in res['content'] if c['type'] == 'tool_use']
            if not tool_calls:
                break # Agent finished
                
            tool_outputs = []
            for tc in tool_calls:
                name, args, tid = tc['name'], tc['input'], tc['id']
                if name == "run_bash": val, err = run_bash(args['command'])
                elif name == "read_file": val, err = read_file(args['path'])
                elif name == "write_file": val, err = write_file(args['path'], args['content'])
                elif name == "edit_file": val, err = edit_file(args['path'], args['old_str'], args['new_str'])
                tool_outputs.append({"type": "tool_result", "tool_use_id": tid, "content": str(val or err)})
            
            messages.append({"role": "user", "content": tool_outputs})
            
        except Exception as e:
            print(f"Error in loop: {e}")
            break

    # Final Verification
    print("Running post-verification...")
    out, _ = run_bash(test_cmd)
    with open("post_verification.log", "w") as f:
        f.write(out)
    
    diff, _ = run_bash("git diff", cwd="/testbed")
    with open("changes.patch", "w") as f:
        f.write(diff)

    # Human-readable history
    with open("prompts.md", "w") as f:
        f.write("# Autonomous Agent Session history\n\n")
        for m in messages:
            f.write(f"## {m['role'].upper()}\n\n{json.dumps(m['content'], indent=2)}\n\n")

if __name__ == "__main__":
    main()
