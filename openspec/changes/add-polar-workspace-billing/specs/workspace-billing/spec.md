## ADDED Requirements

### Requirement: Workspace Subscription State
Each `Workspace` MUST have a persisted billing state that can be used for access control.

#### Scenario: Workspace defaults to locked
- **WHEN** a workspace is created
- **THEN** its billing status is `locked` until a subscription becomes `trialing` or `active`

### Requirement: Subscription-Gated Access
Access to subscription-gated routes and paid APIs MUST depend on the billing state of the active workspace.

#### Scenario: Member blocked when workspace not subscribed
- **GIVEN** a user is a member of a workspace
- **AND** the workspace billing status is not `trialing` or `active`
- **WHEN** the user attempts to access `/dashboard` or `/onboarding`
- **THEN** access is denied

#### Scenario: Owner/Admin redirected to subscribe
- **GIVEN** a user is an Owner or Admin of the active workspace
- **AND** the workspace is not `trialing` or `active`
- **WHEN** the user navigates to a subscription-gated route
- **THEN** the user is redirected to `/subscribe` for that workspace

### Requirement: Polar Checkout Creation
The system MUST create Polar checkouts for a specific workspace and plan.

#### Scenario: Checkout created for a workspace plan
- **GIVEN** a user is Owner or Admin of a workspace
- **WHEN** they request a checkout for `monthly` or `annual`
- **THEN** the backend returns a Polar checkout URL for that workspace and plan

### Requirement: Polar Webhook Synchronization
The system MUST process Polar webhooks to update workspace billing state.

#### Scenario: Checkout update links subscription to workspace
- **GIVEN** a checkout was created for a workspace
- **WHEN** a `checkout.updated` webhook is received
- **THEN** the workspace is linked to the Polar `subscription_id` from the checkout payload

#### Scenario: Subscription update refreshes billing timestamps
- **GIVEN** a workspace is linked to a Polar subscription
- **WHEN** a `subscription.updated` webhook is received
- **THEN** the workspace billing status and `trial_end/current_period_end` fields are updated from the subscription payload

### Requirement: Pending Workspace Cap
The system MUST limit the number of pending (locked) workspaces a user can create.

#### Scenario: Pending cap enforced
- **GIVEN** a user already has 2 pending workspaces where they are Owner/Admin
- **WHEN** they attempt to create another workspace
- **THEN** the request is rejected with a clear, user-actionable error

### Requirement: Member Cap
The system MUST enforce a maximum of 10 active members per workspace.

#### Scenario: Invite blocked when cap reached
- **GIVEN** a workspace already has 10 active members
- **WHEN** an Owner/Admin attempts to invite or add another member
- **THEN** the request is rejected with a clear error explaining the cap

### Requirement: Billing Management Permissions
Only Owners and Admins MUST be able to manage billing for a workspace.

#### Scenario: Viewer cannot open billing portal
- **GIVEN** a user is a Viewer in a workspace
- **WHEN** they attempt to access billing management actions for the workspace
- **THEN** the request is rejected

