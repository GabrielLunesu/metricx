# AI Implementation Prompt: Phase 1 - Natural Copilot

**Copy this entire prompt to your AI IDE (Cursor, GitHub Copilot, etc.) to implement Phase 1.**

---

## Context

We're building metricx, a marketing analytics copilot. The QA system currently gives overly verbose, robotic answers. We need to fix critical bugs and make answers natural and context-appropriate.

**Current Problem**:
```
Q: "what was my roas last month"
A: "Your ROAS is stable at 3.88×, which is right in line with your workspace average of 3.88×. Over time, it has shown some volatility, peaking at 5.80× and dipping as low as 1.38× recently. While the current performance is average, keeping an eye on these fluctuations could help you identify opportunities for improvement."
```
☝️ Too verbose! User just wants: "Your ROAS last month was 3.88×"

**Goal**: Simple questions get simple answers. Comparative questions get comparisons. Analytical questions get full context.

---

## Task Overview

Implement Phase 1 of the Natural Copilot roadmap:

1. **Fix workspace average bug** - `workspace_avg` is incorrectly showing same value as `summary`
2. **Create intent classifier** - Detect if question is SIMPLE/COMPARATIVE/ANALYTICAL
3. **Add intent-specific prompts** - Different GPT prompts for each intent
4. **Integrate into answer builder** - Wire everything together
5. **Test and verify** - Ensure quality improves

**Timeline**: 5 days

**Reference Docs**:
- `/Users/gabriellunesu/Git/metricx/backend/docs/PHASE_1_IMPLEMENTATION_SPEC.md` - Full detailed spec
- `/Users/gabriellunesu/Git/metricx/backend/docs/ROADMAP_TO_NATURAL_COPILOT.md` - Overall strategy
- `/Users/gabriellunesu/Git/metricx/backend/docs/100-realistic-questions.md` - Test questions

---

## Step-by-Step Implementation

### STEP 1: Fix Workspace Average Bug 🐛

**Problem**: 
```json
{
  "summary": 3.877...,
  "workspace_avg": 3.877...  // ← Bug! Should be different
}
```

**Root Cause**: `_calculate_workspace_avg()` might be applying query filters when it should calculate across ALL workspace data.

**Action**:

1. **Add debug logging** to `backend/app/dsl/executor.py` in the `_calculate_workspace_avg()` function (around line 605)
   - Log what filters are being applied
   - Log the calculated workspace avg
   - Log base measures
   - Use `[WORKSPACE_AVG]` prefix for easy filtering

2. **Create test file**: `backend/app/tests/test_workspace_avg.py`
   - Test that workspace_avg ≠ summary when provider filter is applied
   - Test that workspace_avg ignores status filter
   - Test that workspace_avg == summary when no filters
   - See full test code in `PHASE_1_IMPLEMENTATION_SPEC.md` → Task 1, Step 1.2

3. **Run test to confirm bug**:
   ```bash
   cd backend
   pytest app/tests/test_workspace_avg.py -v -s
   ```

4. **Fix the bug**: Ensure `_calculate_workspace_avg()` only applies `workspace_id` and `time_range` filters, NOTHING else

5. **Verify fix**: All tests in `test_workspace_avg.py` should PASS ✅

**Success Criteria**:
- ✅ Tests pass
- ✅ Logs show workspace avg calculated without filters
- ✅ workspace_avg ≠ summary when query has filters

---

### STEP 2: Create Intent Classifier 🎯

**Goal**: Detect if user wants simple/comparative/analytical answer

**Action**:

1. **Create new file**: `backend/app/answer/intent_classifier.py`
   - Define `AnswerIntent` enum (SIMPLE, COMPARATIVE, ANALYTICAL)
   - Implement `classify_intent(question, query)` function
   - Use keyword matching + DSL structure analysis
   - See full code in `PHASE_1_IMPLEMENTATION_SPEC.md` → Task 2, Step 2.1

2. **Classification logic**:
   - **SIMPLE**: Starts with "what/how much/how many" + NO comparison in DSL
   - **COMPARATIVE**: Contains "compare/vs/which/better" OR DSL has breakdown/comparison
   - **ANALYTICAL**: Contains "why/explain/analyze/trend"

