"""
Domain Analyzer Service
=======================

WHAT: Scrapes and analyzes business domains using AI to extract profile information.
WHY: Provides AI-powered suggestions during onboarding to reduce user friction.
REFERENCES:
    - backend/app/routers/onboarding.py (consumer)
    - backend/app/schemas.py (DomainSuggestions)

HOW IT WORKS:
    1. Fetch the domain's homepage HTML (with timeout)
    2. Extract text content using BeautifulSoup
    3. Send content to OpenAI GPT-4o-mini for structured extraction
    4. Return business_name, description, niche, brand_voice, confidence
"""

import logging
import os
import json
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from openai import OpenAI

logger = logging.getLogger(__name__)

# Timeout for domain fetching (seconds)
FETCH_TIMEOUT = 5.0

# Max characters to send to AI (to control costs/tokens)
MAX_CONTENT_LENGTH = 8000

# OpenAI model for domain analysis (cheap and fast)
ANALYSIS_MODEL = "gpt-4o-mini"

# Prompt for business information extraction
DOMAIN_ANALYSIS_PROMPT = """Analyze this website content and extract business information.

Website content:
{content}

Extract and return ONLY valid JSON with these fields:
{{
    "business_name": "Company/brand name (string or null)",
    "description": "1-2 sentence description of what they do/sell (string or null)",
    "niche": "Industry/category - e.g., Fashion, SaaS, E-commerce, Health & Wellness, B2B Services (string or null)",
    "brand_voice": "One of: Professional, Casual, Luxury, Playful, Technical (string or null)",
    "confidence": 0.0-1.0 (how confident you are in these extractions)
}}

Guidelines:
- If you can't determine a field, use null
- For niche, be specific but not too narrow
- For brand_voice, assess the overall tone of the website
- Confidence should reflect how much content was available and how clear it was

Return ONLY the JSON object, no markdown or explanation."""


async def analyze_domain(domain: str) -> dict:
    """
    Fetch a domain and extract business info using AI.

    WHAT: Scrapes domain homepage, extracts text, sends to OpenAI for analysis.
    WHY: Auto-suggests business profile during onboarding.

    Args:
        domain: The domain to analyze (e.g., "acme.com")

    Returns:
        {
            "success": True/False,
            "suggestions": {
                "business_name": "...",
                "description": "...",
                "niche": "...",
                "brand_voice": "...",
                "confidence": 0.0-1.0
            },
            "error": "..." (if failed)
        }

    Example:
        >>> result = await analyze_domain("stripe.com")
        >>> result["suggestions"]["niche"]
        "SaaS / Financial Technology"
    """
    logger.info(f"[DOMAIN_ANALYZER] Analyzing domain: {domain}")

    # Normalize domain (remove protocol if present)
    domain = _normalize_domain(domain)
    if not domain:
        return {"success": False, "error": "Invalid domain format"}

    # Step 1: Fetch the homepage
    logger.info(f"[DOMAIN_ANALYZER] Step 1: Fetching homepage for {domain}")
    html_content = await _fetch_domain_content(domain)
    if not html_content:
        logger.warning(f"[DOMAIN_ANALYZER] Failed to fetch content for {domain}")
        return {"success": False, "error": "Could not fetch domain content"}

    # Step 2: Extract text from HTML
    logger.info(f"[DOMAIN_ANALYZER] Step 2: Extracting text from HTML ({len(html_content)} bytes)")
    text_content = _extract_text_from_html(html_content)
    if not text_content or len(text_content) < 50:
        logger.warning(f"[DOMAIN_ANALYZER] Insufficient text content extracted: {len(text_content) if text_content else 0} chars")
        return {"success": False, "error": "Could not extract meaningful content from domain"}

    # Step 3: Analyze with AI
    logger.info(f"[DOMAIN_ANALYZER] Step 3: Sending to AI ({len(text_content)} chars)")
    suggestions = _analyze_with_ai(text_content, domain)
    if not suggestions:
        logger.error(f"[DOMAIN_ANALYZER] AI analysis returned None for {domain}")
        return {"success": False, "error": "AI analysis failed"}

    logger.info(f"[DOMAIN_ANALYZER] Successfully analyzed {domain}: {suggestions.get('niche', 'Unknown')}")
    return {"success": True, "suggestions": suggestions}


