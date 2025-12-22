"""
Onboarding Router
=================

WHAT: Handles business profile collection during onboarding.
WHY: New users need to provide business context before accessing dashboard.
     This context enables AI personalization in the Copilot.

ENDPOINTS:
    GET  /onboarding/status         - Check if onboarding is completed
    POST /onboarding/analyze-domain - AI-powered domain analysis
    POST /onboarding/complete       - Save profile and mark complete
    PUT  /onboarding/profile        - Update business profile (Settings)
    GET  /onboarding/profile        - Get current business profile

REFERENCES:
    - backend/app/models.py (Workspace model with profile fields)
    - backend/app/services/domain_analyzer.py (AI domain analysis)
    - ui/app/onboarding/ (frontend flow)
    - backend/app/agent/nodes.py (copilot context injection)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.models import User, Workspace
from app.schemas import (
    DomainAnalyzeRequest,
    DomainAnalyzeResponse,
    DomainSuggestions,
    OnboardingCompleteRequest,
    OnboardingCompleteResponse,
    OnboardingStatusResponse,
    BusinessProfileUpdate,
    BusinessProfileResponse,
)
from app.services.domain_analyzer import analyze_domain

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


# =============================================================================
# ONBOARDING STATUS
# =============================================================================


@router.get(
    "/status",
    response_model=OnboardingStatusResponse,
    summary="Check onboarding status",
)
def get_onboarding_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OnboardingStatusResponse:
    """
    Check if the current user has completed onboarding.

    WHAT: Returns onboarding completion status and current profile.
    WHY: Frontend needs this to redirect to onboarding if not completed.

    Returns:
        - completed: bool - Whether onboarding is done
        - workspace_id: str - Current workspace ID
        - workspace_name: str - Current workspace name
        - profile: dict - Current business profile data (if any)
    """
    workspace = db.query(Workspace).filter(
        Workspace.id == current_user.workspace_id
    ).first()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    # Build profile dict from workspace fields
    profile = None
    if workspace.domain or workspace.niche or workspace.domain_description:
        profile = {
            "domain": workspace.domain,
            "domain_description": workspace.domain_description,
            "niche": workspace.niche,
            "target_markets": workspace.target_markets,
            "brand_voice": workspace.brand_voice,
            "business_size": workspace.business_size,
        }

    return OnboardingStatusResponse(
        completed=workspace.onboarding_completed or False,
        workspace_id=str(workspace.id),
        workspace_name=workspace.name,
        profile=profile,
    )


# =============================================================================
# DOMAIN ANALYSIS
# =============================================================================


@router.post(
    "/analyze-domain",
    response_model=DomainAnalyzeResponse,
    summary="Analyze domain with AI",
)
async def analyze_domain_endpoint(
    payload: DomainAnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DomainAnalyzeResponse:
    """
    Analyze a domain to extract business information using AI.

    WHAT: Scrapes domain homepage, extracts text, uses GPT-4o-mini to analyze.
    WHY: Auto-suggests business profile during onboarding to reduce friction.

    Args:
        payload: { "domain": "acme.com" }

    Returns:
        - success: bool
        - suggestions: { business_name, description, niche, brand_voice, confidence }
        - error: str (if failed)

    Example:
        POST /onboarding/analyze-domain
        { "domain": "stripe.com" }
        ->
        {
            "success": true,
            "suggestions": {
                "business_name": "Stripe",
                "description": "Online payment processing platform...",
                "niche": "SaaS / Financial Technology",
                "brand_voice": "Professional",
                "confidence": 0.9
            }
        }
    """
    logger.info(f"[ONBOARDING] Domain analysis requested for: {payload.domain}")

    result = await analyze_domain(payload.domain)

    if not result.get("success"):
        return DomainAnalyzeResponse(
            success=False,
            error=result.get("error", "Unknown error during analysis"),
        )

    suggestions_data = result.get("suggestions", {})
    suggestions = DomainSuggestions(
        business_name=suggestions_data.get("business_name"),
        description=suggestions_data.get("description"),
        niche=suggestions_data.get("niche"),
        brand_voice=suggestions_data.get("brand_voice"),
        confidence=suggestions_data.get("confidence", 0.0),
    )

    return DomainAnalyzeResponse(
        success=True,
        suggestions=suggestions,
    )


# =============================================================================
# COMPLETE ONBOARDING
# =============================================================================


@router.post(
    "/complete",
    response_model=OnboardingCompleteResponse,
    summary="Complete onboarding",
)
def complete_onboarding(
    payload: OnboardingCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OnboardingCompleteResponse:
    """
    Save business profile and mark onboarding as complete.

    WHAT: Updates workspace with business profile, sets onboarding_completed=true.
    WHY: Final step of onboarding flow before user accesses dashboard.

    Args:
        payload: {
            "workspace_name": "ACME Corp" (required),
            "domain": "acme.com" (optional),
            "niche": "E-commerce" (optional),
            "target_markets": ["US", "UK"] (optional),
            "brand_voice": "Professional" (optional),
            ...
        }

    Returns:
        - success: bool
        - redirect_to: "/dashboard"
    """
    logger.info(f"[ONBOARDING] Completing onboarding for user {current_user.id}")

    workspace = db.query(Workspace).filter(
        Workspace.id == current_user.workspace_id
    ).first()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    # Update workspace name (required)
    workspace.name = payload.workspace_name

    # Update optional business profile fields
    if payload.domain is not None:
        workspace.domain = payload.domain
    if payload.domain_description is not None:
        workspace.domain_description = payload.domain_description
    if payload.niche is not None:
        workspace.niche = payload.niche
    if payload.target_markets is not None:
        workspace.target_markets = payload.target_markets
    if payload.brand_voice is not None:
        workspace.brand_voice = payload.brand_voice
    if payload.business_size is not None:
        workspace.business_size = payload.business_size
    if payload.intended_ad_providers is not None:
        workspace.intended_ad_providers = payload.intended_ad_providers

    # Mark onboarding complete
    workspace.onboarding_completed = True
    workspace.onboarding_completed_at = datetime.now(timezone.utc)

    db.commit()

    logger.info(f"[ONBOARDING] Completed onboarding for workspace {workspace.id}")

    return OnboardingCompleteResponse(
        success=True,
        redirect_to="/dashboard",
    )


# =============================================================================
# BUSINESS PROFILE (Settings)
# =============================================================================


@router.get(
    "/profile",
    response_model=BusinessProfileResponse,
    summary="Get business profile",
)
def get_business_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BusinessProfileResponse:
    """
    Get the current business profile for the workspace.

    WHAT: Returns all business profile fields.
    WHY: Settings page needs this to populate edit form.
    """
    workspace = db.query(Workspace).filter(
        Workspace.id == current_user.workspace_id
    ).first()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    return BusinessProfileResponse(
        workspace_id=str(workspace.id),
        workspace_name=workspace.name,
        domain=workspace.domain,
        domain_description=workspace.domain_description,
        niche=workspace.niche,
        target_markets=workspace.target_markets,
        brand_voice=workspace.brand_voice,
        business_size=workspace.business_size,
        onboarding_completed=workspace.onboarding_completed or False,
        onboarding_completed_at=workspace.onboarding_completed_at,
    )


@router.put(
    "/profile",
    response_model=BusinessProfileResponse,
    summary="Update business profile",
)
def update_business_profile(
    payload: BusinessProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BusinessProfileResponse:
    """
    Update business profile fields.

    WHAT: Updates individual profile fields.
    WHY: Settings page allows editing profile after onboarding.

    Args:
        payload: Fields to update (all optional)

    Returns:
        Updated business profile
    """
    logger.info(f"[ONBOARDING] Updating profile for workspace {current_user.workspace_id}")

    workspace = db.query(Workspace).filter(
        Workspace.id == current_user.workspace_id
    ).first()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    # Update fields that were provided
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(workspace, field):
            setattr(workspace, field, value)

    db.commit()
    db.refresh(workspace)

    logger.info(f"[ONBOARDING] Updated profile for workspace {workspace.id}")

    return BusinessProfileResponse(
        workspace_id=str(workspace.id),
        workspace_name=workspace.name,
        domain=workspace.domain,
        domain_description=workspace.domain_description,
        niche=workspace.niche,
        target_markets=workspace.target_markets,
        brand_voice=workspace.brand_voice,
        business_size=workspace.business_size,
        onboarding_completed=workspace.onboarding_completed or False,
        onboarding_completed_at=workspace.onboarding_completed_at,
    )
