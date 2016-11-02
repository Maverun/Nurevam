import aioredis
import asyncio
from cogs.utils import utils

class Redis:
    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.Start())

    async def Start(self):
        utils.prYellow("AIOREDIS")
        self.redis = await aioredis.create_redis((utils.secret["Redis"],6379),encoding='utf8')
