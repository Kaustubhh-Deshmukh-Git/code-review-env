# 🚀 Code Review OpenEnv - Quick Start Guide

## Complete Setup in 15 Minutes

This guide will help you and Priyada get the Code Review environment ready for submission by April 7th.

---

## 📋 Pre-Submission Checklist

- [ ] Downloaded all files from outputs
- [ ] Created GitHub repository  
- [ ] Set up local development
- [ ] Tested locally
- [ ] Created HF Space
- [ ] Deployed to HF Spaces
- [ ] Ran baseline inference
- [ ] All validation tests pass

---

## Step 1: GitHub Setup (5 min)

**Kaustubh** does these:

```bash
# 1. Create new GitHub repo (public)
# Name: code-review-env
# Description: Code Review OpenEnv environment for AI agents

# 2. Clone locally
git clone https://github.com/YOUR_USERNAME/code-review-env.git
cd code-review-env

# 3. Add all files from outputs folder
cp /path/to/downloaded/files/* .

# 4. Add .gitignore (included)
# Already in downloaded files

# 5. Make initial commit
git add .
git commit -m "Initial commit: Code Review OpenEnv"
git push origin main
```

**Priyada** does these:

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/code-review-env.git
cd code-review-env

# Verify all files are there
ls -la
```

---

## Step 2: Local Setup (5 min)

**Both do this:**

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set OpenAI API key
export OPENAI_API_KEY="sk-your-actual-key-here"
# Windows: set OPENAI_API_KEY=sk-your-actual-key-here

# 4. Verify installation
python -c "import environment, tasks, flask; print('✓ All packages OK')"
```

---

## Step 3: Local Testing (3 min)

```bash
# Run validation tests
python test_validation.py

# Expected output:
# ✓ PASS: imports
# ✓ PASS: environment_creation
# ✓ PASS: reset
# ✓ PASS: step
# ✓ PASS: state
# ✓ PASS: graders
# ✓ PASS: tasks_config
# Result: X/X tests passed
```

---

## Step 4: Start Local Server (2 min)

```bash
# Terminal 1: Start Flask server
python app.py

# You should see:
# Starting Code Review OpenEnv server on port 7860
# * Running on http://0.0.0.0:7860
```

---

## Step 5: Test Endpoints (2 min)

**In another terminal:**

```bash
# Test 1: Reset
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_type": "easy"}'

# Test 2: Get tasks
curl http://localhost:7860/tasks

# Test 3: Take a step
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "report_bug",
    "line_number": 2,
    "bug_description": "Missing colon",
    "severity": "critical"
  }'

# All should return 200 OK
```

---

## Step 6: Run Baseline (1 min)

```bash
# Terminal 1: Stop Flask server (Ctrl+C)

# Terminal 2: Run baseline
python baseline_inference.py

# Expected output:
# ============================================================
# CODE REVIEW OPENENV - BASELINE INFERENCE
# ============================================================
# Running EASY task...
#   Attempt 1/3... Score: 0.xxx
#   Attempt 2/3... Score: 0.xxx
#   Attempt 3/3... Score: 0.xxx
#   Average: 0.xxx
# Running MEDIUM task...
# Running HARD task...
# BASELINE RESULTS SUMMARY
# EASY: 0.xxx
# MEDIUM: 0.xxx
# HARD: 0.xxx
# OVERALL SCORE: 0.xxx
```

---

## Step 7: Docker Test (2 min)

```bash
# Build image
docker build -t code-review-env .

# Run container (set API key first!)
docker run -p 7860:7860 \
  -e OPENAI_API_KEY="sk-your-key" \
  code-review-env

# Test from another terminal
curl http://localhost:7860/reset

# Should return 200 OK
```

---

## Step 8: Hugging Face Spaces Deployment (5 min)

### Option A: Manual (Recommended)

1. **Go to** https://huggingface.co/spaces/create

2. **Fill form:**
   - Space name: `code-review-env`
   - License: MIT
   - Visibility: Public
   - Space SDK: Docker

3. **Click "Create"**

4. **In your Space settings (gear icon):**
   - Go to "Repository"
   - Add secret: `OPENAI_API_KEY` = `sk-your-key`

5. **Push to Space:**
   ```bash
   git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/code-review-env
   git push hf main
   ```

6. **Wait for build** (~3-5 minutes)

