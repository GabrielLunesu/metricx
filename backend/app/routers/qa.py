"""
QA Router
==========

HTTP endpoint for natural language question answering using the DSL v1.1 pipeline.

Related files:
- app/services/qa_service.py: Service layer
- app/schemas.py: Request/response models
- app/dsl/schema.py: DSL structure

Architecture:
- Uses new DSL pipeline (dsl/, nlp/, telemetry/)
- Better error handling with specific error types
- Structured telemetry logging
- Workspace scoping enforced
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.schemas import QARequest, QAResult
from app.services.qa_service import QAService
from app.nlp.translator import TranslationError
from app.dsl.validate import DSLValidationError
from app.database import get_db
from app.deps import get_current_user


router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("", response_model=QAResult)
def ask_question(
    req: QARequest,
    workspace_id: str = Query(..., description="Workspace context for scoping queries"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    POST /qa
    
    Translate a natural language question into a metrics query and execute it.
    
    Input:  { "question": "What's my ROAS this week?" }
    Output: { "answer": "...", "executed_dsl": {...}, "data": {...} }
    
    Process:
    1. Translate question → DSL (via LLM)
    2. Validate DSL structure
    3. Plan query execution
    4. Execute against database
    5. Build human-readable answer
    6. Log for telemetry
    
    Error handling:
    - 400: Translation error (LLM failed or returned invalid JSON)
    - 400: Validation error (DSL doesn't match schema)
    - 400: Execution error (database query failed)
    - 401: Authentication error (no valid token)
    
    Security:
    - Requires authentication (current_user dependency)
    - Workspace scoping enforced (all queries filter by workspace_id)
    - No SQL injection possible (DSL → validated → ORM)
    
    Examples:
        curl -X POST "http://localhost:8000/qa?workspace_id=123..." \\
             -H "Cookie: access_token=Bearer..." \\
             -H "Content-Type: application/json" \\
             -d '{"question": "Show me revenue from active campaigns this month"}'
    
    Related:
    - Service: app/services/qa_service.py
    - DSL: app/dsl/schema.py
    - Logging: app/telemetry/logging.py
    """
    try:
        # Initialize service (can fail if OPENAI_API_KEY not set)
        service = QAService(db)
        
        # Execute the QA pipeline
        result = service.answer(
            question=req.question,
            workspace_id=workspace_id,
            user_id=str(current_user.id)
        )
        return result
        
    except ValueError as e:
        # Configuration error (e.g., OPENAI_API_KEY not set)
        raise HTTPException(
            status_code=500,
            detail=f"Service configuration error: {str(e)}"
        )
        
    except TranslationError as e:
        # LLM failed to translate or returned invalid JSON
        raise HTTPException(
            status_code=400,
            detail=f"Could not translate your question: {e.message}"
        )
        
    except DSLValidationError as e:
        # LLM output didn't match DSL schema
        raise HTTPException(
            status_code=400,
            detail=f"Invalid query structure: {e.message}"
        )
        
    except Exception as e:
        # Catch-all for unexpected errors (with logging for debugging)
        import traceback
        print(f"QA Error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
