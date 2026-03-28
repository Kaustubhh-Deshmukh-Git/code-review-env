#!/usr/bin/env python3
"""
Baseline inference script for Code Review OpenEnv
Uses OpenAI API to run a model against the environment
MANDATORY: Uses API_BASE_URL, MODEL_NAME, HF_TOKEN environment variables
"""

import os
import sys
import json
from typing import Dict, List
import time

from openai import OpenAI
from environment import CodeReviewEnv, Action
from tasks import grade_episode, TASKS

# MANDATORY: Get environment variables
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")

DEBUG = True


def create_system_prompt(task_type: str) -> str:
    """Create system prompt for the agent"""
    task_info = TASKS[task_type]
    return f"""You are an expert code reviewer. Your task is to {task_info['description'].lower()}.

Task: {task_info['name']}
Difficulty: {task_info['difficulty'] + 1}/3
Success Criteria: {task_info['success_criteria']}

You will review code line by line. For each line, you can:
1. report_bug: Report a bug with severity (critical, high, medium, low)
2. request_change: Request a code improvement
3. skip_line: Skip this line and move to next
4. approve: Complete the review

Respond in JSON format with these fields:
- action_type: "report_bug", "request_change", "skip_line", or "approve"
- line_number: Line number if reporting bug (1-indexed)
- bug_description: Description of bug (if reporting)
- severity: Severity level (if reporting) - critical, high, medium, low
- reasoning: Brief explanation of your action

Be thorough but precise. Minimize false positives."""


def parse_agent_response(response_text: str) -> dict:
    """Parse agent response to extract action"""
    try:
        # Try to extract JSON from response
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start >= 0 and end > start:
            json_str = response_text[start:end]
            return json.loads(json_str)
    except:
        pass
    
    # Fallback: default to skip_line
    return {"action_type": "skip_line"}


def run_episode(env: CodeReviewEnv, task_type: str, client, max_steps: int = 50) -> tuple:
    """
    Run a single episode with the agent
    
    Args:
        env: CodeReviewEnv instance
        task_type: "easy", "medium", or "hard"
        client: OpenAI client
        max_steps: Maximum steps per episode
    
    Returns:
        Tuple of (final_score, episode_history)
    """
    env.reset(task_type=task_type)
    system_prompt = create_system_prompt(task_type)
    
    conversation_history = []
    episode_history = []
    
    for step in range(max_steps):
        obs = env._get_observation()
        
        # Format observation for agent
        obs_text = f"""Current observation:
Code being reviewed:
{chr(10).join(obs.code_lines)}

Current line under review: {obs.current_line}
Code summary: {obs.code_summary}
Progress: {obs.episode_progress:.0%}
Bugs found so far: {len(obs.bugs_found_so_far)}

Available actions: {', '.join(obs.available_actions)}

What is your next action?"""
        
        # Get agent response
        conversation_history.append({
            "role": "user",
            "content": obs_text
        })
        
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,  # ✅ Uses environment variable
                messages=[{"role": "system", "content": system_prompt}] + conversation_history,
                temperature=0.7,
                max_tokens=200
            )
            
            agent_response = response.choices[0].message.content
            conversation_history.append({
                "role": "assistant",
                "content": agent_response
            })
            
            # Parse response
            action_dict = parse_agent_response(agent_response)
            
            # Create action
            action = Action(
                action_type=action_dict.get("action_type", "skip_line"),
                line_number=action_dict.get("line_number"),
                bug_description=action_dict.get("bug_description"),
                severity=action_dict.get("severity"),
                suggestion=action_dict.get("suggestion")
            )
            
        except Exception as e:
            print(f"Error calling OpenAI API: {e}", file=sys.stderr)
            action = Action(action_type="skip_line")
        
        # Take step
        obs, reward, done, info = env.step(action)
        
        episode_history.append({
            "step": step,
            "action": action.dict(),
            "reward": reward,
            "info": info
        })
        
        if done:
            break
    
    # Grade episode
    final_state = env.state()
    score = grade_episode(task_type, final_state)
    
    return score, episode_history


def main():
    """Main baseline script"""
    
    # Validate API key
    if not API_KEY:
        print("Error: OPENAI_API_KEY or HF_TOKEN not set", file=sys.stderr)
        sys.exit(1)
    
    if DEBUG:
        print(f"Using Model: {MODEL_NAME}")
        print(f"Using API Base URL: {API_BASE_URL}")
        print()
    
    # Create OpenAI client with environment variables
    try:
        client = OpenAI(
            api_key=API_KEY,
            base_url=API_BASE_URL
        )
    except Exception as e:
        print(f"Error creating OpenAI client: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Initialize environment
    env = CodeReviewEnv()
    
    # Run baseline on all tasks
    results = {}
    print("=" * 60)
    print("CODE REVIEW OPENENV - BASELINE INFERENCE")
    print(f"Model: {MODEL_NAME}")
    print(f"API Base URL: {API_BASE_URL}")
    print("=" * 60)
    
    for task_type in ["easy", "medium", "hard"]:
        print(f"\nRunning {task_type.upper()} task...")
        print("-" * 40)
        
        task_scores = []
        for attempt in range(3):  # Run 3 attempts per task
            print(f"  Attempt {attempt + 1}/3...", end=" ", flush=True)
            
            try:
                score, history = run_episode(env, task_type, client)
                task_scores.append(score)
                print(f"Score: {score:.3f}")
                time.sleep(1)  # Rate limiting
            except Exception as e:
                print(f"Error: {e}")
                task_scores.append(0.0)
        
        avg_score = sum(task_scores) / len(task_scores)
        results[task_type] = {
            "scores": task_scores,
            "average": avg_score,
            "min": min(task_scores),
            "max": max(task_scores)
        }
        print(f"  Average: {avg_score:.3f} (min: {min(task_scores):.3f}, max: {max(task_scores):.3f})")
    
    # Print summary
    print("\n" + "=" * 60)
    print("BASELINE RESULTS SUMMARY")
    print("=" * 60)
    
    overall_score = 0.0
    for task_type in ["easy", "medium", "hard"]:
        task_result = results[task_type]
        print(f"\n{task_type.upper()}: {task_result['average']:.3f}")
        print(f"  Scores: {[f'{s:.3f}' for s in task_result['scores']]}")
        overall_score += task_result['average']
    
    overall_score /= 3
    print(f"\nOVERALL SCORE: {overall_score:.3f}")
    print("=" * 60)
    
    # Save results
    output = {
        "model": MODEL_NAME,
        "api_base_url": API_BASE_URL,
        "timestamp": time.time(),
        "results": results,
        "overall_score": overall_score
    }
    
    with open("baseline_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nResults saved to baseline_results.json")
    
    return results


if __name__ == "__main__":
    main()