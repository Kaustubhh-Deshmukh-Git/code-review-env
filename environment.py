from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import json
from enum import Enum
import random
import string
import ast


class BugSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionType(str, Enum):
    REPORT_BUG = "report_bug"
    REQUEST_CHANGE = "request_change"
    APPROVE = "approve"
    SKIP_LINE = "skip_line"


class Action(BaseModel):
    action_type: str  # "report_bug", "request_change", "approve", "skip_line"
    line_number: Optional[int] = None
    bug_description: Optional[str] = None
    severity: Optional[str] = None  # "critical", "high", "medium", "low"
    suggestion: Optional[str] = None


class Observation(BaseModel):
    code_lines: List[str]  # List of code lines with line numbers
    current_line: int  # Agent currently reviewing this line
    bugs_found_so_far: Dict[int, Dict[str, Any]]  # {line_no: {severity, description}}
    available_actions: List[str]  # ["report_bug", "request_change", "approve", "skip_line"]
    episode_progress: float  # 0.0 to 1.0
    task_type: str  # "easy", "medium", "hard"
    code_summary: str  # Brief description of what code does


class Reward(BaseModel):
    score: float  # 0.0 to 1.0 partial reward
    partial_progress: float  # Progress towards task
    done: bool
    info: Dict[str, Any]


