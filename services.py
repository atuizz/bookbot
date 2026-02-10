import asyncio
import json
import logging
import meilisearch
import asyncpg
import redis.asyncio as redis
from config import config
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

class MeilisearchService:
    def __init__(self):
        self.client = meilisearch.Client(config.MEILI_HOST, config.MEILI_MASTER_KEY)
        self.index_name = "books"
        self.index = self.client.index(self.index_name)

    async def init_index(self):
        """Initialize Meilisearch index settings for optimal performance."""
        # Run in executor because meilisearch-python-sdk is synchronous (mostly)
        # or we use the async client if available, but the standard lib is sync.
        # We will wrap sync calls in run_in_executor for async compatibility.
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._configure_index)

    def _configure_index(self):
        try:
            # Create index if not exists
            try:
                self.client.get_index(self.index_name)
            except Exception:
                self.client.create_index(self.index_name, {'primaryKey': 'id'})
            
            # Update settings
            self.index.update_settings({
                'searchableAttributes': [
                    'title',
                    'author',
                    'tags',
                    'file_name'
                ],
                'filterableAttributes': [
                    'tags',
                    'author',
                    'ext',
                    'file_size',
                    'word_count',
                    'content_rating'
                ],
                'sortableAttributes': [
                    'created_at',
                    'downloads',
                    'file_size'
                ],
                'rankingRules': [
                    'words',
                    'typo',
                    'proximity',
                    'attribute',
                    'sort',
                    'exactness'
                ],
                'typoTolerance': {
                    'minWordSizeForTypos': {
                        'oneTypo': 5,
                        'twoTypos': 9
                    }
                },
                'pagination': {
                    'maxTotalHits': 1000
                }
            })
            logger.info("Meilisearch index configured successfully.")
        except Exception as e:
            err_type = type(e).__name__
            logger.error(f"Failed to configure Meilisearch [{err_type}]: {e}")

    async def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        filter: Optional[str] = None,
        sort: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        options = {
            'limit': limit,
            'offset': offset,
            'attributesToHighlight': ['title', 'author'],
        }
        if filter:
            options['filter'] = filter
        if sort:
            options["sort"] = sort
        return await loop.run_in_executor(None, lambda: self.index.search(query, options))

    async def add_documents(self, documents: List[Dict[str, Any]]):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: self.index.add_documents(documents))

    async def delete_document(self, document_id: str):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: self.index.delete_document(document_id))


class DatabaseService:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(config.PG_DSN)
        await self.init_db()

    async def init_db(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id SERIAL PRIMARY KEY,
                    file_id TEXT UNIQUE NOT NULL,
                    file_unique_id TEXT NOT NULL,
                    file_name TEXT,
                    file_size BIGINT,
                    title TEXT,
                    author TEXT,
                    tags TEXT[],
                    downloads INT DEFAULT 0,
                    collections INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    uploader_id BIGINT
                );
                CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);
                CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
                CREATE UNIQUE INDEX IF NOT EXISTS uniq_books_file_unique_id ON books(file_unique_id);
            """)

    async def add_book(self, book_data: Dict[str, Any]) -> int:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO books (file_id, file_unique_id, file_name, file_size, title, author, tags, uploader_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (file_unique_id) DO NOTHING
                RETURNING id
            """, book_data['file_id'], book_data['file_unique_id'], book_data['file_name'],
               book_data['file_size'], book_data.get('title'), book_data.get('author'),
               book_data.get('tags', []), book_data.get('uploader_id'))
            if row:
                return row['id']
            existing = await conn.fetchrow("SELECT id FROM books WHERE file_unique_id = $1", book_data['file_unique_id'])
            return existing['id']

    async def get_book(self, book_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM books WHERE id = $1", book_id)
            
    async def get_book_by_file_unique_id(self, file_unique_id: str):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM books WHERE file_unique_id = $1", file_unique_id)

    async def increment_download(self, book_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE books SET downloads = downloads + 1 WHERE id = $1", book_id)

    async def close(self):
        if self.pool:
            await self.pool.close()


class RedisService:
    def __init__(self):
        self.redis = redis.from_url(config.REDIS_URL, encoding="utf-8", decode_responses=True)
        self.supports_getdel = hasattr(self.redis, "getdel")

    async def cache_search_context(self, user_id: int, query: str, filter_type: str = None):
        data = json.dumps(
            {
                "query": query,
                "filter": filter_type,
                "page": 0,
                "sort": "best",
                "filters": {},
            }
        )
        await self.redis.set(f"search_ctx:{user_id}", data, ex=3600)

    async def get_search_context(self, user_id: int) -> Optional[Dict[str, Any]]:
        data = await self.redis.get(f"search_ctx:{user_id}")
        if not data:
            return None
        ctx = json.loads(data)
        if "page" not in ctx:
            ctx["page"] = 0
        if "sort" not in ctx:
            ctx["sort"] = "best"
        if "filters" not in ctx or ctx["filters"] is None:
            ctx["filters"] = {}
        return ctx

    async def update_search_context(self, user_id: int, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ctx = await self.get_search_context(user_id)
        if not ctx:
            return None
        merged = {**ctx, **patch}
        await self.redis.set(f"search_ctx:{user_id}", json.dumps(merged), ex=3600)
        return merged

    async def get_user_settings(self, user_id: int) -> Dict[str, Any]:
        defaults = {
            "content_rating": "ALL",
            "search_button_mode": "preview",
            "hide_personal_info": False,
            "hide_upload_list": False,
            "mute_upload_feedback": False,
            "mute_invite_feedback": False,
            "mute_feed": False,
        }
        data = await self.redis.get(f"user_settings:{user_id}")
        if not data:
            return defaults
        try:
            stored = json.loads(data)
            if isinstance(stored, dict):
                return {**defaults, **stored}
        except Exception:
            return defaults
        return defaults

    async def update_user_settings(self, user_id: int, patch: Dict[str, Any]) -> Dict[str, Any]:
        current = await self.get_user_settings(user_id)
        merged = {**current, **patch}
        await self.redis.set(f"user_settings:{user_id}", json.dumps(merged), ex=7776000)
        return merged

    async def create_upload_session(self, file_data: Dict[str, Any]) -> str:
        """Store upload data temporarily and return a short ID."""
        import uuid
        short_id = uuid.uuid4().hex[:8]
        await self.redis.set(f"pending:{short_id}", json.dumps(file_data), ex=86400)
        return short_id

    async def get_and_delete_upload_session(self, short_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve and delete upload session atomically."""
        # Use getdel if available (Redis 6.2+), else get and del
        # python-redis supports getdel
        if self.supports_getdel:
            data = await self.redis.getdel(f"pending:{short_id}")
        else:
            logger.debug("Redis getdel not supported, falling back to pipeline get+delete.")
            async with self.redis.pipeline() as pipe:
                await pipe.get(f"pending:{short_id}")
                await pipe.delete(f"pending:{short_id}")
                res = await pipe.execute()
                data = res[0]
        
        return json.loads(data) if data else None

    async def close(self):
        await self.redis.close()

# Singleton instances
meili_service = MeilisearchService()
db_service = DatabaseService()
redis_service = RedisService()
