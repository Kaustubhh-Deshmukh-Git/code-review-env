from typing import Dict, Any, List


class EasyGrader:
    """Grader for EASY task: Detect syntax errors"""
    
    @staticmethod
    def grade(final_state: dict) -> float:
        """
        Easy task: Find syntax errors (deterministic, line 2, 3, etc)
        
        Grading:
        - Perfect: Found all syntax errors and no false positives (1.0)
        - Good: Found most errors (0.7-0.9)
        - Partial: Found some errors (0.4-0.6)
        - Poor: Found few/no errors (0.0-0.3)
        """
        ground_truth = final_state.get("ground_truth_bugs", {})
        bugs_reported = final_state.get("bugs_reported", {})
        
        if not ground_truth:
            return 1.0  # No bugs = perfect
        
        true_positives = len(set(bugs_reported.keys()) & set(ground_truth.keys()))
        false_positives = len(set(bugs_reported.keys()) - set(ground_truth.keys()))
        false_negatives = len(set(ground_truth.keys()) - set(bugs_reported.keys()))
        
        # Calculate precision and recall
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        
        # F1 score
        if precision + recall == 0:
            f1_score = 0.0
        else:
            f1_score = 2 * (precision * recall) / (precision + recall)
        
        # Ensure score is between 0.0 and 1.0
        return max(0.0, min(1.0, f1_score))


class MediumGrader:
    """Grader for MEDIUM task: Detect style and performance issues"""
    
    @staticmethod
    def grade(final_state: dict) -> float:
        """
        Medium task: Find style/performance issues + severity classification
        
        Grading:
        - Perfect: Found all issues with correct severities (1.0)
        - Good: Found most issues, mostly correct severities (0.7-0.9)
        - Partial: Found some issues (0.4-0.6)
        - Poor: Found few/no issues (0.0-0.3)
        """
        ground_truth = final_state.get("ground_truth_bugs", {})
        bugs_reported = final_state.get("bugs_reported", {})
        
        if not ground_truth:
            return 1.0
        
        true_positives = len(set(bugs_reported.keys()) & set(ground_truth.keys()))
        false_positives = len(set(bugs_reported.keys()) - set(ground_truth.keys()))
        false_negatives = len(set(ground_truth.keys()) - set(bugs_reported.keys()))
        
        # Precision and recall
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        
        # F1 score
        if precision + recall == 0:
            f1_score = 0.0
        else:
            f1_score = 2 * (precision * recall) / (precision + recall)
        
        # Bonus for severity classification accuracy
        severity_bonus = 0.0
        for line in bugs_reported:
            if line in ground_truth:
                reported_severity = bugs_reported[line].get("severity", "").lower()
                true_severity = ground_truth[line].get("severity", "").lower()
                if reported_severity == true_severity:
                    severity_bonus += 0.05
        
        final_score = f1_score + min(severity_bonus, 0.15)  # Max +0.15 bonus
        return max(0.0, min(1.0, final_score))


class HardGrader:
    """Grader for HARD task: Detect security vulnerabilities and edge cases"""
    
    @staticmethod
    def grade(final_state: dict) -> float:
        """
        Hard task: Find security issues, edge cases, and design flaws
        
        Grading criteria:
        - Find critical vulnerabilities: +0.4
        - Find high severity issues: +0.3
        - Find medium severity issues: +0.2
        - Minimize false positives: penalty -0.1 each
        
        Final score uses weighted F1 with severity weighting.
        """
        ground_truth = final_state.get("ground_truth_bugs", {})
        bugs_reported = final_state.get("bugs_reported", {})
        
        if not ground_truth:
            return 1.0
        
        # Weight by severity
        severity_weights = {
            "critical": 0.50,
            "high": 0.30,
            "medium": 0.15,
            "low": 0.05
        }
        
        # Calculate weighted precision and recall
        weighted_tp = 0.0
        weighted_fp = 0.0
        weighted_fn = 0.0
        
        # True positives (correct bugs found)
        for line in set(bugs_reported.keys()) & set(ground_truth.keys()):
            severity = ground_truth[line].get("severity", "low")
            weight = severity_weights.get(severity, 0.1)
            weighted_tp += weight
        
        # False positives (bugs reported that don't exist)
        for line in set(bugs_reported.keys()) - set(ground_truth.keys()):
            weighted_fp += 0.15  # Penalty for false alarm
        
        # False negatives (bugs not found)
        for line in set(ground_truth.keys()) - set(bugs_reported.keys()):
            severity = ground_truth[line].get("severity", "low")
            weight = severity_weights.get(severity, 0.1)
            weighted_fn += weight
        
        # Weighted F1
        precision = weighted_tp / (weighted_tp + weighted_fp) if (weighted_tp + weighted_fp) > 0 else 0.0
        recall = weighted_tp / (weighted_tp + weighted_fn) if (weighted_tp + weighted_fn) > 0 else 0.0
        
        if precision + recall == 0:
            f1_score = 0.0
        else:
            f1_score = 2 * (precision * recall) / (precision + recall)
        
        return max(0.0, min(1.0, f1_score))


# Task definitions
TASKS = {
    "easy": {
        "id": "easy",
        "name": "Syntax Error Detection",
        "description": "Review code for syntax errors and obvious bugs",
        "difficulty": 0,
        "max_steps": 30,
        "grader_class": EasyGrader,
        "success_criteria": "Find syntax errors like missing colons, unclosed parentheses"
    },
    "medium": {
        "id": "medium",
        "name": "Style & Performance Issues",
        "description": "Review code for style violations, performance issues, and best practices",
        "difficulty": 1,
        "max_steps": 50,
        "grader_class": MediumGrader,
        "success_criteria": "Find style/performance issues and classify severity correctly"
    },
    "hard": {
        "id": "hard",
        "name": "Security Vulnerabilities",
        "description": "Review code for critical security vulnerabilities and design flaws",
        "difficulty": 2,
        "max_steps": 80,
        "grader_class": HardGrader,
        "success_criteria": "Find security vulnerabilities (SQL injection, global mutations, unsafe practices)"
    }
}


def grade_episode(task_type: str, final_state: dict) -> float:
    """
    Grade an episode based on task type
    
    Args:
        task_type: "easy", "medium", or "hard"
        final_state: Final state dict from environment
    
    Returns:
        Score between 0.0 and 1.0
    """
    if task_type not in TASKS:
        raise ValueError(f"Unknown task type: {task_type}")
    
    grader_class = TASKS[task_type]["grader_class"]
    return grader_class.grade(final_state)
