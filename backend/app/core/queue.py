import abc
import asyncio
import json
from typing import Any, Callable, Dict, Optional
from app.core.config import settings
from app.core.logging import logger


class BaseTaskBroker(abc.ABC):
    """Abstract interface for queuing async document ingestion & extraction jobs."""

    @abc.abstractmethod
    async def enqueue(self, task_name: str, payload: Dict[str, Any], priority: int = 0) -> str:
        """Enqueues a background task and returns task_id."""
        pass

    @abc.abstractmethod
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves task state and metadata."""
        pass

    @abc.abstractmethod
    async def is_healthy(self) -> bool:
        """Checks broker connectivity."""
        pass


class InMemoryTaskBroker(BaseTaskBroker):
    """In-memory broker for local testing, development, and unit test execution."""

    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._queue: asyncio.Queue = asyncio.Queue()

    async def enqueue(self, task_name: str, payload: Dict[str, Any], priority: int = 0) -> str:
        import uuid
        task_id = f"task_{uuid.uuid4()}"
        task_record = {
            "task_id": task_id,
            "task_name": task_name,
            "payload": payload,
            "status": "QUEUED",
            "priority": priority,
            "result": None,
            "error": None,
        }
        self._tasks[task_id] = task_record
        await self._queue.put(task_record)
        logger.info("Enqueued task %s (%s) [broker: in-memory]", task_id, task_name)
        return task_id

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._tasks.get(task_id)

    async def is_healthy(self) -> bool:
        return True


class RedisTaskBroker(BaseTaskBroker):
    """Redis-backed queue broker for distributed worker nodes."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._fallback = InMemoryTaskBroker()

    async def enqueue(self, task_name: str, payload: Dict[str, Any], priority: int = 0) -> str:
        try:
            import redis.asyncio as aioredis
            client = aioredis.from_url(self.redis_url, socket_connect_timeout=0.2, decode_responses=True)
            import uuid
            task_id = f"task_{uuid.uuid4()}"
            task_data = json.dumps({
                "task_id": task_id,
                "task_name": task_name,
                "payload": payload,
                "status": "QUEUED",
            })
            await client.lpush("nidan_task_queue", task_data)
            await client.set(f"nidan_task:{task_id}", task_data, ex=86400)
            await client.aclose()
            logger.info("Enqueued task %s (%s) [broker: redis]", task_id, task_name)
            return task_id
        except Exception as e:
            logger.warning("Redis broker unavailable (%s), using in-memory queue fallback", str(e))
            return await self._fallback.enqueue(task_name, payload, priority)

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        try:
            import redis.asyncio as aioredis
            client = aioredis.from_url(self.redis_url, socket_connect_timeout=0.2, decode_responses=True)
            data = await client.get(f"nidan_task:{task_id}")
            await client.aclose()
            if data:
                return json.loads(data)
            return None
        except Exception:
            return await self._fallback.get_task_status(task_id)

    async def is_healthy(self) -> bool:
        try:
            import redis.asyncio as aioredis
            client = aioredis.from_url(self.redis_url, socket_connect_timeout=0.2)
            await client.ping()
            await client.aclose()
            return True
        except Exception:
            return False


_global_broker: Optional[BaseTaskBroker] = None


def get_task_broker() -> BaseTaskBroker:
    global _global_broker
    if _global_broker is None:
        if settings.ENVIRONMENT == "test":
            _global_broker = InMemoryTaskBroker()
        elif settings.REDIS_URL.startswith("redis"):
            _global_broker = RedisTaskBroker(settings.REDIS_URL)
        else:
            _global_broker = InMemoryTaskBroker()
    return _global_broker
