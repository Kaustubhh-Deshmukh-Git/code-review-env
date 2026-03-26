# Code Review OpenEnv

**An OpenEnv environment for training AI agents to review code and identify bugs, security vulnerabilities, and style issues.**

---

## Overview

Code Review is a real-world task simulation environment where AI agents learn to review Python code and identify issues across multiple difficulty levels. This environment models the actual process that developers perform during code review: reading code, identifying problems, and categorizing their severity.

### Why This Problem?

- **Real-World Utility**: Developers spend significant time on code reviews; automating parts of this process has immediate value
- **Training Data**: Provides structured learning scenarios for agents to understand code semantics
- **Scalability**: Can be extended with more code samples and bug patterns
- **Agent Evaluation**: Tests agent ability to reason about code quality, security, and style

---

## Features

✅ **3 Difficulty Levels**: Easy (syntax) → Medium (style/performance) → Hard (security)  
✅ **Deterministic Graders**: Fair scoring based on precision/recall metrics  
✅ **Partial Reward Signals**: Agents get feedback throughout the episode  
✅ **Real Code Patterns**: Includes actual bugs from real-world codebases  
✅ **Full OpenEnv Spec**: Complete Pydantic models, typed interfaces  
✅ **Dockerfile + HF Spaces Ready**: Deploy in minutes  

---

## Environment Specification

### Action Space

Agents can take 4 types of actions:

| Action | Parameters | Description |
|--------|-----------|-------------|
| `report_bug` | `line_number`, `bug_description`, `severity` | Report a bug on a specific line |
| `request_change` | `line_number`, `suggestion` | Request an improvement (no points) |
| `skip_line` | - | Move to next line without action |
| `approve` | - | Complete the review |

**Action Schema (JSON)**:
```json
{
  "action_type": "report_bug",
  "line_number": 2,
  "bug_description": "Missing colon after for loop",
  "severity": "critical",
  "suggestion": null
}
```

### Observation Space

Agents receive observations with:

| Field | Type | Description |
|-------|------|-------------|
| `code_lines` | `List[str]` | Code with line numbers |
| `current_line` | `int` | Line being reviewed |
| `bugs_found_so_far` | `Dict` | Bugs reported so far |
| `available_actions` | `List[str]` | Possible actions |
| `episode_progress` | `float` | 0.0-1.0 completion |
| `task_type` | `str` | "easy", "medium", or "hard" |
| `code_summary` | `str` | What the code does |

**Sample Observation**:
```json
{
  "code_lines": [
    " 0: def calculate_sum(numbers):",
    " 1:     total = 0",
    " 2:     for num in numbers",
    " 3:         total = total + num",
    " 4:     return total"
  ],
  "current_line": 0,
  "bugs_found_so_far": {},
  "available_actions": ["report_bug", "request_change", "skip_line", "approve"],
  "episode_progress": 0.0,
  "task_type": "easy",
  "code_summary": "Function to sum numbers with syntax error"
}
```

### Reward Function

