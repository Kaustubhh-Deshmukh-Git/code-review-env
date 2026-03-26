#!/usr/bin/env python3
"""
Local validation script for Code Review OpenEnv
Tests all core functionality before submission
"""

import sys
import json
from environment import CodeReviewEnv, Action
from tasks import grade_episode, TASKS


def test_imports():
    """Test all imports work"""
    print("✓ Testing imports...")
    try:
        from environment import CodeReviewEnv, Action, Observation
        from tasks import grade_episode, TASKS
        print("  ✓ All imports successful")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_environment_creation():
    """Test environment can be created"""
    print("\n✓ Testing environment creation...")
    try:
        env = CodeReviewEnv()
        print("  ✓ Environment created successfully")
        return env
    except Exception as e:
        print(f"  ✗ Environment creation failed: {e}")
        return None


def test_reset(env):
    """Test reset functionality"""
    print("\n✓ Testing reset...")
    try:
        for task_type in ["easy", "medium", "hard"]:
            obs = env.reset(task_type=task_type)
            assert obs.code_lines, f"No code lines for {task_type}"
            assert obs.task_type == task_type, f"Task type mismatch"
            print(f"  ✓ Reset successful for {task_type}")
        return True
    except Exception as e:
        print(f"  ✗ Reset failed: {e}")
        return False


def test_step(env):
    """Test step functionality"""
    print("\n✓ Testing step...")
    try:
        env.reset(task_type="easy")
        
        # Test report_bug action
        action = Action(
            action_type="report_bug",
            line_number=2,
            bug_description="Test bug",
            severity="high"
        )
        obs, reward, done, info = env.step(action)
        
        assert isinstance(reward, float), "Reward should be float"
        assert isinstance(done, bool), "Done should be bool"
        assert isinstance(info, dict), "Info should be dict"
        
        print(f"  ✓ Step successful (reward: {reward}, done: {done})")
        
        # Test skip_line action
        action = Action(action_type="skip_line")
        obs, reward, done, info = env.step(action)
        print(f"  ✓ Skip line successful")
        
        # Test approve action
        action = Action(action_type="approve")
        obs, reward, done, info = env.step(action)
        assert done == True, "Approve should end episode"
        print(f"  ✓ Approve action successful (ended episode)")
        
        return True
    except Exception as e:
        print(f"  ✗ Step failed: {e}")
        return False


def test_state(env):
    """Test state functionality"""
    print("\n✓ Testing state...")
    try:
        env.reset(task_type="easy")
        state = env.state()
        
        assert "code" in state, "State missing 'code'"
        assert "bugs_reported" in state, "State missing 'bugs_reported'"
        assert "ground_truth_bugs" in state, "State missing 'ground_truth_bugs'"
        assert "task_type" in state, "State missing 'task_type'"
        
        print(f"  ✓ State successful")
        return True
    except Exception as e:
        print(f"  ✗ State failed: {e}")
        return False


def test_graders(env):
    """Test all graders"""
    print("\n✓ Testing graders...")
    try:
        for task_type in ["easy", "medium", "hard"]:
            env.reset(task_type=task_type)
            
            # Take some steps
            for i in range(10):
                action = Action(action_type="skip_line")
                obs, reward, done, info = env.step(action)
                if done:
                    break
            
            # Grade episode
            final_state = env.state()
            score = grade_episode(task_type, final_state)
            
            assert 0.0 <= score <= 1.0, f"Score out of range: {score}"
            print(f"  ✓ {task_type} grader: score={score:.3f}")
        
        return True
    except Exception as e:
        print(f"  ✗ Grader failed: {e}")
        return False


def test_tasks_config():
    """Test tasks configuration"""
    print("\n✓ Testing tasks configuration...")
    try:
        assert len(TASKS) == 3, f"Expected 3 tasks, got {len(TASKS)}"
        
        for task_id, task_info in TASKS.items():
            assert task_id in ["easy", "medium", "hard"], f"Invalid task ID: {task_id}"
            assert "name" in task_info, f"Task {task_id} missing 'name'"
            assert "description" in task_info, f"Task {task_id} missing 'description'"
            assert "grader_class" in task_info, f"Task {task_id} missing 'grader_class'"
            print(f"  ✓ Task '{task_id}' configured correctly")
        
        return True
    except Exception as e:
        print(f"  ✗ Tasks configuration failed: {e}")
        return False


def test_openenv_yaml():
    """Test openenv.yaml exists and is valid"""
    print("\n✓ Testing openenv.yaml...")
    try:
        import yaml
        with open("openenv.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        assert config["name"] == "code-review", "Invalid environment name"
        assert "action_schema" in config, "Missing action_schema"
        assert "observation_schema" in config, "Missing observation_schema"
        assert len(config["tasks"]) == 3, "Should have 3 tasks"
        
        print(f"  ✓ openenv.yaml is valid")
        return True
    except Exception as e:
        print(f"  ✗ openenv.yaml validation failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("CODE REVIEW OPENENV - LOCAL VALIDATION")
    print("=" * 60)
    
    results = {
        "imports": test_imports(),
    }
    
    env = test_environment_creation()
    if env:
        results["reset"] = test_reset(env)
        results["step"] = test_step(env)
        results["state"] = test_state(env)
        results["graders"] = test_graders(env)
    else:
        results["reset"] = False
        results["step"] = False
        results["state"] = False
        results["graders"] = False
    
    results["tasks_config"] = test_tasks_config()
    results["openenv_yaml"] = test_openenv_yaml()
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nResult: {passed}/{total} tests passed")
    print("=" * 60)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
