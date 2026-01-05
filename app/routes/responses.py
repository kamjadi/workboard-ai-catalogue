from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from ..models import (
    ResponseCreate, ResponseUpdate, Response, ResponseWithDetails,
    DashboardSummary, FunctionBreakdown, TeamBreakdown
)
from .. import crud

router = APIRouter(prefix="/api", tags=["responses"])


# ============ Response CRUD Endpoints ============

@router.get("/responses", response_model=List[dict])
async def list_responses(
    function_id: Optional[int] = None,
    team_id: Optional[int] = None,
    method_type: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0)
):
    """List all responses with optional filters."""
    return crud.get_responses(
        function_id=function_id,
        team_id=team_id,
        method_type=method_type,
        limit=limit,
        offset=offset
    )


@router.get("/responses/{response_id}", response_model=dict)
async def get_response(response_id: int):
    """Get a single response by ID."""
    response = crud.get_response(response_id)
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")
    return response


@router.post("/responses", response_model=dict, status_code=201)
async def create_response(response: ResponseCreate):
    """Create a new response."""
    # Validate foreign keys exist
    if not crud.get_function(response.function_id):
        raise HTTPException(status_code=400, detail="Invalid function_id")
    # team_id is optional - only validate if provided
    if response.team_id is not None and not crud.get_team(response.team_id):
        raise HTTPException(status_code=400, detail="Invalid team_id")
    if not crud.get_capability(response.capability_id):
        raise HTTPException(status_code=400, detail="Invalid capability_id")

    return crud.create_response(response)


@router.put("/responses/{response_id}", response_model=dict)
async def update_response(response_id: int, response: ResponseUpdate):
    """Update an existing response."""
    existing = crud.get_response(response_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Response not found")

    # Validate foreign keys if provided
    if response.function_id and not crud.get_function(response.function_id):
        raise HTTPException(status_code=400, detail="Invalid function_id")
    if response.team_id and not crud.get_team(response.team_id):
        raise HTTPException(status_code=400, detail="Invalid team_id")
    if response.capability_id and not crud.get_capability(response.capability_id):
        raise HTTPException(status_code=400, detail="Invalid capability_id")

    return crud.update_response(response_id, response)


@router.delete("/responses/{response_id}")
async def delete_response(response_id: int):
    """Delete a response."""
    if not crud.get_response(response_id):
        raise HTTPException(status_code=404, detail="Response not found")

    crud.delete_response(response_id)
    return {"message": "Response deleted successfully"}


# ============ Dashboard Endpoints ============

@router.get("/dashboard/summary", response_model=dict)
async def get_dashboard_summary():
    """Get aggregated dashboard summary."""
    return crud.get_dashboard_summary()


@router.get("/dashboard/by-function", response_model=List[dict])
async def get_dashboard_by_function():
    """Get dashboard breakdown by function."""
    return crud.get_dashboard_by_function()


@router.get("/dashboard/by-team", response_model=List[dict])
async def get_dashboard_by_team():
    """Get dashboard breakdown by team."""
    return crud.get_dashboard_by_team()


@router.get("/dashboard/impact-types", response_model=List[dict])
async def get_dashboard_impact_types():
    """Get dashboard breakdown by impact type."""
    return crud.get_dashboard_impact_types()


@router.get("/dashboard/tools-used", response_model=List[dict])
async def get_dashboard_tools_used():
    """Get dashboard breakdown by tools used."""
    return crud.get_dashboard_tools_used()


@router.get("/dashboard/capabilities", response_model=List[dict])
async def get_dashboard_capabilities():
    """Get dashboard breakdown by capability."""
    return crud.get_dashboard_capabilities()


@router.get("/dashboard/by-category", response_model=dict)
async def get_dashboard_by_category():
    """Get dashboard breakdown by category (workflow, task, experiment)."""
    return crud.get_dashboard_by_category()


@router.get("/dashboard/functions-with-teams", response_model=List[dict])
async def get_dashboard_functions_with_teams():
    """Get dashboard functions with teams breakdown (including teamless functions)."""
    return crud.get_dashboard_by_function_with_teams()
