import unittest
import asyncio
import os

class FakePipeline:
    def __init__(self, store, key):
        self.store = store
        self.key = key
        self.ops = []
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        return False
    async def get(self, key):
        self.ops.append(("get", key))
    async def delete(self, key):
        self.ops.append(("del", key))
    async def execute(self):
        data = self.store.get(self.key)
        self.store.pop(self.key, None)
        return [data, 1]

class FakeRedis:
    def __init__(self):
        self._store = {}
        # intentionally no getdel method
    async def set(self, key, value, ex=None):
        self._store[key] = value
    def pipeline(self):
        # returns async context manager
        return FakePipeline(self._store, key=self._pending_key)
    # Helper to mimic from_url interface
    @property
    def _pending_key(self):
        # last key used by tests
        return self._last_key
    async def close(self):
        pass

class TestRedisFallback(unittest.TestCase):
    def test_getdel_fallback_pipeline(self):
        # Prepare minimal env for config.Settings to initialize
        os.environ.setdefault("BOT_TOKEN", "TEST_TOKEN")
        os.environ.setdefault("MEILI_MASTER_KEY", "TEST_KEY")
        os.environ.setdefault("PG_DSN", "postgresql://user:password@localhost:5432/bookbot")
        os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
        from services import RedisService
        svc = RedisService()
        # override redis client with FakeRedis
        fake = FakeRedis()
        svc.redis = fake
        svc.supports_getdel = False
        # prepare data
        key = "pending:abcd1234"
        fake._last_key = key
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(fake.set(key, '{"file_id":"x"}'))
            result = loop.run_until_complete(svc.get_and_delete_upload_session("abcd1234"))
        finally:
            loop.close()
        self.assertEqual(result["file_id"], "x")

if __name__ == "__main__":
    unittest.main()