3. **Create test file**: `backend/app/tests/test_intent_classifier.py`
   - Test simple questions → SIMPLE
   - Test comparative questions → COMPARATIVE
   - Test analytical questions → ANALYTICAL
   - Test edge cases
   - See full test code in `PHASE_1_IMPLEMENTATION_SPEC.md` → Task 2, Step 2.2

4. **Run tests**:
   ```bash
   pytest app/tests/test_intent_classifier.py -v
   ```

**Success Criteria**:
- ✅ All tests pass
- ✅ "what was my roas" → SIMPLE
- ✅ "compare google vs meta" → COMPARATIVE
- ✅ "why is my roas low" → ANALYTICAL

---

### STEP 3: Add Intent-Specific Prompts 💬

**Goal**: Create 3 different GPT prompts for different intent levels

**Action**:

1. **Modify**: `backend/app/nlp/prompts.py` (around line 660, after `ANSWER_GENERATION_PROMPT`)

2. **Add 3 new prompts**:
   - `SIMPLE_ANSWER_PROMPT`: "Answer in ONE sentence. No analysis."
   - `COMPARATIVE_ANSWER_PROMPT`: "2-3 sentences with comparison. Sound human."
   - `ANALYTICAL_ANSWER_PROMPT`: "3-4 sentences with full insights."

3. **See full prompt text** in `PHASE_1_IMPLEMENTATION_SPEC.md` → Task 3, Step 3.1

**Key differences**:
- **SIMPLE**: Max 1 sentence, no workspace avg, no trends
- **COMPARATIVE**: 2-3 sentences, include comparison OR top performer
- **ANALYTICAL**: 3-4 sentences, include everything (trends, outliers, recommendations)

---

### STEP 4: Integrate into AnswerBuilder ⚙️

**Goal**: Wire intent classification into answer generation

**Action**:

1. **Modify**: `backend/app/answer/answer_builder.py`

2. **Add imports** (top of file):
   ```python
   from app.answer.intent_classifier import classify_intent, AnswerIntent, explain_intent
   from app.nlp.prompts import (
       SIMPLE_ANSWER_PROMPT,
       COMPARATIVE_ANSWER_PROMPT,
       ANALYTICAL_ANSWER_PROMPT
   )
   ```

3. **Modify `build_answer()` method** (around line 169):
   - Classify intent at start
   - Filter context based on intent
   - Select appropriate prompt
   - See full code in `PHASE_1_IMPLEMENTATION_SPEC.md` → Task 4, Step 4.1

4. **Add 2 new helper methods**:
   - `_build_simple_prompt(context, question)`: For SIMPLE intent
   - `_build_comparative_prompt(context, question)`: For COMPARATIVE intent
   - See full code in `PHASE_1_IMPLEMENTATION_SPEC.md` → Task 4, Step 4.1

5. **Add logging**:
   ```python
   logger.info(f"[INTENT] Classified as {intent.value}: {explain_intent(intent)}")
   logger.info(f"[ANSWER] Generated {intent.value} answer ({len(answer_text)} chars)")
   ```

**Key logic**:

```python
# Classify intent
intent = classify_intent(question, dsl)

if intent == AnswerIntent.SIMPLE:
    # Only include basic value
    filtered_context = {"metric_name": ..., "metric_value": ...}
    system_prompt = SIMPLE_ANSWER_PROMPT
    user_prompt = self._build_simple_prompt(filtered_context, question)

elif intent == AnswerIntent.COMPARATIVE:
    # Include comparison + top performer
    filtered_context = {..., "comparison": ..., "top_performer": ...}
    system_prompt = COMPARATIVE_ANSWER_PROMPT
    user_prompt = self._build_comparative_prompt(filtered_context, question)

else:  # ANALYTICAL
    # Include everything
    system_prompt = ANALYTICAL_ANSWER_PROMPT
    user_prompt = self._build_rich_context_prompt(context, dsl)
```

---

### STEP 5: Test Everything 🧪

**Action**:

1. **Create manual test script**: `backend/app/tests/test_phase1_manual.py`
   - See full code in `PHASE_1_IMPLEMENTATION_SPEC.md` → Task 5, Step 5.1

