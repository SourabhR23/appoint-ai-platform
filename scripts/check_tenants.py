import asyncio, sys
sys.path.insert(0, '.')
from sqlalchemy import text

async def check():
    from backend.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        result = await db.execute(text(
            "SELECT name, subdomain, email, hashed_password IS NOT NULL as has_pw FROM tenants ORDER BY created_at"
        ))
        rows = result.fetchall()
        print("Tenants in DB:")
        for r in rows:
            print(f"  {r.name:30s} | {r.subdomain:15s} | {r.email:35s} | has_password={r.has_pw}")

asyncio.run(check())