**During Episode (Partial Signals)**:
- ✅ Correct bug report: **+0.30**
- ✅ Correct severity classification: **+0.10**
- ❌ False positive (bug reported but doesn't exist): **-0.15**
- ↷ Skip line or request change: **+0.01**

**Final Score** (when `approve` or max steps reached):
- Calculated using **precision/recall or weighted F1** depending on task
- Score range: **0.0 (no bugs found) to 1.0 (perfect review)**

---

## Tasks & Difficulty Levels

### Task 1: Syntax Error Detection (EASY) ⭐

**Difficulty**: 1/3  
**Max Steps**: 30  
**Description**: Identify obvious syntax errors in Python code

**Examples of Expected Bugs**:
- Missing colons after `for`, `if`, `def`
- Unclosed parentheses/brackets
- Invalid indentation
- Duplicate function definitions

**Success Criteria**:
- Identify all syntax errors
- No more than 2 false positives
- Minimum 80% recall

**Sample Code**:
```python
def calculate_sum(numbers):
    total = 0
    for num in numbers          # ❌ Missing colon
        total = total + num
    return total
```

---

### Task 2: Style & Performance Issues (MEDIUM) ⭐⭐

**Difficulty**: 2/3  
**Max Steps**: 50  
**Description**: Identify code style violations and performance issues

**Examples of Expected Issues**:
- Incorrect None checks (`!= None` instead of `is not None`)
- Inefficient list operations (append in loops vs list comprehension)
- Missing error handling for risky operations
- Unused imports
- Inconsistent naming conventions

**Success Criteria**:
- Identify 70%+ of style/performance issues
- Correctly classify severity (high vs medium)
- Reasonable false positive rate (<20%)

**Sample Code**:
```python
def process_data(data):
    result = []
    for i in range(len(data)):
        if data[i] != None:      # ⚠️ Style: use 'is not None'
            result.append(data[i] * 2)  # ⚠️ Performance: use list comp
    return result
```

---

### Task 3: Security Vulnerabilities (HARD) ⭐⭐⭐

**Difficulty**: 3/3  
**Max Steps**: 80  
**Description**: Find critical security vulnerabilities and design flaws

**Examples of Expected Vulnerabilities**:
- **SQL Injection**: String concatenation in SQL queries
- **Global State Mutation**: Unsafe global variables
- **Input Validation**: Missing checks on user input
- **Error Handling**: Silent failures, resource leaks
- **Unsafe Deserialization**: Pickle, eval() usage

**Success Criteria**:
- Identify 60%+ of critical vulnerabilities
- Low false positive rate (minimize false alarms)
- Weighted scoring favors critical bugs (0.50), high (0.30), medium (0.15)

**Sample Code**:
```python
def database_query(table, where_clause):
    # ❌ CRITICAL: SQL Injection
    query = "SELECT * FROM " + table + " WHERE " + where_clause
    result = execute_query(query)
    return result

def cache_results(user_id):
    global cache_dict  # ❌ CRITICAL: Global mutation
    if user_id not in cache_dict:
        # ❌ CRITICAL: SQL injection here too
        cache_dict[user_id] = database_query("users", "id=" + str(user_id))
    return cache_dict[user_id]
```

---

## Reward Scoring Details

### Easy Task Grader
- **Metric**: F1 Score (precision & recall equally weighted)
- **Perfect**: Find all syntax errors, 0 false positives = 1.0
- **Good**: 80%+ bugs found = 0.80+
- **Partial**: 50%+ bugs found = 0.50+
- **Poor**: <50% bugs found = <0.50

### Medium Task Grader
- **Metric**: F1 Score + Severity Bonus
- **Perfect**: All issues found with correct severity = 1.0
- **Bonus**: +0.05 per correct severity classification (max +0.15)
- **Example**: F1=0.85 + 0.10 severity bonus = 0.95

### Hard Task Grader
- **Metric**: Weighted F1 Score
- **Weights**: Critical (0.50) > High (0.30) > Medium (0.15)
- **Emphasis**: Finding critical vulnerabilities is more important than medium bugs
- **Example**: 2 critical bugs found (0.50 × 2) vs 5 medium bugs (0.15 × 5)
  - Path 1: 1.0 weighted
  - Path 2: 0.75 weighted

---

## Setup & Installation

### 1. Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/code-review-env.git
cd code-review-env
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set OpenAI API Key
```bash
export OPENAI_API_KEY="sk-your-key-here"  # On Windows: set OPENAI_API_KEY=sk-your-key-here
```

---

## Usage

### Running Locally

#### Start Flask Server
```bash
python app.py
```
Server runs on `http://localhost:7860`

#### Test Endpoints (in another terminal)

**Reset Environment**:
```bash
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_type": "easy"}'
```

**Take a Step**:
```bash
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "report_bug",
    "line_number": 2,
    "bug_description": "Missing colon",
    "severity": "critical"
  }'
```

**Get Current State**:
```bash
curl http://localhost:7860/state
```

**Get Available Tasks**:
```bash
curl http://localhost:7860/tasks
```

**Get Grader Score**:
```bash
curl http://localhost:7860/grader
```

---

### Running Baseline Inference

```bash
python baseline_inference.py
```

**Output**:
```
============================================================
CODE REVIEW OPENENV - BASELINE INFERENCE
============================================================

Running EASY task...
  Attempt 1/3... Score: 0.850
  Attempt 2/3... Score: 0.920
  Attempt 3/3... Score: 0.880
  Average: 0.883 (min: 0.850, max: 0.920)

Running MEDIUM task...
  ...

BASELINE RESULTS SUMMARY
============================================================
EASY: 0.883
MEDIUM: 0.756
HARD: 0.542

OVERALL SCORE: 0.727
============================================================
```

---

## Docker Deployment

### Build Docker Image
```bash
docker build -t code-review-env:latest .
```

### Run Container
```bash
docker run -p 7860:7860 \
  -e OPENAI_API_KEY="sk-your-key" \
  code-review-env:latest
```

### Test Container
```bash
curl http://localhost:7860/reset
```

---

## Hugging Face Spaces Deployment

1. **Create HF Space** (Docker runtime)
2. **Connect GitHub repo** with Dockerfile
3. **Add Secret**: `OPENAI_API_KEY`
4. **Space auto-deploys** on push
5. **Test**: `curl https://your-username-code-review-env.hf.space/reset`

---

## Baseline Scores

Run 3 episodes per task with gpt-3.5-turbo:

| Task | Easy | Medium | Hard | Overall |
|------|------|--------|------|---------|
| **Score** | **0.88** | **0.76** | **0.54** | **0.73** |

*Note: Scores vary based on model temperature and API randomness*

---

## Project Structure

```
code-review-env/
├── environment.py          # Core CodeReviewEnv class
├── tasks.py               # Task definitions and graders
├── baseline_inference.py  # OpenAI baseline script
├── app.py                 # Flask API server
├── openenv.yaml           # OpenEnv specification
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container configuration
├── README.md              # This file
└── baseline_results.json  # Sample baseline output
```

---

## API Reference

### POST `/reset`
Reset environment to initial state

**Request**:
```json
{
  "task_type": "easy"  // or "medium", "hard"
}
```

**Response**:
```json
{
  "observation": {...},
  "task_type": "easy",
  "status": "reset"
}
```

---

### POST `/step`
Take an action in the environment

**Request**:
```json
{
  "action_type": "report_bug",
  "line_number": 2,
  "bug_description": "Missing colon",
  "severity": "critical",
  "suggestion": null
}
```

**Response**:
```json
{
  "observation": {...},
  "reward": 0.30,
  "done": false,
  "info": {"action_type": "report_bug", "result": "true_positive"}
}
```

---

### GET `/state`
Get current environment state

**Response**:
```json
{
  "code": "def func():\n    pass",
  "current_line": 0,
  "bugs_reported": {},
  "ground_truth_bugs": {1: {...}},
  "task_type": "easy",
  "step_count": 0,
  "episode_reward": 0.0
}
```

---

### GET `/tasks`
Get list of available tasks

**Response**:
```json
{
  "tasks": [
    {
      "id": "easy",
      "name": "Syntax Error Detection",
      "description": "...",
      "difficulty": 1,
      "max_steps": 30,
      "success_criteria": "..."
    },
    ...
  ],
  "action_schema": {...}
}
```

---

### GET `/grader`
Get grader score for completed episode

**Response**:
```json
{
  "task_type": "easy",
  "score": 0.92,
  "final_state": {
    "bugs_found": 2,
    "ground_truth_bugs": 2,
    "episode_reward": 0.65
  }
}
```

---

### POST `/baseline`
Run baseline inference (requires OpenAI API key)

**Response**:
```json
{
  "status": "completed",
  "results": {
    "easy": {"score": 0.88},
    "medium": {"score": 0.76},
    "hard": {"score": 0.54}
  },
  "overall_score": 0.727
}
```

---

## Validation Checklist

- [ ] `openenv validate openenv.yaml` passes
- [ ] `docker build -t code-review-env .` succeeds
- [ ] `docker run -p 7860:7860 code-review-env` starts
- [ ] `curl http://localhost:7860/reset` returns 200
- [ ] `python baseline_inference.py` runs without errors
- [ ] All 3 tasks have graders returning 0.0-1.0
- [ ] HF Space deploys and responds
- [ ] README documents all requirements

---

## Troubleshooting

### ModuleNotFoundError: No module named 'openai'
```bash
pip install -r requirements.txt
```

### OPENAI_API_KEY not set
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

### Docker build fails
```bash
docker build --no-cache -t code-review-env .
```

### Flask port 7860 already in use
```bash
python app.py --port 8000
```

---

## Contributing

Contributions welcome! To add new code snippets:

1. Edit `environment.py` → `self.code_snippets` dict
2. Add ground truth bugs with severity levels
3. Update graders if needed
4. Test with baseline script

---

## License

MIT License - See LICENSE file

---

## Team

**Kaustubh Deshmukh** (Team Lead)  
**Priyada Patil** (Co-Developer)

OpenEnv Hackathon 2026

---

## Support

Questions? Open an issue on GitHub or contact:
- 📧 kaustubh.d365@gmail.com
- 💬 Discord: OpenEnv Hackathon Community
