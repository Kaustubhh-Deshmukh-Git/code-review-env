#!/usr/bin/env python3
"""
Inference script for Code Review OpenEnv
MANDATORY:
- Uses API_BASE_URL, MODEL_NAME, HF_TOKEN environment variables
- Complies with competition requirements
- Must be named inference.py in root directory
"""

import os
import sys
import json
import time
from typing import Dict

from openai import OpenAI
from environment import CodeReviewEnv
from baseline_inference import run_episode
from tasks import grade_episode


# MANDATORY: Get environment variables
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")

DEBUG = True


def main():
    """Main inference entry point"""
    
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
    try:
        env = CodeReviewEnv()
    except Exception as e:
        print(f"Error initializing environment: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Run baseline
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
        for attempt in range(3):
            print(f"  Attempt {attempt + 1}/3...", end=" ", flush=True)
            
            try:
                score, _ = run_episode(env, task_type, client)
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
    
    # Summary
    print("\n" + "=" * 60)
    print("BASELINE RESULTS SUMMARY")
    print("=" * 60)
    
    overall_score = sum(r["average"] for r in results.values()) / 3
    
    for task_type in ["easy", "medium", "hard"]:
        result = results[task_type]
        print(f"{task_type.upper()}: {result['average']:.3f}")
    
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
    
    return 0


if __name__ == "__main__":
    sys.exit(main())