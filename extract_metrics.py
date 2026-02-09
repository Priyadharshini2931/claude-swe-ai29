
import json
import os
import re

LOG_FILES = {
    "pre": "pre_verification.log",
    "post": "post_verification.log",
    "agent": "agent.log",
    "prompts": "prompts.log"
}

OUTPUT_FILE = "result.json"

def parse_pytest_output(content):
    """
    Parse pytest output to find number of passed/failed tests.
    """
    if "no tests ran" in content:
        return {"passed": 0, "failed": 0, "error": True}
        
    # Look for the final summary line: "== 1 failed, 4 passed in 0.12s =="
    match = re.search(r"=+\s+(?:(\d+)\s+failed,?)?\s*(?:(\d+)\s+passed,?)?.*=+", content)
    if match:
        failed = int(match.group(1)) if match.group(1) else 0
        passed = int(match.group(2)) if match.group(2) else 0
        return {"passed": passed, "failed": failed, "error": False}
        
    return {"passed": 0, "failed": 0, "error": False}

def main():
    metrics = {
        "agent_actions": 0,
        "pre_verification_status": "unknown",
        "post_verification_status": "unknown", 
        "resolved": False,
        "details": {}
    }

    # 1. Analyze Agent Logs
    if os.path.exists(LOG_FILES['agent']):
        with open(LOG_FILES['agent'], 'r') as f:
            lines = f.readlines()
            metrics['agent_actions'] = len(lines)

    # 2. Analyze Pre-Verification
    if os.path.exists(LOG_FILES['pre']):
        with open(LOG_FILES['pre'], 'r') as f:
            pre_content = f.read()
        pre_stats = parse_pytest_output(pre_content)
        metrics['details']['pre'] = pre_stats
        # Pre-verification is "successful" if it FAILS (demonstrating the bug)
        if pre_stats['failed'] > 0:
            metrics['pre_verification_status'] = "success_failure_reproduced"
        else:
            metrics['pre_verification_status'] = "unexpected_pass"
    else:
        metrics['pre_verification_status'] = "missing_log"

    # 3. Analyze Post-Verification
    if os.path.exists(LOG_FILES['post']):
        with open(LOG_FILES['post'], 'r') as f:
            post_content = f.read()
        post_stats = parse_pytest_output(post_content)
        metrics['details']['post'] = post_stats
        
        # Post-verification is successful if NO tests failed
        if post_stats['failed'] == 0 and post_stats['passed'] > 0:
            metrics['post_verification_status'] = "success_fixed"
        else:
            metrics['post_verification_status'] = "failed_fix"
    else:
        metrics['post_verification_status'] = "missing_log"

    # 4. Determine Resolution
    if (metrics['pre_verification_status'] == "success_failure_reproduced" and 
        metrics['post_verification_status'] == "success_fixed"):
        metrics['resolved'] = True
    else:
        metrics['resolved'] = False

    # 5. Write Result
    print(f"Generating {OUTPUT_FILE} with metrics: {metrics}")
    with open(OUTPUT_FILE, "w") as f:
        json.dump(metrics, f, indent=4)

if __name__ == "__main__":
    main()
