<!-- 3334529e-0e11-4922-b0aa-9ee772ce6d4d 539e5e30-93d9-4929-85ed-904e8a03c311 -->
# Plan: Display Selected Timeframe in Answers

This plan will enhance the QA system to always include the selected timeframe in answers, providing clarity about what time period the data covers.

## Current State

The system currently:

- Has `timeframe_description` field in DSL (e.g., "this month", "last week")
- Passes `window` dict with actual dates to answer builder
- Includes date range in some answers (via `_format_date_range()`)
- **BUT** doesn't consistently show timeframe in all answers

## Goal

Make timeframe visible in ALL answers:

- **"What's my revenue last month?"** → "You made $50K **in the last 30 days**"
- **"What's my CPC this month?"** → "**From October 1 to October 13**, your CPC has been $0.45"

## Implementation Steps

### 1. Enhance Timeframe Context in Answer Builder

**File**: `backend/app/answer/answer_builder.py`

The system already extracts `timeframe_description` from DSL and passes `window` dates. We need to:

1. **Build a human-readable timeframe string** that combines:

                                                                                                                                                                                                - The user's original phrase (from `timeframe_description`)
                                                                                                                                                                                                - The actual date range (from `window`)

2. **Add timeframe to ALL answer contexts** (SIMPLE, COMPARATIVE, ANALYTICAL):
   ```python
   # Currently at line 260-270 (SIMPLE context)
   filtered_context = {
       "metric_name": context.metric_name,
       "metric_value": context.metric_value,
       "timeframe": timeframe_desc,  # Already here
       "timeframe_display": self._format_timeframe_display(timeframe_desc, window),  # NEW
       ...
   }
   ```

3. **Create helper method** `_format_timeframe_display()`:
   ```python
   def _format_timeframe_display(self, timeframe_desc: str, window: Optional[Dict[str, date]]) -> str:
       """
       Build human-friendly timeframe display.
       
       Examples:
       - timeframe_desc="last month" + window → "in the last 30 days"
       - timeframe_desc="this month" + window={start: Oct 1, end: Oct 13} → "from October 1 to October 13"
       - timeframe_desc="last week" + window → "in the last 7 days"
       - timeframe_desc="yesterday" + window → "yesterday"
       """
   ```


### 2. Update Answer Generation Prompts

**File**: `backend/app/nlp/prompts.py`

Update the three intent-specific prompts to include timeframe instructions:

1. **SIMPLE_ANSWER_PROMPT** (currently around line 930):
   ```python
   SIMPLE_ANSWER_PROMPT = """...
   
   CRITICAL RULES:
   1. ALWAYS include the timeframe in your answer
   2. Use the 'timeframe_display' field for the time period
   3. Format: "[Metric] [was/is] [value] [timeframe]"
   
   Examples:
   - "Your revenue was $50,000 in the last 30 days"
   - "From October 1 to October 13, your CPC has been $0.45"
   - "Your ROAS is 3.2× this week"
   """
   ```

2. **COMPARATIVE_ANSWER_PROMPT**:

                                                                                                                                                                                                - Add timeframe to comparison statements
                                                                                                                                                                                                - Example: "Your ROAS was 3.2× last week, up 15% from the previous week"

3. **ANALYTICAL_ANSWER_PROMPT**:

                                                                                                                                                                                                - Include timeframe in first sentence
                                                                                                                                                                                                - Example: "Last week, your ROAS was 3.2×, driven by..."

### 3. Update Context Extractor (if needed)

**File**: `backend/app/answer/context_extractor.py`

Check if `extract_rich_context()` needs to be updated to pass timeframe information through to the analytical prompt.

### 4. Update Template Fallback

**File**: `backend/app/services/qa_service.py`

Update `_build_answer_template()` method (around line 339) to also include timeframe in fallback answers when LLM fails.

## Expected Behavior

### Before

- "Your CPC is $0.45 this month" *(vague timeframe)*
- "You made $50,000" *(no timeframe at all)*

### After

- "From October 1 to October 13, your CPC is $0.45"
- "You made $50,000 in the last 30 days"
- "Your ROAS was 3.2× last week"

## Files to Modify

1. `backend/app/answer/answer_builder.py` - Add timeframe formatting logic
2. `backend/app/nlp/prompts.py` - Update prompts with timeframe instructions
3. `backend/app/services/qa_service.py` - Update template fallback (optional)

## Testing

After implementation, test with:

- "What's my revenue last month?" → Should show "in the last 30 days"
- "What's my CPC this month?" → Should show "from October 1 to October 13"
- "What was my ROAS yesterday?" → Should show "yesterday"
- "Give me my spend this week" → Should show timeframe clearly

### To-dos

- [ ] Enforce XOR constraint on `TimeRange` DSL model in `backend/app/dsl/schema.py`.
- [ ] Create a new date parsing module at `backend/app/dsl/date_parser.py` and add corresponding tests.
- [ ] Update LLM prompts in `backend/app/nlp/prompts.py` with explicit date handling rules.
- [ ] Integrate the new date parser into the translation pipeline in `backend/app/nlp/translator.py`.
- [ ] Update the `QA_SYSTEM_ARCHITECTURE.md` with the new date parsing stage and DSL changes.
- [ ] Update `metricx_BUILD_LOG.md` with a detailed changelog entry for this phase.