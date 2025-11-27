# Quick Start: Fix Natural Copilot Issues

**Problem**: Answers are too verbose and robotic. "What was my ROAS last month?" gets a 3-paragraph analysis when users want a simple number.

**Solution**: 4-week roadmap to natural, context-appropriate answers.

---

## 🐛 Critical Bug Found

**Workspace Average Calculation**

Your suspicion was correct! The workspace_avg is showing the same value as summary:
```json
{
  "summary": 3.877...,
  "workspace_avg": 3.877...  // ← Bug: should be different!
}
```

**Why this happens**: The `_calculate_workspace_avg()` function might be applying the same filters as the main query instead of calculating across ALL workspace data.

**Fix**: See `ROADMAP_TO_NATURAL_COPILOT.md` → Phase 1, Task 1.1

---

## 📋 The Fix Plan (4 Weeks)

### Week 1: Fix Critical Bugs ⚠️
1. **Fix workspace avg** - Should ignore query filters
2. **Intent classification** - Detect if user wants simple vs detailed answer
3. **Simple answer mode** - "Your ROAS last month was 3.88×" (1 sentence)

**Deliverable**: Simple questions get simple answers

**Implementation Guide**: 
- 📋 Detailed spec: [PHASE_1_IMPLEMENTATION_SPEC.md](./PHASE_1_IMPLEMENTATION_SPEC.md)
- 🤖 AI prompt: [AI_PROMPT_PHASE_1.md](./AI_PROMPT_PHASE_1.md)

---

### Week 2: Natural Language Polish ✨
1. **Better prompts** - Sound human, not robotic
2. **Retry logic** - Make GPT more reliable
3. **Remove formality** - Use contractions, casual tone

**Deliverable**: Answers sound like a colleague, not a report

---

### Week 3: More Question Coverage 📈
1. **Acknowledge filters** - "Your Google campaigns are at 4.2×"
2. **Test questions 1-75** - Basic, comparisons, breakdowns, filters
3. **Gap analysis** - Document what we can't answer yet

**Deliverable**: 80%+ of questions 1-75 answered well

---

### Week 4: Testing & Validation 🧪
1. **Build test harness** - Automated testing of 100 questions
2. **Manual review** - Rate answer quality 1-5 stars
3. **Iterate** - Fix low-rated answers

**Deliverable**: 90% of questions get 4+ star ratings

---

## 🎯 How Intent Classification Works

```python
# SIMPLE: Just the facts
Q: "what was my roas last month"
A: "Your ROAS last month was 3.88×"  # ✅ One sentence

# COMPARATIVE: Show me differences  
Q: "how does my roas compare to last month"
A: "Your ROAS is 3.88× this month, up 12% from last month's 3.46×"  # ✅ Comparison

# ANALYTICAL: Explain the why
Q: "why is my roas so volatile"
A: "Your ROAS has been volatile, ranging from 1.38× to 5.80×..."  # ✅ Full analysis
```

**How we detect it**:
- Simple: Starts with "what/how much/how many", no comparison requested
- Comparative: Contains "compare/vs/versus", OR DSL has breakdown/comparison
- Analytical: Contains "why/explain/analyze/trend"

---

## 📁 New Files We'll Create

```
backend/app/answer/
├── context_extractor.py     # ✅ Already exists (v2.0.1)
├── intent_classifier.py     # 🆕 NEW - Detect question intent
└── answer_builder.py        # ✏️ MODIFY - Use intent to adjust depth
```

---

## 🚀 Start Today: Debug the Bug

**Step 1**: Add logging to see what's happening

```bash
cd backend
```

Edit `app/dsl/executor.py`, find `_calculate_workspace_avg()`:

```python
def _calculate_workspace_avg(...):
    try:
        # ... existing code ...
        
        logger.info(f"[WORKSPACE AVG DEBUG] Calculating for metric: {metric}")
        logger.info(f"[WORKSPACE AVG DEBUG] Time range: {time_range}")
        logger.info(f"[WORKSPACE AVG DEBUG] Query: {query}")
        
        row = query.first()
        
        logger.info(f"[WORKSPACE AVG DEBUG] Result row: {row}")
        logger.info(f"[WORKSPACE AVG DEBUG] Base measures: {base_measures}")
        logger.info(f"[WORKSPACE AVG DEBUG] Workspace avg: {workspace_avg}")
        
        return workspace_avg
```

**Step 2**: Run a query and check the logs

```bash
# Start server
uvicorn app.main:app --reload

# In another terminal, make a request
curl -X POST http://localhost:8000/qa/?workspace_id=<ID> \
  -H "Content-Type: application/json" \
  -d '{"question": "what was my roas last month"}'

# Check server logs for [WORKSPACE AVG DEBUG] lines
```

**Step 3**: Analyze the logs

Look for:
- ✅ Is the query filtering by anything? (Should be workspace_id ONLY)
- ✅ Are the base measures different from the main query?
- ✅ Is workspace_avg different from summary?

---

## 📊 Expected Results After Week 1

**Before** (Current):
```
Q: "what was my roas last month"
A: "Your ROAS is stable at 3.88×, which is right in line with your workspace 
average of 3.88×. Over time, it has shown some volatility, peaking at 5.80× 
and dipping as low as 1.38× recently. While the current performance is average, 
keeping an eye on these fluctuations could help you identify opportunities for 
improvement."
```

**After** (Week 1):
```
Q: "what was my roas last month"
A: "Your ROAS last month was 3.88×"  # ✅ Simple!

Q: "how does my roas compare to last month"
A: "Your ROAS is 3.88× this month, up from 3.46× last month—that's a 12% improvement"  # ✅ Comparative

Q: "why is my roas volatile"
A: "Your ROAS has been quite volatile this month, swinging from a low of 1.38× 
to a high of 5.80×. The volatility seems to come from inconsistent daily 
performance across your campaigns."  # ✅ Analytical
```

---

## 🎯 Success Criteria

### Week 1
- [ ] Workspace avg ≠ summary (bug fixed)
- [ ] Simple questions = 1 sentence answers
- [ ] 10 test questions all pass

### Week 2  
- [ ] No more "Your X for the selected period is..."
- [ ] Answers sound conversational
- [ ] GPT success rate >95%

### Week 3
- [ ] "Google campaigns..." acknowledges filter
- [ ] Questions 1-75: 80% coverage

### Week 4
- [ ] Automated test harness working
- [ ] 90% questions get 4+ stars
- [ ] Process documented

---

## 📚 Documentation References

- **Full Roadmap**: `backend/docs/ROADMAP_TO_NATURAL_COPILOT.md`
- **Architecture**: `backend/docs/QA_SYSTEM_ARCHITECTURE.md`
- **Test Questions**: `backend/docs/100-realistic-questions.md`
- **Build Log**: `docs/metricx_BUILD_LOG.md`

---

## 💡 Philosophy

**Let AI do its thing**:
- Don't over-engineer templates
- Let GPT be creative (but controlled)
- Match response to user intent

**Focus on fundamentals**:
- Clean architecture (separation of concerns)
- Good documentation (always up to date)
- Test-driven development

**Simple > Complex**:
- Start with intent classification (simple logic)
- Add complexity only if needed
- Always question if we're overthinking

---

_Ready to start? Begin with debugging the workspace avg bug, then move to intent classification._

