# SWE-bench Pro GitHub Actions Hackathon

## 🎯 Objective
Build and verify an end-to-end solution using GitHub Actions to automate SWE-bench Pro task evaluation, demonstrating your ability to integrate AI-powered code generation with CI/CD pipelines.

## ⏱️ Time Limit
**96 hours**

## 🔧 Focus: Build and Verify
This hackathon emphasizes creating a complete, working end-to-end solution that you can demonstrate live.

## 📋 Overview
In this hackathon, you will create a complete GitHub repository with a GitHub Actions workflow that:
1. Downloads a pre-configured Docker environment
2. Sets up a repository for testing
3. Runs pre-verification tests (expecting them to fail)
4. Uses AI coding agents to generate fixes
5. Runs post-verification tests (expecting them to pass)
6. Generates all required artifacts
7. **Creates a complete GitHub repository that can be demonstrated live**

## 🎯 Success Criteria
A successful completion means:
- ✅ **Complete GitHub repository created and pushed**
- ✅ Working GitHub Actions workflow file (`.github/workflows/swebench-eval.yml`)
- ✅ Supporting Python scripts (`run_agent.py`, `extract_metrics.py`)
- ✅ Setup scripts for repository configuration
- ✅ All required artifacts generated:
  - `agent.log` (JSONL format with AI agent's actions)
  - `result.json` (metrics and success status)
  - `pre_verification.log` (fail-to-pass test results before fix)
  - `post_verification.log` (test results after fix)
  - `changes.patch` (diff of changes made)
  - **`prompts.md` (all prompts used to generate code)**
- ✅ **Live demonstration of the workflow running successfully in GitHub Actions**

## 📦 What You're Provided

### 1. Task Details
- **Task ID**: `internetarchive__openlibrary-c4eebe6677acc4629cb541a98d5e91311444f5d4`
- **Repository**: OpenLibrary (Internet Archive)
- **Task File**: `task.yaml` (see provided file)
- **Docker Image**: `manojva/openlibrary-python312:latest` (publicly available on Docker Hub)

### 2. AI Coding Agent API Keys (provided at hackathon start)
Participants can use their preferred AI coding agent:
- **Claude** (Anthropic) API key
- **Gemini** (Google) API key
- **OpenAI** (GPT/Codex) API key
- **Cursor** API access

Choose the AI agent you're most comfortable with!

### 3. Task Description
The task involves improving ISBN import logic by using local staged records instead of external API calls. See `task.yaml` for full details.

## 🛠️ Technical Requirements

### GitHub Actions Workflow Structure

Your workflow should have these key steps:

```yaml
name: SWE-bench Pro Evaluation
on:
  workflow_dispatch:
    inputs:
      task_id:
        description: 'Task ID to run'
        required: true
        default: 'internetarchive__openlibrary-c4eebe6677acc4629cb541a98d5e91311444f5d4'

jobs:
  evaluate:
    runs-on: ubuntu-latest
    container:
      image: manojva/openlibrary-python312:latest
      options: --user root

    steps:
      # Your implementation here
```

### Required Files to Create

#### 1. `run_agent.py`
This script should:
- Accept the task instruction as input
- Initialize your chosen AI agent client (Claude, Gemini, OpenAI, or Cursor)
- Send the task to the AI agent
- Execute the agent's proposed changes
- Log all actions to `agent.log` in JSONL format
- Handle file reading/writing operations
- Support bash command execution
- **Document all prompts used in `prompts.md`**

Key features:
- Support for multiple AI agents (Claude, Gemini, OpenAI, Cursor)
- Tool implementation for file operations (read, write, edit)
- Bash command execution capability
- JSONL logging of all AI agent interactions
- Error handling and retry logic
- Prompt documentation

#### 2. `extract_metrics.py`
This script should:
- Parse `agent.log` to extract metrics
- Count tokens (input/output)
- Calculate duration and cost
- Determine success/failure status
- Generate `result.json` with proper format

#### 3. `setup_repository.sh`
This script should:
- Clone the repository
- Checkout the correct commit
- Apply any necessary patches
- Set up the test environment

## 📊 Expected Artifacts Format

### `agent.log` (JSONL format)
```json
{"timestamp": "2024-01-20T10:00:00Z", "type": "request", "content": "..."}
{"timestamp": "2024-01-20T10:00:01Z", "type": "tool_use", "tool": "read_file", "args": {...}}
{"timestamp": "2024-01-20T10:00:02Z", "type": "response", "content": "..."}
```

### `result.json`
```json
{
  "resolved": true,
  "duration_seconds": 300,
  "total_cost_usd": 0.25,
  "tokens": {
    "input": 15000,
    "output": 2500,
    "cache_read": 0,
    "cache_write": 0
  },
  "tool_usage": {
    "read": 10,
    "write": 2,
    "edit": 5,
    "bash": 3
  }
}
```

### `pre_verification.log` / `post_verification.log`
Standard pytest output showing test results.

### `changes.patch`
Standard git diff output showing all changes made.

## 🔧 Implementation Tips

### 1. Repository Setup
```bash
# Use the provided git commands from task.yaml
git reset --hard 84cc4ed5697b83a849e9106a09bfed501169cc20
git clean -fd
git checkout c4eebe6677acc4629cb541a98d5e91311444f5d4 -- openlibrary/tests/core/test_imports.py
```

### 2. Running Tests
```bash
# Pre-verification (should fail)
cd /testbed && python -m pytest openlibrary/tests/core/test_imports.py::TestImportItem::test_find_staged_or_pending -xvs

# Post-verification (should pass after fixes)
cd /testbed && python -m pytest openlibrary/tests/core/test_imports.py::TestImportItem::test_find_staged_or_pending -xvs
```

### 3. AI Agent Integration Examples

#### Claude (Anthropic)
```python
from anthropic import Anthropic
client = Anthropic(api_key=os.environ['CLAUDE_API_KEY'])
```

#### Gemini (Google)
```python
import google.generativeai as genai
genai.configure(api_key=os.environ['GEMINI_API_KEY'])
```

#### OpenAI (GPT/Codex)
```python
from openai import OpenAI
client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
```

#### Cursor
```python
# Cursor API integration
# Check Cursor documentation for specific implementation
```

### 4. Tool Definitions
You'll need to implement these tools for your chosen AI agent:
- `read_file`: Read file contents
- `write_file`: Create/overwrite files
- `edit_file`: Make specific edits to files
- `run_bash`: Execute bash commands

Each AI agent has different tool/function calling formats - adapt accordingly!

## 📝 Evaluation Criteria

Your submission will be evaluated on:

1. **Functionality (40%)**
   - Workflow runs successfully
   - All artifacts are generated
   - Tests pass after Claude's fixes

2. **Code Quality (30%)**
   - Clean, readable code
   - Proper error handling
   - Good logging practices

3. **Completeness (20%)**
   - All required files present
   - Proper artifact formatting
   - Documentation

4. **Innovation (10%)**
   - Creative solutions
   - Optimization techniques
   - Extra features

## 🚀 Getting Started

1. Fork the provided repository template
2. Set up your GitHub Actions secrets:
   - `CLAUDE_API_KEY`: Your Claude API key
3. Create the required files in your repository
4. Test your workflow locally if possible
5. Push and trigger the workflow
6. Iterate and debug

## 💡 Hints

- Start with a minimal working version, then add features
- Use GitHub Actions logs extensively for debugging
- Test your Python scripts locally first
- Remember to handle edge cases (file not found, API errors, etc.)
- The Docker container has all dependencies pre-installed

## 🎖️ Bonus Challenges

If you finish early, consider these extensions:
- Add retry logic for flaky tests
- Implement caching for faster runs
- Add detailed progress reporting
- Create a dashboard for results visualization
- Support for multiple task execution

## 📞 Support

During the hackathon:
- Technical questions: Ask the facilitators
- API issues: Check the troubleshooting guide
- Docker/GitHub issues: Refer to provided documentation

## 🏁 Submission

To submit your solution:
1. **Push your complete repository to GitHub**
2. Ensure your workflow runs successfully end-to-end
3. Create a README in your repo with:
   - Link to successful workflow run
   - Which AI agent you used and why
   - Any special instructions
   - Challenges faced and solutions
4. Include `prompts.md` with all prompts used
5. **Prepare to demonstrate your solution live**
6. Submit your repository URL

## 🎯 Remember: Build and Verify!
This hackathon is about creating a complete, working solution that you can demonstrate. Focus on:
- End-to-end functionality
- Live demonstration readiness
- Complete documentation including prompts
- Working GitHub repository

Good luck! 🚀

