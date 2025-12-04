"""Authentication endpoints: register, login, me, logout."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..deps import get_current_user, get_settings
from ..models import User, Workspace, WorkspaceMember, WorkspaceInvite, AuthCredential, RoleEnum, InviteStatusEnum
from ..security import create_access_token, get_password_hash, verify_password
from ..telemetry import (
    track_user_signed_up,
    track_user_logged_in,
    set_user_context,
    clear_user_context,
)
import secrets
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/auth", 
    tags=["Authentication"],
    responses={
        400: {"model": schemas.ErrorResponse, "description": "Bad Request"},
        401: {"model": schemas.ErrorResponse, "description": "Unauthorized"},
        500: {"model": schemas.ErrorResponse, "description": "Internal Server Error"},
    }
)


def _hydrate_user_context(db: Session, user: User) -> User:
    """Attach memberships and pending invites to the user for response shaping."""
    user_query = (
        db.query(User)
        .options(joinedload(User.memberships).joinedload(WorkspaceMember.workspace))
        .filter(User.id == user.id)
    )
    hydrated = user_query.first()
    if not hydrated:
        return user

    memberships = hydrated.memberships or []
    # Backfill membership for legacy users
    if not memberships and hydrated.workspace_id:
        legacy_membership = WorkspaceMember(
            workspace_id=hydrated.workspace_id,
            user_id=hydrated.id,
            role=hydrated.role,
            status="active",
        )
        db.add(legacy_membership)
        db.commit()
        db.refresh(legacy_membership)
        memberships = [legacy_membership]

    # Attach workspace_name for serialization
    for m in memberships:
        m.workspace_name = m.workspace.name if m.workspace else None

    hydrated.active_workspace_id = hydrated.workspace_id
    hydrated.memberships = memberships

    pending_invites = (
        db.query(WorkspaceInvite)
        .filter(
            WorkspaceInvite.email == hydrated.email,
            WorkspaceInvite.status == InviteStatusEnum.pending,
        )
        .all()
    )
    hydrated.pending_invites = pending_invites
    return hydrated


@router.post(
    "/register", 
    response_model=schemas.UserOut, 
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="""
    Create a new user account with a default workspace.
    
    This endpoint:
    - Creates a new workspace named "New workspace" for the user
    - Creates a user with Owner role (temporary default)
    - Stores encrypted password credentials
    - Returns user information without auto-login
    
    **Note**: All new users are currently given Owner role. This will be updated
    in the future to support invitation-based role assignment.
    """,
    responses={
        201: {
            "model": schemas.UserOut,
            "description": "User successfully created",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "email": "john.doe@company.com",
                        "name": "john.doe",
                        "role": "Owner",
                        "workspace_id": "456e7890-e89b-12d3-a456-426614174001"
                    }
                }
            }
        },
        400: {
            "model": schemas.ErrorResponse,
            "description": "Email already registered",
            "content": {
                "application/json": {
                    "example": {"detail": "Email already registered"}
                }
            }
        }
    }
)
def register_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user with a default workspace and local credentials.

    - If email already exists, respond with 400.
    - Create a `Workspace` named "New workspace".
    - Create `User` with role Owner (temporary default) and a simple `name` derived from email.
    - Create `AuthCredential` storing the bcrypt hash.
    - Do not auto-login.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Create a workspace for the new user (FirstName's Workspace)
    first_name = (payload.name.split(" ")[0] or "My").strip().title()
    workspace = Workspace(name=f"{first_name}'s Workspace")
    db.add(workspace)
    db.flush()  # assign workspace.id without committing yet

    # Generate verification token
    verification_token = secrets.token_urlsafe(32)

    # NOTE: All new users are Owner of their default workspace
    user = User(
        email=payload.email,
        name=payload.name,
        # Persist Owner temporarily for all signups (future: invites/roles)
        role=RoleEnum.owner,
        workspace_id=workspace.id,
        verification_token=verification_token,
        is_verified=False
    )
    db.add(user)
    db.flush()  # assign user.id

    # Add membership record (single owner per workspace)
    membership = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role=RoleEnum.owner,
        status="active",
    )
    db.add(membership)

    credential = AuthCredential(user_id=user.id, password_hash=get_password_hash(payload.password))
    db.add(credential)

    db.commit()
    db.refresh(user)

    # Log verification link (Mock email service)
    logger.info(f"[AUTH] Verification link for {user.email}: http://localhost:3000/auth/verify-email?token={verification_token}")

    # Track user signup event (flows to Google Analytics via RudderStack)
    track_user_signed_up(
        user_id=str(user.id),
        email=user.email,
        name=user.name,
        workspace_id=str(workspace.id),
    )

    return _hydrate_user_context(db, user)


@router.post(
    "/login",
    response_model=schemas.LoginResponse,
    summary="Authenticate user",
    description="""
    Authenticate a user with email and password.
    
    On successful authentication:
    - Sets an HTTP-only JWT cookie named `access_token`
    - Cookie contains JWT token with format "Bearer <token>"
    - Cookie is valid for 7 days
    - Returns user information
    
    **Security Features**:
    - HTTP-only cookie prevents XSS attacks
    - SameSite=Lax prevents CSRF attacks
    - Secure flag enabled in production
    """,
    responses={
        200: {
            "model": schemas.LoginResponse,
            "description": "Login successful",
            "content": {
                "application/json": {
                    "example": {
                        "user": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "email": "john.doe@company.com",
                            "name": "John Doe",
                            "role": "Owner",
                            "workspace_id": "456e7890-e89b-12d3-a456-426614174001"
                        }
                    }
                }
            }
        },
        401: {
            "model": schemas.ErrorResponse,
            "description": "Invalid credentials",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid credentials"}
                }
            }
        }
    }
)
def login_user(
    payload: schemas.UserLogin,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    """Authenticate a user and set an HTTP-only JWT cookie.

    Cookie:
    - name: access_token
    - value: "Bearer <jwt>"
    - httponly: True, samesite: lax, secure: False (dev), domain from env
    - max_age: 7 days
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    cred = db.query(AuthCredential).filter(AuthCredential.user_id == user.id).first()
    if not cred or not verify_password(payload.password, cred.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(subject=user.email)
    cookie_value = f"Bearer {token}"
    settings = get_settings()
    max_age = 7 * 24 * 3600

    # Cookie settings that work for both local dev and production.
    # We use SameSite=None to allow cross-site requests (required when frontend
    # and backend are on different domains, e.g. Defang deployment).
    # Secure must be True when SameSite=None.
    cookie_kwargs = {
        "key": "access_token",
        "value": cookie_value,
        "httponly": True,
        "samesite": "none",
        "secure": True,
        "max_age": max_age,
        "path": "/",
    }

    # When running over plain HTTP (common for local dev or LAN/mobile testing),
    # browsers will ignore cookies with SameSite=None and Secure=True.
    # In that case, fall back to SameSite=Lax and secure=False so the cookie
    # is actually stored and subsequent /auth/me calls succeed.
    if request.url.scheme == "http":
        cookie_kwargs["samesite"] = "lax"
        cookie_kwargs["secure"] = False
    
    # Only set domain if explicitly configured (None for most cases)
    if settings.COOKIE_DOMAIN:
        cookie_kwargs["domain"] = settings.COOKIE_DOMAIN
    
    response.set_cookie(**cookie_kwargs)

    # Set Sentry user context for error tracking
    set_user_context(
        user_id=str(user.id),
        email=user.email,
        workspace_id=str(user.workspace_id) if user.workspace_id else None,
    )

    # Track login event (flows to Google Analytics via RudderStack)
    track_user_logged_in(
        user_id=str(user.id),
        email=user.email,
        workspace_id=str(user.workspace_id) if user.workspace_id else None,
    )

    user = _hydrate_user_context(db, user)
    return schemas.LoginResponse(user=schemas.UserOut.model_validate(user))


@router.get(
    "/me", 
    response_model=schemas.UserOut,
    summary="Get current user",
    description="""
    Retrieve information about the currently authenticated user.
    
    Requires a valid JWT token in the `access_token` cookie.
    Returns user details including role and workspace information.
    """,
    responses={
        200: {
            "model": schemas.UserOut,
            "description": "Current user information",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "email": "john.doe@company.com",
                        "name": "John Doe",
                        "role": "Admin",
                        "workspace_id": "456e7890-e89b-12d3-a456-426614174001"
                    }
                }
            }
        },
        401: {
            "model": schemas.ErrorResponse,
            "description": "Not authenticated or invalid token",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authenticated"}
                }
            }
        }
    },
    dependencies=[Depends(get_current_user)]
)
def get_me(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return the current authenticated user."""
    hydrated = _hydrate_user_context(db, user)
    return hydrated


@router.put(
    "/me",
    response_model=schemas.UserOut,
    summary="Update user profile",
    description="Update current user's name, email, or avatar."
)
def update_profile(
    payload: schemas.UserUpdate,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user profile fields."""
    if payload.name is not None:
        current_user.name = payload.name
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url
    if payload.email is not None and payload.email != current_user.email:
        # Check if email is taken
        existing = db.query(User).filter(User.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        current_user.email = payload.email
        current_user.is_verified = False
        current_user.verification_token = secrets.token_urlsafe(32)
        logger.info(f"[AUTH] Re-verification link for {current_user.email}: http://localhost:3000/auth/verify-email?token={current_user.verification_token}")

        # Refresh the JWT token with the new email
        token = create_access_token(subject=current_user.email)
        cookie_value = f"Bearer {token}"
        settings = get_settings()
        max_age = 7 * 24 * 3600

        cookie_kwargs = {
            "key": "access_token",
            "value": cookie_value,
            "httponly": True,
            "samesite": "none",
            "secure": True,
            "max_age": max_age,
            "path": "/",
        }

        if request.url.scheme == "http":
            cookie_kwargs["samesite"] = "lax"
            cookie_kwargs["secure"] = False
        
        if settings.COOKIE_DOMAIN:
            cookie_kwargs["domain"] = settings.COOKIE_DOMAIN
        
        response.set_cookie(**cookie_kwargs)

    db.commit()
    db.refresh(current_user)
    return _hydrate_user_context(db, current_user)


@router.post(
    "/change-password",
    response_model=schemas.SuccessResponse,
    summary="Change password",
    description="Change the current user's password."
)
def change_password(
    payload: schemas.PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Change password for authenticated user."""
    cred = db.query(AuthCredential).filter(AuthCredential.user_id == current_user.id).first()
    if not cred or not verify_password(payload.old_password, cred.password_hash):
        raise HTTPException(status_code=400, detail="Invalid current password")

    cred.password_hash = get_password_hash(payload.new_password)
    db.commit()
    return schemas.SuccessResponse(detail="Password updated successfully")


@router.post(
    "/forgot-password",
    response_model=schemas.SuccessResponse,
    summary="Request password reset",
    description="Send a password reset link to the user's email."
)
def request_password_reset(
    payload: schemas.PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Generate reset token and log link (mock email)."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        # Don't reveal user existence
        return schemas.SuccessResponse(detail="If email exists, reset link sent")

    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires_at = datetime.utcnow() + timedelta(hours=1)
    db.commit()

    logger.info(f"[AUTH] Password reset link for {user.email}: http://localhost:3000/auth/reset-password?token={token}")
    return schemas.SuccessResponse(detail="If email exists, reset link sent")


@router.post(
    "/reset-password",
    response_model=schemas.SuccessResponse,
    summary="Confirm password reset",
    description="Reset password using a valid token."
)
def confirm_password_reset(
    payload: schemas.PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Reset password with token."""
    user = db.query(User).filter(
        User.reset_token == payload.token,
        User.reset_token_expires_at > datetime.utcnow()
    ).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    cred = db.query(AuthCredential).filter(AuthCredential.user_id == user.id).first()
    if cred:
        cred.password_hash = get_password_hash(payload.new_password)
    
    user.reset_token = None
    user.reset_token_expires_at = None
    db.commit()

    return schemas.SuccessResponse(detail="Password reset successfully")


@router.post(
    "/verify-email",
    response_model=schemas.SuccessResponse,
    summary="Verify email",
    description="Verify email address using a token."
)
def verify_email(
    payload: schemas.EmailVerification,
    db: Session = Depends(get_db)
):
    """Verify email with token."""
    user = db.query(User).filter(User.verification_token == payload.token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token")

    user.is_verified = True
    user.verification_token = None
    db.commit()

    return schemas.SuccessResponse(detail="Email verified successfully")


@router.post(
    "/logout",
    response_model=schemas.SuccessResponse,
    summary="Logout user",
    description="""
    Log out the current user by clearing the authentication cookie.
    
    This endpoint:
    - Clears the `access_token` HTTP-only cookie
    - Invalidates the current session
    - Does not require authentication (can be called even with invalid token)
    """,
    responses={
        200: {
            "model": schemas.SuccessResponse,
            "description": "Successfully logged out",
            "content": {
                "application/json": {
                    "example": {"detail": "logged out"}
                }
            }
        }
    }
)
def logout_user(response: Response, request: Request):
    """Clear the access token cookie."""
    # Clear Sentry user context
    clear_user_context()

    settings = get_settings()

    cookie_kwargs = {
        "key": "access_token",
        "value": "",
        "max_age": 0,
        "httponly": True,
        "samesite": "none",
        "secure": True,
        "path": "/",
    }

    if request.url.scheme == "http":
        cookie_kwargs["samesite"] = "lax"
        cookie_kwargs["secure"] = False
    
    if settings.COOKIE_DOMAIN:
        cookie_kwargs["domain"] = settings.COOKIE_DOMAIN
    
    response.set_cookie(**cookie_kwargs)
    return schemas.SuccessResponse(detail="logged out")


@router.delete(
    "/delete-account",
    response_model=schemas.SuccessResponse,
    summary="Delete user account",
    description="""
    Permanently delete the current user's account and all associated data.
    
    This endpoint:
    - Deletes the user account
    - Deletes all workspace data (if user is the only member)
    - Deletes all connections, entities, metrics, and queries
    - Deletes authentication credentials
    - This action cannot be undone
    
    GDPR/CCPA Compliance:
    - Fulfills user's right to erasure
    - Permanently removes all personal and activity data
    - Complies with Privacy Policy section 7.3
    """,
    responses={
        200: {
            "model": schemas.SuccessResponse,
            "description": "Account successfully deleted",
            "content": {
                "application/json": {
                    "example": {"detail": "Account deleted successfully"}
                }
            }
        },
        401: {
            "model": schemas.ErrorResponse,
            "description": "Not authenticated",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authenticated"}
                }
            }
        }
    }
)
def delete_account(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete user account and all associated data (GDPR/CCPA compliant).
    
    WHAT:
        Permanently deletes user account, workspace (if sole user), and all related data.
    WHY:
        Users have the right to delete their data per GDPR/CCPA regulations.
    REFERENCES:
        - docs/PRIVACY_POLICY.md (Section 7.3 - Deletion)
        - Privacy Policy page (/privacy)
    """
    from app.models import (
        AuthCredential, QaQueryLog, MetricFact, Entity,
        Connection, Token, Workspace, ManualCost, WorkspaceMember
    )
    
    user_id = current_user.id
    workspace_id = current_user.workspace_id
    
    logger.info(f"[DELETE_ACCOUNT] Starting account deletion for user {user_id}")
    
    try:
        # Check if user is the only one in the workspace
        users_in_workspace = db.query(User).filter(User.workspace_id == workspace_id).all()
        delete_workspace = len(users_in_workspace) == 1
        
        # Delete user's query logs
        db.query(QaQueryLog).filter(QaQueryLog.user_id == user_id).delete()
        logger.info(f"[DELETE_ACCOUNT] Deleted query logs for user {user_id}")
        
        # Delete auth credentials
        db.query(AuthCredential).filter(AuthCredential.user_id == user_id).delete()
        logger.info(f"[DELETE_ACCOUNT] Deleted auth credentials for user {user_id}")
        
        # Nullify created_by_user_id in manual costs (they belong to workspace, not individual user)
        # This prevents foreign key constraint violation when deleting user
        db.query(ManualCost).filter(ManualCost.created_by_user_id == user_id).update(
            {"created_by_user_id": None},
            synchronize_session=False
        )
        logger.info(f"[DELETE_ACCOUNT] Nullified user reference in manual costs for user {user_id}")
        
        if delete_workspace:
            logger.info(f"[DELETE_ACCOUNT] User is sole member, deleting workspace {workspace_id}")
            
            # Delete all workspace data
            # 1. Delete metric facts
            db.query(MetricFact).filter(
                MetricFact.entity_id.in_(
                    db.query(Entity.id).filter(Entity.workspace_id == workspace_id)
                )
            ).delete(synchronize_session=False)
            
            # 2. Delete entities
            db.query(Entity).filter(Entity.workspace_id == workspace_id).delete()
            
            # 3. Delete manual costs
            db.query(ManualCost).filter(ManualCost.workspace_id == workspace_id).delete()
            
            # 4. Delete tokens associated with connections
            connection_ids = [c.id for c in db.query(Connection.id).filter(
                Connection.workspace_id == workspace_id
            ).all()]
            
            if connection_ids:
                # Get token IDs from connections
                token_ids = [t[0] for t in db.query(Connection.token_id).filter(
                    Connection.id.in_(connection_ids),
                    Connection.token_id.isnot(None)
                ).all()]
                
                # Delete connections
                db.query(Connection).filter(Connection.workspace_id == workspace_id).delete()
                
                # Delete orphaned tokens
                if token_ids:
                    db.query(Token).filter(Token.id.in_(token_ids)).delete(synchronize_session=False)
            
            # 5. Delete all query logs for workspace
            db.query(QaQueryLog).filter(QaQueryLog.workspace_id == workspace_id).delete()

            # 6. Delete workspace memberships for this user
            db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user_id).delete()

            # 7. Delete the user BEFORE workspace (user has FK to workspace)
            db.query(User).filter(User.id == user_id).delete()
            logger.info(f"[DELETE_ACCOUNT] Deleted user {user_id}")

            # 8. Delete the workspace (now safe, no FK references)
            db.query(Workspace).filter(Workspace.id == workspace_id).delete()

            logger.info(f"[DELETE_ACCOUNT] Deleted workspace {workspace_id} and all associated data")
        else:
            # Multi-user workspace: only delete the user, keep workspace
            db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user_id).delete()
            db.query(User).filter(User.id == user_id).delete()
        
        db.commit()
        logger.info(f"[DELETE_ACCOUNT] Successfully deleted user {user_id}")
        
        # Clear the authentication cookie
        settings = get_settings()
        cookie_kwargs = {
            "key": "access_token",
            "value": "",
            "max_age": 0,
            "httponly": True,
            "samesite": "none",
            "secure": True,
            "path": "/",
        }
        
        if request.url.scheme == "http":
            cookie_kwargs["samesite"] = "lax"
            cookie_kwargs["secure"] = False
        
        if settings.COOKIE_DOMAIN:
            cookie_kwargs["domain"] = settings.COOKIE_DOMAIN
        
        response.set_cookie(**cookie_kwargs)
        
        return schemas.SuccessResponse(detail="Account deleted successfully")
        
    except Exception as e:
        db.rollback()
        logger.exception(f"[DELETE_ACCOUNT] Failed to delete account for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(e)}"
        )
