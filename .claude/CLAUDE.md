# Project Instructions for Claude Code

## Overview
This project is building **metricx** - an ad analytics platform that helps merchants get the most out of their advertising spend. We compete with Triple Whale but with a clearer focus.

## Strategic Vision: Ad Analytics First, Attribution Second

**This one decision unblocks everything.**

### Primary (Front and Center)
- **Dashboard** → Ad performance, spend, ROAS (platform-reported), AI insights
- **Analytics** → Deep dive, campaign comparisons, trends
- **P&L** → Profitability view
- **Campaigns** → Manage and monitor

### Secondary (There, but Not in Your Face)
- **Attribution** → Settings/setup thing, a "verification layer" that enhances your numbers
- **UTM Setup, Pixel Config, Shopify Connection** → Lives in Settings or "Integrations" area
- **Attribution Warnings** → Only surface when Shopify is connected but something's misconfigured

### Why This Matters
1. **Onboarding gets simpler**: "Connect Meta + Google" → done, you're in
2. **Dashboard isn't full of empty boxes**: Show platform data immediately
3. **Stop apologizing for missing attribution data**: It's an enhancement, not a requirement
4. **Shopify users get a "premium" feeling**: Their data is verified
5. **We can go live now**: Without everything needing to be perfect

### The Goal
**Help merchants understand and optimize their ad spend.** Attribution is the cherry on top, not the cake.

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

## Reasoning Approach
For complex architectural decisions or debugging, use atom of thought:
1. Identify the core sub-problems
2. Reason through each independently
3. Check for conflicts between conclusions
4. Synthesize into a coherent solution

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

### UI Components (MANDATORY)
**All UI components MUST use shadcn/ui.** This is non-negotiable.

- **Never** create custom components when a shadcn equivalent exists
- **Never** use raw HTML elements for buttons, inputs, cards, dialogs, etc.
- **Always** check if shadcn has the component first: `npx shadcn@latest add <component>`
- Components live in `ui/components/ui/` - use these, don't reinvent them

**Already installed:** button, card, chart, calendar, popover, date-range-picker

**To add new components:**
```bash
cd ui && npx shadcn@latest add <component-name>
```

**Shadcn config:** `ui/components.json` (new-york style, JSX, Lucide icons)

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
- [ ] **UI uses shadcn components** (no custom buttons, inputs, cards, etc.)

## Triple Whale Context
Key domains we're competing in:
- E-commerce analytics and reporting
- Marketing attribution (multi-touch)
- Ad spend optimization
- Customer journey tracking
- Real-time dashboards

Always consider: How does this feature help merchants understand and optimize their business?