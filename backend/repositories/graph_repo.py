"""
repositories/graph_repo.py

DB access for agent graphs and version snapshots.
Every save creates a new graph_versions row — never overwrites (R6).
"""

import uuid
import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.graph import Graph, GraphVersion
from backend.schemas.graph import GraphCreate, GraphDefinition

logger = logging.getLogger(__name__)


async def get_graph_by_id(
    db: AsyncSession, tenant_id: uuid.UUID, graph_id: uuid.UUID
) -> Optional[Graph]:
    result = await db.execute(
        select(Graph).where(
            Graph.id == graph_id,
            Graph.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def list_graphs(
    db: AsyncSession, tenant_id: uuid.UUID
) -> List[Graph]:
    result = await db.execute(
        select(Graph)
        .where(Graph.tenant_id == tenant_id)
        .order_by(Graph.created_at.desc())
    )
    return list(result.scalars().all())


async def create_graph(
    db: AsyncSession, tenant_id: uuid.UUID, data: GraphCreate
) -> Graph:
    """Create a new graph and its first version snapshot."""
    graph = Graph(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=data.name,
        description=data.description,
        active_version=1,
        is_deployed=False,
    )
    db.add(graph)
    await db.flush()  # get graph.id before creating version

    version = GraphVersion(
        id=uuid.uuid4(),
        graph_id=graph.id,
        tenant_id=tenant_id,
        version=1,
        definition=data.definition.model_dump(),
        is_active=False,
    )
    db.add(version)

    logger.info(
        "graph_created",
        extra={"tenant_id": str(tenant_id), "graph_id": str(graph.id)},
    )
    return graph


async def save_new_version(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    graph: Graph,
    new_definition: GraphDefinition,
) -> GraphVersion:
    """
    Increment graph version and create a new snapshot row (R6).
    The previous version row is preserved — never updated.
    """
    graph.active_version += 1

    version = GraphVersion(
        id=uuid.uuid4(),
        graph_id=graph.id,
        tenant_id=tenant_id,
        version=graph.active_version,
        definition=new_definition.model_dump(),
        is_active=False,
    )
    db.add(version)

    logger.info(
        "graph_version_saved",
        extra={
            "tenant_id": str(tenant_id),
            "graph_id": str(graph.id),
            "version": graph.active_version,
        },
    )
    return version


async def get_graph_version(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    graph_id: uuid.UUID,
    version: int,
) -> Optional[GraphVersion]:
    result = await db.execute(
        select(GraphVersion).where(
            GraphVersion.graph_id == graph_id,
            GraphVersion.tenant_id == tenant_id,
            GraphVersion.version == version,
        )
    )
    return result.scalar_one_or_none()


async def get_all_versions(
    db: AsyncSession, tenant_id: uuid.UUID, graph_id: uuid.UUID
) -> List[GraphVersion]:
    result = await db.execute(
        select(GraphVersion)
        .where(
            GraphVersion.graph_id == graph_id,
            GraphVersion.tenant_id == tenant_id,
        )
        .order_by(GraphVersion.version.desc())
    )
    return list(result.scalars().all())


async def deploy_graph_version(
    db: AsyncSession,
    graph: Graph,
    version_row: GraphVersion,
) -> Graph:
    """
    Mark a specific version as active and set graph.is_deployed = True.
    Deactivates the previously active version row first.
    """
    # Deactivate all other versions for this graph
    all_versions = await get_all_versions(db, graph.tenant_id, graph.id)
    for v in all_versions:
        v.is_active = False

    version_row.is_active = True
    graph.active_version = version_row.version
    graph.is_deployed = True

    logger.info(
        "graph_deployed",
        extra={
            "tenant_id": str(graph.tenant_id),
            "graph_id": str(graph.id),
            "version": version_row.version,
        },
    )
    return graph