2. **Run it**:
   ```bash
   cd backend
   python -m app.tests.test_phase1_manual
   ```

3. **Review results**: Should see different answer lengths based on intent

4. **Test in Swagger UI** (`http://localhost:8000/docs`):
   ```json
   POST /qa?workspace_id=<ID>
   
   // SIMPLE
   {"question": "what was my roas last month"}
   Expected: 1 sentence
   
   // COMPARATIVE
   {"question": "which campaign had highest roas"}
   Expected: 2-3 sentences with top performer
   
   // ANALYTICAL
   {"question": "why is my roas volatile"}
   Expected: 3-4 sentences with trend analysis
   ```

5. **Iterate**: If answers still wrong, adjust prompts and re-test

---

## Expected Results After Phase 1

### Before (Current)
```
Q: "what was my roas last month"
A: "Your ROAS is stable at 3.88×, which is right in line with your workspace average of 3.88×. Over time, it has shown some volatility, peaking at 5.80× and dipping as low as 1.38× recently. While the current performance is average, keeping an eye on these fluctuations could help you identify opportunities for improvement."
```
⚠️ Way too long! 4 sentences with analysis user didn't ask for.

### After Phase 1 ✅
```
Q: "what was my roas last month"
A: "Your ROAS last month was 3.88×"
```
✅ Perfect! Simple question, simple answer.

```
Q: "how does my roas compare to last month"
A: "Your ROAS is 3.88× this month, up from 3.46× last month—that's a 12% improvement"
```
✅ Great! Comparative question with context.

```
Q: "why is my roas volatile"
A: "Your ROAS has been quite volatile this month, ranging from 1.38× to 5.80×. The swings are coming from inconsistent daily performance across campaigns. Your overall average of 3.88× is on par with your workspace norm, but the volatility suggests reviewing campaign settings or creative rotation"
```
✅ Excellent! Analytical question with full insights.

---

## Files You'll Create

```
backend/app/answer/
└── intent_classifier.py          # NEW - Intent detection logic

backend/app/tests/
├── test_workspace_avg.py         # NEW - Tests for workspace avg bug fix
├── test_intent_classifier.py     # NEW - Tests for intent classification
└── test_phase1_manual.py         # NEW - Manual testing script
```

## Files You'll Modify

```
backend/app/dsl/
└── executor.py                   # FIX - Add logging, fix workspace avg

backend/app/nlp/
└── prompts.py                    # ADD - 3 new intent-specific prompts

backend/app/answer/
└── answer_builder.py             # MODIFY - Integrate intent classification
```

---

## Key Principles to Follow

1. **Separation of Concerns**:
   - Intent classifier: ONE job (detect intent)
   - Answer builder: ONE job (generate answer)
   - Each module independently testable

2. **Simple > Complex**:
   - Use keyword matching (not ML)
   - Clear if/else logic
   - Easy to debug and extend

3. **Test-Driven**:
   - Write tests first
   - Verify bug exists
   - Fix bug
   - Verify fix with tests

4. **Documentation**:
   - Update docs after each step
   - Log everything for observability
   - Keep metricx_BUILD_LOG.md current

---

## Quick Start

1. **Read the full spec**: `backend/docs/PHASE_1_IMPLEMENTATION_SPEC.md`
2. **Start with workspace avg bug**: Follow Task 1
3. **Then intent classification**: Follow Task 2-4
4. **Test everything**: Follow Task 5
5. **Update docs**: Mark Phase 1 complete

---

## Success Check

After implementing everything, run:

```bash
cd backend

# Run all new tests
pytest app/tests/test_workspace_avg.py -v
pytest app/tests/test_intent_classifier.py -v

# Run manual test script
python -m app.tests.test_phase1_manual

# Test in Swagger UI
# http://localhost:8000/docs → POST /qa
```

**Expected**: 
- ✅ All automated tests pass
- ✅ Simple questions → 1 sentence
- ✅ Comparative questions → 2-3 sentences
- ✅ Analytical questions → 3-4 sentences
- ✅ workspace_avg ≠ summary when filters applied

---

_Ready to implement? Start with STEP 1 (workspace avg bug) and work through steps 1-5 in order._

_Full details: `backend/docs/PHASE_1_IMPLEMENTATION_SPEC.md`_

