"""
scripts/patch_graphs_add_info_agent.py

One-time migration: adds info_agent node + 3 new edges (list_services,
list_staff, check_slots) to every deployed graph that doesn't already
have them. Creates a new graph version and sets it as active.

Run once after deploying the info_agent feature:
    conda run -n appt_agent python scripts/patch_graphs_add_info_agent.py
"""

import asyncio
import copy
import logging
import sys
import uuid

sys.path.insert(0, ".")
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

INFO_NODE = {
    "id": "info_agent",
    "type": "info_agent",
    "config": {},
    "position": {"x": 250, "y": 160},
}

NEW_EDGES = [
    {"id": "ei_ls", "source": "intent_classifier", "target": "info_agent", "condition": "list_services"},
    {"id": "ei_lf", "source": "intent_classifier", "target": "info_agent", "condition": "list_staff"},
    {"id": "ei_cs", "source": "intent_classifier", "target": "info_agent", "condition": "check_slots"},
    {"id": "ei_end", "source": "info_agent", "target": "__end__", "condition": None},
]


async def patch():
    from sqlalchemy import select, update
    from backend.core.database import engine
    from backend.models.graph import Graph, GraphVersion
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        # Fetch all deployed graphs
        result = await db.execute(
            select(Graph).where(Graph.is_deployed == True)
        )
        graphs = list(result.scalars().all())
        logger.info(f"Found {len(graphs)} deployed graph(s)")

        patched = 0
        for graph in graphs:
            # Fetch active version
            ver_result = await db.execute(
                select(GraphVersion).where(
                    GraphVersion.graph_id == graph.id,
                    GraphVersion.tenant_id == graph.tenant_id,
                    GraphVersion.version == graph.active_version,
                )
            )
            version_row = ver_result.scalar_one_or_none()
            if not version_row:
                logger.warning(f"  SKIP  graph {graph.id} — active version not found")
                continue

            definition = copy.deepcopy(version_row.definition)
            node_ids = {n["id"] for n in definition.get("nodes", [])}
            edge_ids_conditions = {
                (e["source"], e.get("condition")) for e in definition.get("edges", [])
            }

            if "info_agent" in node_ids:
                logger.info(f"  SKIP  graph {graph.id} ({graph.name}) — info_agent already present")
                continue

            # Add node
            definition["nodes"].append(INFO_NODE)

            # Add edges (only if not already present)
            for edge in NEW_EDGES:
                key = (edge["source"], edge.get("condition"))
                if key not in edge_ids_conditions:
                    definition["edges"].append(edge)

            # Create new version
            new_version_num = graph.active_version + 1
            from datetime import datetime, timezone
            new_version = GraphVersion(
                id=uuid.uuid4(),
                graph_id=graph.id,
                tenant_id=graph.tenant_id,
                version=new_version_num,
                definition=definition,
                is_active=True,
                compiled_at=datetime.now(timezone.utc),
            )
            db.add(new_version)

            # Update graph active_version
            graph.active_version = new_version_num

            patched += 1
            logger.info(f"  PATCH graph {graph.id} ({graph.name}) → v{new_version_num}")

        await db.commit()
        logger.info(f"\nDone. {patched} graph(s) patched.")


if __name__ == "__main__":
    asyncio.run(patch())