def _normalize_domain(domain: str) -> Optional[str]:
    """
    Normalize domain input to a clean domain name.

    WHAT: Strips protocols, paths, and validates format.
    WHY: Users might enter "https://acme.com/about" instead of "acme.com".

    Examples:
        >>> _normalize_domain("https://acme.com/about")
        "acme.com"
        >>> _normalize_domain("acme.com")
        "acme.com"
    """
    if not domain:
        return None

    # Remove protocol
    domain = re.sub(r'^https?://', '', domain)

    # Remove path
    domain = domain.split('/')[0]

    # Remove port
    domain = domain.split(':')[0]

    # Basic validation
    if not domain or '.' not in domain:
        return None

    return domain.lower().strip()


async def _fetch_domain_content(domain: str) -> Optional[str]:
    """
    Fetch the homepage HTML content.

    WHAT: Makes HTTP request to domain with timeout.
    WHY: Need raw HTML to extract text content.

    Args:
        domain: Normalized domain name

    Returns:
        HTML content string or None if failed
    """
    urls_to_try = [
        f"https://{domain}",
        f"http://{domain}",
    ]

    async with httpx.AsyncClient(
        timeout=FETCH_TIMEOUT,
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; metricx-bot/1.0; +https://metricx.io)"
        }
    ) as client:
        for url in urls_to_try:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    logger.debug(f"[DOMAIN_ANALYZER] Successfully fetched {url}")
                    return response.text
            except httpx.TimeoutException:
                logger.warning(f"[DOMAIN_ANALYZER] Timeout fetching {url}")
                continue
            except httpx.RequestError as e:
                logger.warning(f"[DOMAIN_ANALYZER] Error fetching {url}: {e}")
                continue

    logger.error(f"[DOMAIN_ANALYZER] Failed to fetch any URL for {domain}")
    return None


def _extract_text_from_html(html: str) -> str:
    """
    Extract meaningful text content from HTML.

    WHAT: Parses HTML, removes scripts/styles, extracts text.
    WHY: AI needs clean text, not HTML markup.

    Args:
        html: Raw HTML content

    Returns:
        Cleaned text content
    """
    soup = BeautifulSoup(html, 'html.parser')

    # Remove script and style elements
    for element in soup(['script', 'style', 'nav', 'footer', 'header', 'noscript']):
        element.decompose()

    # Get text
    text = soup.get_text(separator=' ', strip=True)

    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)

    # Truncate to max length
    if len(text) > MAX_CONTENT_LENGTH:
        text = text[:MAX_CONTENT_LENGTH] + "..."

    return text


def _analyze_with_ai(content: str, domain: str) -> Optional[dict]:
    """
    Use OpenAI to extract business information from text.

    WHAT: Sends text to GPT-4o-mini with extraction prompt.
    WHY: AI can understand context and extract structured data.

    Args:
        content: Text content from website
        domain: Domain name (for context)

    Returns:
        Extracted suggestions dict or None if failed
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("[DOMAIN_ANALYZER] OPENAI_API_KEY not set - check .env file")
        return None

    logger.info(f"[DOMAIN_ANALYZER] Starting AI analysis for {domain} (content: {len(content)} chars)")

    try:
        client = OpenAI(api_key=api_key)

        # Add domain context to content
        content_with_context = f"Domain: {domain}\n\n{content}"

        response = client.chat.completions.create(
            model=ANALYSIS_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a business analyst that extracts company information from website content. Always respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": DOMAIN_ANALYSIS_PROMPT.format(content=content_with_context)
                }
            ],
            max_tokens=500,
            temperature=0.3,  # Lower temperature for more consistent extraction
        )

        result_text = response.choices[0].message.content

        # Parse JSON response
        # Handle potential markdown code blocks
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]

        suggestions = json.loads(result_text.strip())

        # Validate expected fields
        required_fields = ["business_name", "description", "niche", "brand_voice", "confidence"]
        for field in required_fields:
            if field not in suggestions:
                suggestions[field] = None if field != "confidence" else 0.0

        return suggestions

    except json.JSONDecodeError as e:
        logger.error(f"[DOMAIN_ANALYZER] Failed to parse AI response as JSON: {e}")
        logger.error(f"[DOMAIN_ANALYZER] Raw response: {result_text[:500] if 'result_text' in dir() else 'N/A'}")
        return None
    except Exception as e:
        logger.exception(f"[DOMAIN_ANALYZER] AI analysis failed with error: {type(e).__name__}: {e}")
        return None
