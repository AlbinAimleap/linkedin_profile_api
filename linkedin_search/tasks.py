import aioredis
import os

# Connect to Redis
redis_client = aioredis.from_url(
    f"redis://{os.getenv('REDIS_HOST', 'redis')}:6379/0",
    decode_responses=True
)

class Task:
    @staticmethod
    async def save(task_id, status, output=None):
        task_data = {
            'id': task_id,
            'status': status,
            'output': output if output is not None else ''
        }
        await redis_client.hmset(f"task:{task_id}", task_data)

    @staticmethod
    async def get(task_id):
        return await redis_client.hgetall(f"task:{task_id}")

    @staticmethod
    async def get_all_keys():
        keys = await redis_client.keys("task:*")
        return [key.replace("task:", "") for key in keys]

    @staticmethod
    async def save_search_history(query: str, profiles: str):
        await redis_client.set(f"search_history:{query}", profiles)

    @staticmethod
    async def get_search_history(query: str):
        return await redis_client.get(f"search_history:{query}")