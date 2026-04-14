"""
api/graphs.py

Agent graph builder endpoints.

POST   /api/v1/graphs           — create new graph
GET    /api/v1/graphs           — list tenant's graphs
GET    /api/v1/graphs/{id}      — get graph with versions
PUT    /api/v1/graphs/{id}      — save new version
POST   /api/v1/graphs/{id}/deploy  — deploy specific version
GET    /api/v1/graphs/{id}/versions — list all versions
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_tenant
from backend.models.tenant import Tenant
from backend.repositories.graph_repo import (
    create_graph,
    deploy_graph_version,
    get_all_versions,
    get_graph_by_id,
    get_graph_version,
    list_graphs,
    save_new_version,
)
from backend.schemas.common import APIResponse
from backend.schemas.graph import (
    GraphCreate,
    GraphDeployRequest,
    GraphResponse,
    GraphUpdate,
    GraphVersionResponse,
)

router = APIRouter(prefix="/graphs", tags=["Graphs"])
logger = logging.getLogger(__name__)


@router.post(
    "",
    response_model=APIResponse[GraphResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_new_graph(
    data: GraphCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[GraphResponse]:
    if not tenant.onboarding_completed:
        raise HTTPException(
            status_code=403,
            detail="Complete onboarding before creating graphs.",
        )

    graph = await create_graph(db, tenant.id, data)
    return APIResponse.ok(GraphResponse.model_validate(graph))


@router.get(
    "",
    response_model=APIResponse[list[GraphResponse]],
)
async def list_tenant_graphs(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[GraphResponse]]:
    graphs = await list_graphs(db, tenant.id)
    return APIResponse.ok([GraphResponse.model_validate(g) for g in graphs])


@router.get(
    "/{graph_id}",
    response_model=APIResponse[GraphResponse],
)
async def get_graph(
    graph_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[GraphResponse]:
    graph = await get_graph_by_id(db, tenant.id, graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found.")
    return APIResponse.ok(GraphResponse.model_validate(graph))


@router.put(
    "/{graph_id}",
    response_model=APIResponse[GraphVersionResponse],
)
async def save_graph_version(
    graph_id: uuid.UUID,
    data: GraphUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[GraphVersionResponse]:
    """Save a new version of the graph (increments version counter)."""
    graph = await get_graph_by_id(db, tenant.id, graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found.")

    version_row = await save_new_version(db, tenant.id, graph, data.definition)
    return APIResponse.ok(GraphVersionResponse.model_validate(version_row))


@router.post(
    "/{graph_id}/deploy",
    response_model=APIResponse[GraphResponse],
)
async def deploy_graph(
    graph_id: uuid.UUID,
    data: GraphDeployRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[GraphResponse]:
    """Deploy a specific version of a graph (makes it live for /chat)."""
    graph = await get_graph_by_id(db, tenant.id, graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found.")

    version_row = await get_graph_version(db, tenant.id, graph_id, data.version)
    if not version_row:
        raise HTTPException(
            status_code=404, detail=f"Version {data.version} not found."
        )

    updated_graph = await deploy_graph_version(db, graph, version_row)

    # Invalidate Redis cache for old version
    import redis.asyncio as aioredis
    from backend.core.config import settings
    redis = aioredis.from_url(settings.REDIS_URL)
    await redis.delete(f"graph:{graph_id}:v{data.version}")

    logger.info(
        "graph_deployed_via_api",
        extra={"tenant_id": str(tenant.id), "graph_id": str(graph_id), "version": data.version},
    )

    return APIResponse.ok(GraphResponse.model_validate(updated_graph))


@router.get(
    "/{graph_id}/versions",
    response_model=APIResponse[list[GraphVersionResponse]],
)
async def get_graph_versions(
    graph_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[GraphVersionResponse]]:
    graph = await get_graph_by_id(db, tenant.id, graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found.")

    versions = await get_all_versions(db, tenant.id, graph_id)
    return APIResponse.ok([GraphVersionResponse.model_validate(v) for v in versions])
