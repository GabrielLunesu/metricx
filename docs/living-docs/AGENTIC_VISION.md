# Agentic Marketing Copilot: Architectural Vision
**Target**: Evolution of `QA_SYSTEM_ARCHITECTURE.md`
**Goal**: Transform metricx from a "Passive QA Bot" into a "Proactive AI Marketing Employee"
**Status**: Vision / Proposal

---

## 1. Executive Summary

Current State: metricx is a **deterministic, linear QA pipeline**. It translates questions to SQL-like DSL, executes them, and formats the result. It is safe, reliable, but passive. It waits for questions and has limited "thinking" capacity beyond immediate translation.

**Future Vision**: metricx becomes a **Fully Agentic Copilot**. It doesn't just answer questions; it understands *intent*, *business context*, and *market dynamics*. It proactively monitors accounts, suggests actions, and executes them upon approval. It "self-heals" when data is messy and learns from every interaction.

---

## 2. Architectural Shift: From Pipeline to Loop

We will move from a **Linear Pipeline** to a **Cognitive Loop (OODA)**.

### Current (Linear)
`User Input` → `Translator` → `Executor` → `Formatter` → `Response`

### Future (Agentic Loop)
The system runs a continuous "Thought Process":

1.  **Perceive**: User input + System Alerts + Market News + Campaign Performance.
2.  **Contextualize**: Retrieve long-term memory (User goals: "Aggressive Growth", Brand Voice, Past successful strategies).
3.  **Reason (The Brain)**:
    *   *Is this a simple lookup?* -> Fast Path (Current Pipeline).
    *   *Is this a complex problem?* -> Decompose into sub-tasks.
    *   *Do I need external info?* -> Call Search Tool.
4.  **Act**:
    *   Query Internal DB.
    *   Query External APIs (Perplexity, Google Trends).
    *   Propose Actions (Meta Ads API).
5.  **Reflect & Heal**:
    *   *Did the query fail?* -> Analyze error, re-plan, retry.
    *   *Is the answer helpful?* -> Self-critique before showing user.

---

## 3. Core Capabilities & Improvements

### A. Self-Healing & Reflection
**Problem**: Currently, if the LLM generates invalid DSL or the DB returns empty results, we show a generic error or "No data found".
**Solution**:
*   **Automatic Query Refinement**: If a query returns 0 results, the Agent pauses. *"Hmm, no data for 'ROI' last week. Let me check if 'ROAS' has data, or if the date range is too narrow."* It retries automatically with relaxed constraints.
*   **Syntax Correction**: If the DSL validator fails, the error is fed back into the LLM: *"You used an invalid metric 'cpc_all'. Available metrics are [...]. Fix it."*

### B. Deep Context & Memory (The "Hippocampus")
**Problem**: Context is currently just the last 5 messages.
**Solution**:
*   **Vector Database (RAG)**: Store every insight ever generated, every user preference, and business documents (PDF brand guidelines, strategy docs).
*   **User Graph**: Explicitly model the user's business.
    *   *"Client A cares about CPA < $50."*
    *   *"Client B cares about Volume over Efficiency."*
*   **Session Persistence**: "Remember that analysis we did last Tuesday? Update it for today."

### C. 3rd Party API Integration (The "Tools")
We will give the Agent a "Tool Belt" beyond just our database.

| Tool Category | Integration | Use Case |
| :--- | :--- | :--- |
| **Market Knowledge** | **Perplexity / Google Search API** | *"Why is CPM high today?"* -> Agent searches news for "Facebook outage" or "Black Friday competition" and correlates with data. |
| **Action & Execution** | **Meta Marketing API / Google Ads API** | *"Pause the underperforming creatives."* -> Agent identifies them, drafts the API calls, and asks for confirmation. |
| **Visual Intelligence** | **GPT-4o Vision** | *"Why is this ad winning?"* -> Agent analyzes the image. *"Bright colors and human faces in Ad A are outperforming the text-only Ad B."* |
| **Competitor Intel** | **SEMRush / SpyFu API** | *"How does my CPC compare to the industry average?"* |

---

## 4. The "Actionable Insight" Engine

The system should stop being a "Report Generator" and start being a "Growth Hacker".

**Proactive Monitoring (Cron Agents)**:
Instead of waiting for a user prompt, background agents run 24/7:
*   **Anomaly Detector**: "Alert: Spend spiked 50% in the last hour on Campaign X."
*   **Opportunity Scout**: "Trend Alert: 'Eco-friendly' keywords are cheap right now. Should we launch a campaign?"

**Rich Responses**:
*   **Generative UI**: The Agent doesn't just pick a chart type. It designs the dashboard. *"Here is a funnel view I constructed to show where you are losing customers."*
*   **Interactive Drill-downs**: "Click on the 'Low ROAS' bar to see the specific ads causing the drag."

---

## 5. Implementation Roadmap

### Phase 1: The "Smart" Observer (Weeks 1-4)
*   **Add Reflection Step**: Implement a "Critic" node after DSL generation to catch errors before execution.
*   **Integrate Search**: Add a tool for "Explain Why" queries that searches the web.

### Phase 2: The "Memory" Upgrade (Weeks 5-8)
*   **Deploy Vector DB (Pinecone/Weaviate)**: Index past queries and results.
*   **User Preference Profile**: Allow users to set "North Star Metrics" that the agent prioritizes.

### Phase 3: The "Active" Employee (Weeks 9-12)
*   **Write Access**: Build the "Action Proposal" UI. Agent suggests API calls -> User clicks "Approve".
*   **Vision Analysis**: Integrate creative analysis into performance reports.

---

## 6. Example Scenario: The "Full Loop"

**User**: "Why is my performance down today?"

**metricx Agent**:
1.  **Check Data**: Queries DB. *Result: Spend is normal, but Conversions dropped 40%.*
2.  **Check Tech**: Checks landing page uptime (Tool: Ping). *Result: Site is up.*
3.  **Check Market**: Queries Perplexity. *Result: "Major Instagram outage reported in Europe."*
4.  **Check Creatives**: Analyzes recent ad comments. *Result: Negative sentiment on new ad.*
5.  **Synthesize Answer**:
    > "Performance is down because Conversions dropped 40%.
    > 
    > **Diagnosis**:
    > 1. 🌍 **External**: There is a reported Instagram outage in your main region (Europe).
    > 2. 📉 **Internal**: Your new 'Winter Promo' ad has a high negative sentiment rate.
    > 
    > **Recommended Actions**:
    > *   [Button: Pause 'Winter Promo' Ad]
    > *   [Button: Monitor Outage Status]
    > 
    > Shall I execute these?"
