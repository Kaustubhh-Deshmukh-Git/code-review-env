#!/usr/bin/env python3
"""
Flask server for Code Review OpenEnv
Exposes REST API endpoints for /reset, /step, /state, /baseline, /grader, /tasks
"""

from flask import Flask, request, jsonify
import json
import os
import sys
from typing import Dict, Any

from environment import CodeReviewEnv, Action, Observation
from tasks import grade_episode, TASKS


app = Flask(__name__)

# Global environment instance
env = CodeReviewEnv()
current_task = "easy"
episode_state = None


@app.route("/", methods=["GET"])
def home():
    """Home endpoint"""
    return jsonify({
        "name": "Code Review OpenEnv",
        "version": "1.0",
        "endpoints": {
            "POST /reset": "Reset environment to initial state",
            "POST /step": "Take a step in the environment",
            "GET /state": "Get current state",
            "POST /baseline": "Run baseline inference script",
            "GET /grader": "Get grader for current episode",
            "GET /tasks": "Get list of available tasks"
        }
    })


@app.route("/reset", methods=["POST"])
def reset():
    """Reset environment to initial state"""
    global env, current_task, episode_state
    
    data = request.get_json() or {}
    task_type = data.get("task_type", "easy")
    
    if task_type not in ["easy", "medium", "hard"]:
        return jsonify({"error": f"Invalid task type: {task_type}"}), 400
    
    current_task = task_type
    obs = env.reset(task_type=task_type)
    
    return jsonify({
        "observation": obs.dict(),
        "task_type": current_task,
        "status": "reset"
    }), 200


@app.route("/step", methods=["POST"])
def step():
    """Take a step in the environment"""
    global env, episode_state
    
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No action provided"}), 400
    
    try:
        # Create action from request
        action = Action(
            action_type=data.get("action_type"),
            line_number=data.get("line_number"),
            bug_description=data.get("bug_description"),
            severity=data.get("severity"),
            suggestion=data.get("suggestion")
        )
    except Exception as e:
        return jsonify({"error": f"Invalid action: {str(e)}"}), 400
    
    try:
        # Take step
        obs, reward, done, info = env.step(action)
        
        # Store episode state if done
        if done:
            episode_state = env.state()
        
        return jsonify({
            "observation": obs.dict(),
            "reward": reward,
            "done": done,
            "info": info
        }), 200
    
    except Exception as e:
        return jsonify({"error": f"Error during step: {str(e)}"}), 500


@app.route("/state", methods=["GET"])
def get_state():
    """Get current environment state"""
    global env
    
    try:
        state = env.state()
        return jsonify(state), 200
    except Exception as e:
        return jsonify({"error": f"Error getting state: {str(e)}"}), 500


@app.route("/tasks", methods=["GET"])
def get_tasks():
    """Get list of available tasks and action schema"""
    tasks_list = []
    for task_id, task_info in TASKS.items():
        tasks_list.append({
            "id": task_id,
            "name": task_info["name"],
            "description": task_info["description"],
            "difficulty": task_info["difficulty"],
            "max_steps": task_info["max_steps"],
            "success_criteria": task_info["success_criteria"]
        })
    
    action_schema = {
        "type": "object",
        "properties": {
            "action_type": {
                "type": "string",
                "enum": ["report_bug", "request_change", "approve", "skip_line"]
            },
            "line_number": {
                "type": "integer",
                "description": "Line number (0-indexed)"
            },
            "bug_description": {
                "type": "string"
            },
            "severity": {
                "type": "string",
                "enum": ["critical", "high", "medium", "low"]
            },
            "suggestion": {
                "type": "string"
            }
        },
        "required": ["action_type"]
    }
    
    return jsonify({
        "tasks": tasks_list,
        "action_schema": action_schema
    }), 200


@app.route("/grader", methods=["GET"])
def get_grader_result():
    """Get grader score for completed episode"""
    global env, episode_state, current_task
    
    if episode_state is None:
        return jsonify({"error": "No completed episode available. Run /reset and /step first."}), 400
    
    try:
        score = grade_episode(current_task, episode_state)
        
        return jsonify({
            "task_type": current_task,
            "score": score,
            "final_state": {
                "bugs_found": len(episode_state.get("bugs_reported", {})),
                "ground_truth_bugs": len(episode_state.get("ground_truth_bugs", {})),
                "episode_reward": episode_state.get("episode_reward", 0.0)
            }
        }), 200
    
    except Exception as e:
        return jsonify({"error": f"Error in grader: {str(e)}"}), 500


@app.route("/baseline", methods=["POST"])
def run_baseline():
    """Run baseline inference script"""
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return jsonify({
            "error": "OPENAI_API_KEY environment variable not set",
            "status": "failed"
        }), 500
    
    try:
        # Import and run baseline script
        from openai import OpenAI
        from baseline_inference import run_episode
        
        client = OpenAI(api_key=api_key)
        results = {}
        
        for task_type in ["easy", "medium", "hard"]:
            scores = []
            try:
                score, _ = run_episode(env, task_type, client, max_steps=50)
                scores.append(score)
            except Exception as e:
                scores.append(0.0)
            
            results[task_type] = {
                "score": scores[0] if scores else 0.0
            }
        
        overall = sum(r["score"] for r in results.values()) / 3
        
        return jsonify({
            "status": "completed",
            "results": results,
            "overall_score": overall
        }), 200
    
    except ImportError as e:
        return jsonify({
            "error": f"Missing dependency: {str(e)}",
            "status": "failed"
        }), 500
    except Exception as e:
        return jsonify({
            "error": f"Baseline inference failed: {str(e)}",
            "status": "failed"
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": [
            "/",
            "/reset",
            "/step",
            "/state",
            "/tasks",
            "/grader",
            "/baseline"
        ]
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        "error": "Internal server error",
        "message": str(error)
    }), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    debug = os.getenv("FLASK_DEBUG", "False") == "True"
    
    print(f"Starting Code Review OpenEnv server on port {port}")
    print(f"Debug mode: {debug}")
    
    app.run(host="0.0.0.0", port=port, debug=debug)
