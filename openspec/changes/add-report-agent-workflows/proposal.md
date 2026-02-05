# Change: Report Agent Workflows & Multi-Channel Notifications

## Why
Teams need scheduled, customizable reporting agents that feel like "deploying employees" across platforms, not just basic alerts. The current creation flow and notification model are too rigid for report agents and multi-channel delivery.

## What Changes
- Add first-class scheduled report agents with timezone-aware schedules and explicit date ranges.
- Allow "always send" report agents that bypass conditions at schedule time.
- Expand agent scope to support filtered + aggregate evaluation (workspace totals with optional platform filters).
- Introduce a unified multi-channel notification action with Slack/webhook support and template presets/custom messages.
- Enable event-specific notification customization (trigger vs report vs error/stopped) with sensible defaults.
- Refactor the agent creation flow to support report mode without requiring conditions, while still allowing optional scope selection.

## Impact
- Affected specs: `specs/agent-workflows/spec.md`
- Affected code:
  - `backend/app/services/agents/*`
  - `backend/app/routers/agents.py`
  - `backend/app/models.py`
  - `backend/app/schemas.py`
  - `backend/app/workers/arq_worker.py`
  - `backend/app/services/sync_scheduler.py`
  - `ui/app/(dashboard)/agents/new/page.jsx`
  - `ui/lib/api.js`
