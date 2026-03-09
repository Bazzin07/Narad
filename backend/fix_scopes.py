import asyncio
from sqlalchemy import select
from app.database import async_session
from app.models.article import Article
from app.services.geo_scope_classifier import classify_geo_scope

async def fix_database_scopes():
    async with async_session() as db:
        result = await db.execute(select(Article))
        articles = result.scalars().all()
        updated = 0
        for a in articles:
            new_scope = classify_geo_scope(
                title=a.title,
                content=a.content,
                source_region="india" if "BBC" not in a.source and "NYT" not in a.source and "Global" not in a.source else "global",
                language=a.language
            )
            if a.geographic_scope != new_scope:
                print(f"Updating '{a.title[:60]}' from {a.geographic_scope} -> {new_scope}")
                a.geographic_scope = new_scope
                updated += 1
        
        if updated > 0:
            await db.commit()
            print(f"\nSuccessfully updated {updated} articles.")
        else:
            print("No scope updates needed.")

if __name__ == "__main__":
    asyncio.run(fix_database_scopes())
