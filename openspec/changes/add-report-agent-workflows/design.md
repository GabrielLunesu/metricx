## Context
Agents currently focus on real-time alerts with email-only defaults. Report agents require scheduled execution, flexible scopes, and multi-channel delivery, while the creation flow should feel like deploying a capable operator across platforms.

## Goals / Non-Goals
- Goals:
  - Support scheduled report agents with timezone-aware schedules and explicit date ranges.
  - Allow "always send" scheduled reports without condition evaluation.
  - Support scoped aggregation (totals across filtered entities) and optional per-entity evaluation.
  - Provide multi-channel notifications (email, Slack, webhook) with presets and custom templates.
  - Allow event-specific overrides (trigger vs report vs error/stopped) with sane fallbacks.
  - Refactor creation flow for report mode without requiring a condition, while allowing optional scope selection.
- Non-Goals:
  - Building a Slack OAuth app or interactive Slack features.
  - Replacing existing notification or action execution subsystems.
  - Introducing real-time streaming updates beyond current WebSocket support.

## Decisions
- Represent schedule on the Agent model using `schedule_type` and `schedule_config` (timezone, hour/minute, day_of_week/day_of_month).
- Represent date range explicitly with `date_range_type` and map it to metrics queries (e.g., yesterday, last_7_days).
- Use `condition_required=false` to implement report agents that always trigger at schedule time.
- Use a unified `notify` action with channel configs; allow template presets or custom templates.
- Add event-specific overrides for notification routing and templates, but fallback to base config when not specified.
- Update the creation flow to separate "Mission" (report vs alert), "Scope", "Cadence", and "Delivery" steps.

## Risks / Trade-offs
- Timezone accuracy depends on correct schedule configuration; defaults should be explicit and visible in UI.
- Event overrides add complexity to notify configuration; defaults must remain simple.
- Aggregation across filtered scopes can be expensive; must reuse existing snapshot aggregation paths.

## Migration Plan
- Add columns with defaults (schedule_type='realtime', condition_required=true).
- Backfill or interpret null `date_range_type` as:
  - `rolling_24h` for realtime agents
  - `yesterday` for scheduled report agents
- Keep existing email action behavior as a fallback, but prefer `notify` for new agents.

## Open Questions
- Final list of event types to expose in UI (trigger, report, error, stopped, circuit_breaker).
- Default template per event type (e.g., report uses daily_summary preset).