class CodeReviewEnv:
    """Code Review Environment for OpenEnv"""
    
    def __init__(self):
        self.code_snippets = {
            "easy": [
                {
                    "code": """def calculate_sum(numbers):
    total = 0
    for num in numbers
        total = total + num
    return total
""",
                    "bugs": {
                        2: {"severity": "critical", "description": "Missing colon after for loop"},
                    },
                    "description": "Function to sum numbers with syntax error"
                },
                {
                    "code": """def find_max(arr):
    max_val = arr[0]
    for i in range(len(arr)
        if arr[i] > max_val:
            max_val = arr[i]
    return max_val
""",
                    "bugs": {
                        3: {"severity": "critical", "description": "Missing closing parenthesis in range()"},
                    },
                    "description": "Function to find maximum value with syntax error"
                },
            ],
            "medium": [
                {
                    "code": """def process_data(data):
    result = []
    for i in range(len(data)):
        if data[i] != None:
            result.append(data[i] * 2)
    return result
""",
                    "bugs": {
                        4: {"severity": "high", "description": "Use 'is not None' instead of '!= None'"},
                        5: {"severity": "medium", "description": "Inefficient list append in loop, use list comprehension"},
                    },
                    "description": "Data processing with style and performance issues"
                },
                {
                    "code": """def fetch_user_data(user_id):
    users = {}
    # Missing input validation
    data = database.query(user_id)
    for item in data:
        users[item] = data[item]
    return users
""",
                    "bugs": {
                        4: {"severity": "high", "description": "No input validation for user_id"},
                        5: {"severity": "medium", "description": "Missing error handling for database query"},
                    },
                    "description": "Function with validation and error handling issues"
                },
            ],
            "hard": [
                {
                    "code": """def parse_json_and_process(data_str):
    import json
    data = json.loads(data_str)
    result = []
    for key in data:
        result.append(data[key])
    return ''.join(result)
""",
                    "bugs": {
                        2: {"severity": "high", "description": "Import inside function, should be at module level"},
                        4: {"severity": "critical", "description": "No try-except for json.loads(), will crash on invalid JSON"},
                        6: {"severity": "high", "description": "join() requires strings, data values might be non-string types"},
                    },
                    "description": "JSON parsing with security and robustness issues"
                },
                {
                    "code": """def database_query(table, where_clause):
    query = "SELECT * FROM " + table + " WHERE " + where_clause
    result = execute_query(query)
    return result

def cache_results(user_id):
    global cache_dict
    if user_id not in cache_dict:
        cache_dict[user_id] = database_query("users", "id=" + str(user_id))
    return cache_dict[user_id]
""",
                    "bugs": {
                        2: {"severity": "critical", "description": "SQL injection vulnerability: string concatenation instead of parameterized queries"},
                        7: {"severity": "critical", "description": "Global variable mutation, poor state management"},
                        8: {"severity": "high", "description": "SQL injection in where_clause construction"},
                    },
                    "description": "Database code with critical security vulnerabilities"
                },
            ]
        }
        self.reset()
    
    def reset(self, task_type: str = "easy"):
        """Reset environment to initial state"""
        self.task_type = task_type
        snippet = random.choice(self.code_snippets[task_type])
        
        self.code = snippet["code"]
        self.code_lines = self.code.split('\n')
        self.ground_truth_bugs = snippet["bugs"]
        self.code_summary = snippet["description"]
        
        self.current_line = 0
        self.bugs_reported = {}  # {line_no: {severity, description}}
        self.step_count = 0
        self.max_steps = len(self.code_lines) * 2 + 10
        self.episode_reward = 0.0
        
        return self._get_observation()
    
    def _get_observation(self) -> Observation:
        """Get current observation"""
        code_display = []
        for i, line in enumerate(self.code_lines):
            code_display.append(f"{i:2d}: {line}")
        
        progress = min(self.step_count / self.max_steps, 1.0)
        
        return Observation(
            code_lines=code_display,
            current_line=self.current_line,
            bugs_found_so_far=self.bugs_reported,
            available_actions=["report_bug", "request_change", "approve", "skip_line"],
            episode_progress=progress,
            task_type=self.task_type,
            code_summary=self.code_summary
        )
    
    def step(self, action: Action) -> tuple[Observation, float, bool, dict]:
        """Process agent action"""
        self.step_count += 1
        reward = 0.0
        done = False
        info = {"action_type": action.action_type}
        
        if action.action_type == "report_bug":
            reward, info = self._handle_report_bug(action, info)
        
        elif action.action_type == "skip_line":
            if self.current_line < len(self.code_lines) - 1:
                self.current_line += 1
            reward = 0.0
        
        elif action.action_type == "approve":
            # End review, calculate final score
            done = True
            reward = self._calculate_final_reward()
        
        elif action.action_type == "request_change":
            # Neutral action, no immediate reward
            reward = 0.01
        
        # Check if max steps reached
        if self.step_count >= self.max_steps:
            done = True
            if not reward:
                reward = self._calculate_final_reward()
        
        self.episode_reward += reward
        
        return self._get_observation(), reward, done, info
    
    def _handle_report_bug(self, action: Action, info: dict) -> tuple[float, dict]:
        """Handle bug report action"""
        line = action.line_number
        reward = 0.0
        
        if line not in self.ground_truth_bugs:
            # False positive
            reward = -0.15
            info["result"] = "false_positive"
            info["message"] = "Bug reported but not found"
        else:
            # True positive
            true_severity = self.ground_truth_bugs[line]["severity"]
            
            # Reward for finding bug
            reward += 0.30
            
            # Bonus for correct severity
            if action.severity and action.severity.lower() == true_severity:
                reward += 0.10
            else:
                reward -= 0.05
            
            self.bugs_reported[line] = {
                "severity": action.severity or "unknown",
                "description": action.bug_description or ""
            }
            info["result"] = "true_positive"
            info["message"] = f"Bug found! True severity: {true_severity}"
        
        # Move to next line after reporting
        if self.current_line < len(self.code_lines) - 1:
            self.current_line += 1
        
        return reward, info
    
    def _calculate_final_reward(self) -> float:
        """Calculate final episode reward based on accuracy"""
        if not self.ground_truth_bugs:
            return 1.0  # Perfect score if no bugs
        
        true_positives = len(set(self.bugs_reported.keys()) & set(self.ground_truth_bugs.keys()))
        false_positives = len(set(self.bugs_reported.keys()) - set(self.ground_truth_bugs.keys()))
        false_negatives = len(set(self.ground_truth_bugs.keys()) - set(self.bugs_reported.keys()))
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        
        # F1 score as final reward
        if precision + recall == 0:
            f1_score = 0.0
        else:
            f1_score = 2 * (precision * recall) / (precision + recall)
        
        return max(0.0, min(1.0, f1_score))
    
    def state(self) -> dict:
        """Return current state"""
        return {
            "code": self.code,
            "current_line": self.current_line,
            "bugs_reported": self.bugs_reported,
            "ground_truth_bugs": self.ground_truth_bugs,
            "task_type": self.task_type,
            "step_count": self.step_count,
            "episode_reward": self.episode_reward
        }
