## ADDED Requirements

### Requirement: Scheduled Report Agents
The system SHALL allow agents to run on a schedule (daily, weekly, monthly) with a specified timezone and date range.

#### Scenario: Daily report at 1am local time
- **WHEN** a user configures a daily schedule at 01:00 in America/New_York
- **THEN** the agent SHALL evaluate at that local time and use the configured date range

### Requirement: Always-Send Report Mode
The system SHALL support scheduled report agents that trigger at schedule time even when no condition is evaluated.

#### Scenario: Always-send daily report
- **WHEN** a scheduled agent is configured with condition_required=false
- **THEN** the agent SHALL trigger at the scheduled time without evaluating conditions

### Requirement: Scoped Aggregation
The system SHALL support scopes that filter entities (provider, level, entity_ids) and optionally aggregate metrics across the filtered scope.

#### Scenario: Aggregate totals for Meta campaigns
- **WHEN** a user selects provider=meta, level=campaign, and aggregate=true
- **THEN** the agent SHALL evaluate totals across all matching Meta campaigns as a single evaluation

### Requirement: Multi-Channel Notifications
The system SHALL support a notify action that can send notifications to multiple channels (email, Slack, webhook) with per-channel configuration and enablement.

#### Scenario: Slack + Email report delivery
- **WHEN** a notify action is configured with Slack and Email channels enabled
- **THEN** the system SHALL attempt delivery to both channels and record per-channel results

### Requirement: Templates and Event Overrides
The system SHALL support template presets and custom templates with variable substitution, and SHALL allow event-specific overrides for at least trigger and report events.

#### Scenario: Different templates for trigger vs report
- **WHEN** a notify action defines a trigger template preset and a report custom template
- **THEN** trigger events SHALL use the trigger preset and report events SHALL use the report template

### Requirement: Report-Friendly Creation Flow
The system SHALL provide an agent creation flow that supports report mode without requiring a condition, while allowing optional scope selection and aggregation.

#### Scenario: Create a report agent without a condition
- **WHEN** a user selects report mode and skips condition configuration
- **THEN** the system SHALL create a scheduled report agent with a default aggregate scope and allow optional scope filters
