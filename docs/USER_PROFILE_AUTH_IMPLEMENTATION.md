# User Profile & Authentication Implementation

## Overview
This document details the implementation of User Profile management and Authentication features in metricx. The system uses JWT-based authentication with HTTP-only cookies for security, and includes flows for registration, login, profile updates, password management, and email verification.

## Features Implemented

### 1. User Model & Schema
- **Extended User Model**: Added fields for `avatar_url`, `is_verified`, `verification_token`, `reset_token`, and `reset_token_expires_at`.
- **Schemas**: Updated `UserCreate` to include `name`. Created schemas for `UserUpdate`, `PasswordChange`, `PasswordResetRequest`, `PasswordResetConfirm`, and `EmailVerification`.

### 2. Authentication Flows
- **Registration**:
  - Users sign up with Name, Email, and Password.
  - A verification token is generated.
  - A "New workspace" is automatically created for the user.
  - **Note**: Email verification is currently mocked (link logged to console).
- **Login**:
  - Authenticates via Email/Password.
  - Issues an HTTP-only `access_token` cookie (JWT).
  - Supports "Forgot Password" flow.
- **Logout**:
  - Clears the `access_token` cookie.

### 3. Profile Management
- **Settings Page**: Refactored into a tabbed interface:
  - **Connections**: Manage ad platform integrations.
  - **Profile**: Update Name, Email, Avatar, and Change Password.
  - **Users**: Placeholder for future team management.
- **Email Update**:
  - Changing email triggers a re-verification process.
  - Automatically refreshes the JWT token to prevent 401 errors.

### 4. Password & Security
- **Password Reset**:
  - `/auth/forgot-password`: Requests a reset link.
  - `/auth/reset-password`: Sets a new password using the token.
  - **Security**: Tokens expire after 1 hour.
- **Change Password**: Authenticated users can change their password from the Profile tab.
- **Hashing**: Passwords are hashed using `bcrypt`.

## Technical Details

### Backend (`backend/app/routers/auth.py`)
- **`POST /register`**: Creates user, workspace, and verification token.
- **`POST /login`**: Validates credentials, sets HTTP-only cookie.
- **`PUT /me`**: Updates profile. Handles email change logic (token refresh).
- **`POST /forgot-password`**: Generates reset token.
- **`POST /reset-password`**: Verifies token and updates password.
- **`POST /verify-email`**: Marks user as verified.

### Frontend (`ui/app/`)
- **`login/page.jsx`**: Unified Login/Register form with "Forgot Password" link.
- **`auth/forgot-password/page.jsx`**: Request reset link.
- **`auth/reset-password/page.jsx`**: Set new password.
- **`auth/verify-email/page.jsx`**: Auto-verifies token from URL.
- **`settings/components/`**: Modularized settings tabs (`ProfileTab`, `ConnectionsTab`).

## Current Limitations & Future Work
- **Email Service**: Emails are **mocked**. Verification and Reset links are printed to the backend console/logs. Integration with a real email provider (e.g., SendGrid, AWS SES) is required for production.
- **Session Management**: Basic JWT implementation. "Remember Me" and active session management are not yet implemented.
- **Role Management**: All new users are currently assigned the "Owner" role.
