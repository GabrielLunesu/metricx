# Project Instructions for Claude Code

## Overview
This project is building a competitor to Triple Whale (named metricx) - an e-commerce/SaaS analytics and attribution platform. Keep this context in mind for all architectural and feature decisions.

## Core Philosophy

### Code Quality
- Write modular, elegant code. Never cut corners.
- Prioritize readability and maintainability over cleverness.
- If a solution feels hacky, stop and find the right approach.

### Understanding First
- **Before writing any code**, thoroughly understand:
  - The existing codebase architecture and patterns
  - The feature requirements and how they fit into the larger system
  - Any dependencies or integrations involved
- Ask clarifying questions if anything is unclear.

## Development Principles

### Design Patterns
Follow core programming principles rigorously:
- **Separation of Concerns**: Each module handles one domain
- **Single Responsibility**: Each function/class does one thing well
- **DRY (Don't Repeat Yourself)**: Extract shared logic into reusable utilities
- **SOLID Principles**: Apply where relevant, especially dependency injection
- **Composition over Inheritance**: Prefer composable, flexible structures
- **Fail Fast**: Validate inputs early, surface errors immediately

### Code Organization
- Keep files focused and reasonably sized (under 300 lines as a guideline)
- Group related functionality into well-named modules
- Use clear, consistent naming conventions throughout
- Maintain a flat-ish directory structure - avoid deep nesting

## Documentation Requirements

### Every File Must Include
- Header comment explaining the file's purpose and responsibility
- References to related files or modules it interacts with

### Every Function Must Include
- **What**: Clear description of what it does
- **Why**: Business context or reasoning for its existence
- **Parameters**: Type and purpose of each input
- **Returns**: What it returns and when
- **Throws**: Any errors it may throw and under what conditions
- **Example**: Usage example for non-trivial functions

### Inline Comments
- Explain *why* not *what* (the code shows what)
- Document any non-obvious logic or business rules
- Reference tickets, docs, or external resources where relevant
- Mark any temporary solutions with `// TODO:` and explanation

## Testing & Observability

### Testing Requirements
- **Every function and service must have smoke tests**
- Test the happy path and at least one failure case
- Integration tests for service boundaries
- Use descriptive test names that explain the scenario

### Observability (Critical)
We must know when something is failing. Every service should have:
- **Structured logging**: Log key events with context (user ID, request ID, etc.)
- **Error tracking**: Capture and report all exceptions with stack traces
- **Metrics**: Track request counts, latencies, error rates
- **Health checks**: Expose endpoints for monitoring
- **Alerting hooks**: Design for easy integration with alerting systems

### Logging Standards
```
[LEVEL] [TIMESTAMP] [SERVICE] [REQUEST_ID] Message | {contextual_data}
```
- DEBUG: Detailed diagnostic information
- INFO: Key business events (user actions, state changes)
- WARN: Unexpected but handled situations
- ERROR: Failures requiring attention

## Error Handling
- Never swallow errors silently
- Use typed/custom errors for different failure modes
- Include context in error messages (what failed, with what inputs)
- Ensure errors bubble up to observability layer

## When You Get Stuck

**If at any point you are confused or uncertain:**
1. Stop immediately
2. Explain what you understand and what's unclear
3. Ask for clarification before proceeding

Do not guess. Do not make assumptions. Ask.

## Pull Request Checklist
Before considering any feature complete:
- [ ] Code follows all principles above
- [ ] All functions documented with what/why
- [ ] Smoke tests written and passing
- [ ] Logging added for key operations
- [ ] Error cases handled with proper observability
- [ ] No TODO comments without linked tickets
- [ ] Related files/modules updated if needed

## Triple Whale Context
Key domains we're competing in:
- E-commerce analytics and reporting
- Marketing attribution (multi-touch)
- Ad spend optimization
- Customer journey tracking
- Real-time dashboards

Always consider: How does this feature help merchants understand and optimize their business?