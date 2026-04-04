#!/usr/bin/env python3
"""
Inference script for Code Review OpenEnv - VALIDATOR COMPLIANT
MANDATORY:
- Uses API_BASE_URL, MODEL_NAME, HF_TOKEN environment variables
- Emits structured stdout logs in [START], [STEP], [END] format
- Must be named inference.py in root directory
- Complies with competition validator requirements
"""

import os
import sys
import json
import time
from typing import Dict, Tuple
from openai import OpenAI
from environment import CodeReviewEnv, Action
from tasks import grade_episode, TASKS


# MANDATORY: Get environment variables
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")


def emit_start(task_type: str):
    """Emit [START] marker for validator"""
    print(f"[START] task_type={task_type}", flush=True)


def emit_step(step_num: int, action_type: str, line_number: int = None, reward: float = 0.0, done: bool = False):
    """Emit [STEP] marker with structured data for validator"""
    line_str = f" line_number={line_number}" if line_number is not None else ""
    print(f"[STEP] step={step_num} action_type={action_type}{line_str} reward={reward:.3f} done={done}", flush=True)


def emit_end(task_type: str, final_score: float):
    """Emit [END] marker for validator"""
    print(f"[END] task_type={task_type} final_score={final_score:.3f}", flush=True)


def run_episode_with_logging(env: CodeReviewEnv, task_type: str, client: OpenAI) -> float:
    """
    Run a single episode with structured logging for validator
    
    Args:
        env: CodeReviewEnv instance
        task_type: "easy", "medium", or "hard"
        client: OpenAI client
    
    Returns:
        Final episode score (0.0-1.0)
    """
    # Emit START marker
    emit_start(task_type)
    
    try:
        # Reset environment
        env.reset(task_type=task_type)
        step_count = 0
        max_steps = 20
        
        # Run episode steps
        while step_count < max_steps:
            step_count += 1
            obs = env._get_observation()
            
            # Create prompt for model
            code_summary = f"Task: {task_type} - Review code for {TASKS[task_type]['description'].lower()}"
            user_prompt = f"{code_summary}\n\nCode:\n{obs.code_summary}\n\nAction?"
            
            try:
                # Call OpenAI API
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": f"You are a code reviewer. Choose action: report_bug, skip_line, or approve."},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=50,
                    temperature=0.7
                )
                
                response_text = response.choices[0].message.content.lower()
                
                # Parse action
                if "report" in response_text or "bug" in response_text:
                    action = Action(action_type="report_bug", line_number=obs.current_line, 
                                  bug_description="Code issue detected", severity="medium")
                    action_type = "report_bug"
                elif "approve" in response_text:
                    action = Action(action_type="approve")
                    action_type = "approve"
                    done = True
                else:
                    action = Action(action_type="skip_line")
                    action_type = "skip_line"
                
            except Exception as e:
                # Fallback action on API error
                action = Action(action_type="skip_line")
                action_type = "skip_line"
                done = False
            
            # Take step
            obs, reward, done, info = env.step(action)
            
            # Emit STEP marker
            line_num = action.line_number if hasattr(action, 'line_number') else None
            emit_step(
                step_num=step_count,
                action_type=action_type,
                line_number=line_num,
                reward=float(reward),
                done=done
            )
            
            if done:
                break
        
        # Grade final episode
        final_state = env.state()
        final_score = grade_episode(task_type, final_state)
        
        # Emit END marker
        emit_end(task_type, final_score)
        
        return final_score
        
    except Exception as e:
        # On error, emit END with 0.0 score
        emit_end(task_type, 0.0)
        print(f"[ERROR] {str(e)}", file=sys.stderr)
        return 0.0


def main():
    """Main inference entry point - VALIDATOR COMPLIANT"""
    
    # Validate API key
    if not API_KEY:
        print("[ERROR] OPENAI_API_KEY or HF_TOKEN not set", file=sys.stderr)
        sys.exit(1)
    
    # Create OpenAI client
    try:
        client = OpenAI(
            api_key=API_KEY,
            base_url=API_BASE_URL
        )
    except Exception as e:
        print(f"[ERROR] Failed to create OpenAI client: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Initialize environment
    try:
        env = CodeReviewEnv()
    except Exception as e:
        print(f"[ERROR] Failed to initialize environment: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Run all tasks
    results = {}
    overall_scores = []
    
    for task_type in ["easy", "medium", "hard"]:
        task_scores = []
        
        # Run 3 attempts per task
        for attempt in range(3):
            try:
                score = run_episode_with_logging(env, task_type, client)
                task_scores.append(score)
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                print(f"[ERROR] Attempt {attempt + 1} failed for {task_type}: {e}", file=sys.stderr)
                task_scores.append(0.0)
        
        # Calculate average for task
        avg_score = sum(task_scores) / len(task_scores) if task_scores else 0.0
        results[task_type] = {
            "scores": task_scores,
            "average": avg_score
        }
        overall_scores.append(avg_score)
    
    # Calculate overall score
    overall_score = sum(overall_scores) / len(overall_scores) if overall_scores else 0.0
    
    # Emit final summary (for logging, not for validator)
    print(f"\n[SUMMARY] overall_score={overall_score:.3f}", flush=True)
    
    # Save results to JSON
    output = {
        "model": MODEL_NAME,
        "api_base_url": API_BASE_URL,
        "timestamp": time.time(),
        "results": results,
        "overall_score": overall_score
    }
    
    with open("baseline_results.json", "w") as f:
        json.dump(output, f, indent=2)
    
    return 0 if overall_score > 0 else 1


if __name__ == "__main__":
    sys.exit(main())