7. **Test Space:**
   ```bash
   curl https://YOUR_USERNAME-code-review-env.hf.space/reset
   ```

---

## File Structure Verification

Verify your repo has this structure:

```
code-review-env/
├── environment.py              ✓
├── tasks.py                   ✓
├── baseline_inference.py      ✓
├── app.py                     ✓
├── openenv.yaml               ✓
├── requirements.txt           ✓
├── Dockerfile                 ✓
├── test_validation.py         ✓
├── README.md                  ✓
├── SETUP_GUIDE.md            ✓
└── .gitignore                ✓
```

---

## Pre-Submission Validation

Run this checklist before submitting:

```bash
# ✓ All tests pass
python test_validation.py

# ✓ Baseline runs without errors
python baseline_inference.py

# ✓ Docker builds
docker build -t code-review-env .

# ✓ Server runs
python app.py &
sleep 2
curl http://localhost:7860/reset
kill %1

# ✓ HF Space responds
curl https://YOUR_USERNAME-code-review-env.hf.space/reset
# Should return 200

# ✓ Files committed
git status
# Should be "nothing to commit, working tree clean"
```

---

## Submission Details

**Deadline:** April 7, 11:59 PM IST

**What to submit:**
1. GitHub repo link: https://github.com/YOUR_USERNAME/code-review-env
2. HF Space link: https://huggingface.co/spaces/YOUR_USERNAME/code-review-env

**Submission platform:** (Will be revealed on competition dashboard)

---

## Common Issues & Fixes

### Issue: `ModuleNotFoundError: No module named 'openai'`
```bash
pip install -r requirements.txt
pip list | grep openai  # Verify installation
```

### Issue: `OPENAI_API_KEY not set`
```bash
export OPENAI_API_KEY="sk-..."
echo $OPENAI_API_KEY  # Verify
```

### Issue: Port 7860 already in use
```bash
# Find and kill process
lsof -i :7860
kill -9 <PID>
# Or use different port
python app.py --port 8000
```

### Issue: Docker build fails
```bash
docker build --no-cache -t code-review-env .
```

### Issue: HF Space build fails
- Check CloudWatch logs in Space settings
- Verify `OPENAI_API_KEY` secret is set
- Ensure `.gitignore` excludes `.env` files

---

## File Purposes Quick Reference

| File | Purpose |
|------|---------|
| `environment.py` | Core environment with reset/step/state |
| `tasks.py` | 3 task graders (easy/medium/hard) |
| `baseline_inference.py` | OpenAI API baseline script |
| `app.py` | Flask server with 6 endpoints |
| `openenv.yaml` | OpenEnv specification |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Container configuration |
| `test_validation.py` | Local validation tests |
| `README.md` | Full documentation |

---

## Timeline for Your Team

| Date | Task | Owner |
|------|------|-------|
| Today | Setup GitHub + local dev | Kaustubh |
| Today | Test all 3 tasks locally | Both |
| Tomorrow | Deploy to HF Spaces | Kaustubh |
| Tomorrow | Verify all endpoints | Priyada |
| April 5 | Final validation + polish | Both |
| April 7 | Submit | Kaustubh |

---

## Support Resources

- **Discord:** Join OpenEnv Hackathon community for help
- **Email:** help_openenvhackathon@scaler.com
- **GitHub Issues:** Document any bugs you find

---

## Key Scoring Tips

Remember the rubric:

1. **Real-World Utility (30%)** ✓ Code review is genuine task
2. **Task & Grader Quality (25%)** ✓ 3 graders with clear metrics
3. **Environment Design (20%)** ✓ Good reward shaping, state management
4. **Code Quality & Spec (15%)** ✓ Follows OpenEnv, clean code
5. **Creativity & Novelty (10%)** ✓ Security focus is novel

**You should score well on all dimensions!** 🎯

---

## Final Checklist Before April 7

- [ ] GitHub repo created and pushed
- [ ] HF Space deployed and responding
- [ ] All tests pass locally
- [ ] Baseline inference runs successfully
- [ ] Docker builds without errors
- [ ] README fully documented
- [ ] All 3 tasks have working graders
- [ ] API endpoints all functional
- [ ] Team is ready to submit

---

**Good luck! 🚀 You've got this!**

Questions? Reach out to your team or the OpenEnv community on Discord.
