from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import meilisearch
import pymysql
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Arsip Search API",
    description="API for searching arsip documents via Meilisearch",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MEILI_URL = os.getenv("MEILI_URL", "http://localhost:7700")
MEILI_KEY = os.getenv("MEILI_KEY", "arsipsearch2024")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3307"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root123")
MYSQL_DB = os.getenv("MYSQL_DB", "arsipserverdb2")

INDEX_NAME = "arsip_tata_all"

meili_client = meilisearch.Client(MEILI_URL, MEILI_KEY)

class SearchResult(BaseModel):
    id: str
    source_table: str
    code: Optional[str]
    description: Optional[str]
    year_bundle: Optional[int]
    yeardate: Optional[int]
    box_number: Optional[str]
    bundle_number: Optional[int]
    title: Optional[str]
    item_number: Optional[int]
    name: Optional[str]
    organization: Optional[str]
    creator: Optional[str]
    bundle_code: Optional[str]
    filesize: Optional[int]
    page_count: Optional[int]

class SearchResponse(BaseModel):
    query: str
    total: int
    processing_time_ms: int
    results: List[SearchResult]

@app.get("/health")
async def health():
    try:
        meili_client.health()
        return {"status": "healthy", "meilisearch": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "meilisearch": "disconnected", "error": str(e)}

@app.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    year: Optional[int] = None,
    table: Optional[str] = None
):
    try:
        index = meili_client.index(INDEX_NAME)

        filters = []
        if year:
            filters.append(f"yeardate = {year}")
        if table:
            filters.append(f"source_table = '{table}'")

        filter_str = " AND ".join(filters) if filters else None

        search_params = {
            "limit": limit,
            "offset": offset,
            "attributesToRetrieve": [
                "id", "source_table", "code", "description", "year_bundle",
                "yeardate", "box_number", "bundle_number", "title", "item_number",
                "name", "organization", "creator", "bundle_code", "filesize", "page_count"
            ],
        }
        if filter_str:
            search_params["filter"] = filter_str

        result = index.search(q, search_params)

        hits = []
        for hit in result["hits"]:
            hits.append(SearchResult(
                id=hit["id"],
                source_table=hit.get("source_table", ""),
                code=hit.get("code") or "",
                description=hit.get("description"),
                year_bundle=hit.get("year_bundle"),
                yeardate=hit.get("yeardate"),
                box_number=hit.get("box_number") or "",
                bundle_number=hit.get("bundle_number"),
                title=hit.get("title") or "",
                item_number=hit.get("item_number"),
                name=hit.get("name") or "",
                organization=hit.get("organization") or "",
                creator=hit.get("creator") or "",
                bundle_code=hit.get("bundle_code") or "",
                filesize=hit.get("filesize"),
                page_count=hit.get("page_count"),
            ))

        return SearchResponse(
            query=q,
            total=result.get("estimatedTotalHits", len(hits)),
            processing_time_ms=result.get("processingTimeMs", 0),
            results=hits
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sync", tags=["sync"])
async def sync_to_meilisearch():
    try:
        conn = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
            charset='utf8mb4'
        )

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        documents = []
        total_indexed = {}

        tables_config = [
            {
                "name": "arsip_tata_year",
                "select": """
                    SELECT id, yeardate, NULL as description, NULL as code, NULL as box_number,
                           NULL as bundle_number, NULL as title, NULL as item_number,
                           NULL as name, NULL as organization, NULL as creator
                    FROM arsip_tata_year
                """,
                "id_prefix": "year_"
            },
            {
                "name": "arsip_tata_box",
                "select": """
                    SELECT b.id, b.box_number, b.yeardate, b.notes as description,
                           NULL as code, NULL as bundle_number, NULL as title, NULL as item_number,
                           NULL as name, NULL as organization, NULL as creator
                    FROM arsip_tata_box b
                """,
                "id_prefix": "box_"
            },
            {
                "name": "arsip_tata_bundle",
                "select": """
                    SELECT
                        b.id,
                        b.code,
                        b.description,
                        b.year_bundle,
                        b.yeardate,
                        b.bundle_number,
                        bx.box_number,
                        b.creator
                    FROM arsip_tata_bundle b
                    INNER JOIN arsip_tata_box bx ON b.box_id = bx.id
                """,
                "id_prefix": "bundle_"
            },
            {
                "name": "arsip_tata_item",
                "select": """
                    SELECT
                        i.id,
                        i.item_number,
                        i.title,
                        i.codegen,
                        i.yeardate,
                        i.filesize,
                        i.page_count,
                        b.bundle_number,
                        b.code AS bundle_code,
                        b.creator,
                        b.description AS bundle_description,
                        b.year_bundle,
                        bx.box_number,
                        bx.yeardate AS box_year
                    FROM arsip_tata_box bx
                    INNER JOIN arsip_tata_bundle b ON bx.id = b.box_id
                    INNER JOIN arsip_tata_item i ON i.bundle_id = b.id
                """,
                "id_prefix": "item_"
            },
        ]

        for cfg in tables_config:
            cursor.execute(cfg["select"])
            rows = cursor.fetchall()
            count = 0
            for row in rows:
                # Build description: title + bundle_description (like user's CONCAT)
                desc_parts = []
                if row.get("title"):
                    desc_parts.append(str(row["title"]))
                if row.get("bundle_description"):
                    desc_parts.append(str(row["bundle_description"]))
                description = " ".join(desc_parts)

                doc = {
                    "id": f"{cfg['id_prefix']}{row['id']}",
                    "source_table": cfg["name"],
                    "code": row.get("codegen") or row.get("bundle_code") or "",
                    "description": description,
                    "year_bundle": row.get("year_bundle"),
                    "yeardate": row.get("yeardate"),
                    "box_number": row.get("box_number") or "",
                    "bundle_number": row.get("bundle_number"),
                    "creator": row.get("creator") or "",
                    "title": row.get("title") or "",
                    "item_number": row.get("item_number"),
                    "name": "",
                    "organization": "",
                    "bundle_code": row.get("bundle_code") or "",
                    "filesize": row.get("filesize"),
                    "page_count": row.get("page_count"),
                }
                documents.append(doc)
                count += 1
            total_indexed[cfg["name"]] = count

        cursor.close()
        conn.close()

        # Clear existing index and re-index
        try:
            meili_client.delete_index(INDEX_NAME)
        except:
            pass

        task = meili_client.create_index(INDEX_NAME, {"primaryKey": "id"})
        meili_client.wait_for_task(task.task_uid)

        index = meili_client.index(INDEX_NAME)

        task = index.add_documents(documents)

        index.update_settings({
            "searchableAttributes": [
                "description", "code", "box_number", "title",
                "bundle_code", "creator", "name", "organization"
            ],
            "filterableAttributes": ["source_table", "yeardate", "year_bundle", "box_number", "bundle_number"],
            "sortableAttributes": ["yeardate", "year_bundle"],
            "rankingRules": [
                "words", "typo", "proximity", "attribute", "sort", "exactness"
            ]
        })

        return {
            "status": "success",
            "indexed": total_indexed,
            "total_documents": len(documents),
            "task_uid": task.task_uid
        }
    except Exception as e:
        logger.error(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/index/stats", tags=["index"])
async def index_stats():
    try:
        index = meili_client.index(INDEX_NAME)
        stats = index.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)
