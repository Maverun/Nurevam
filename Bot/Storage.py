import aioredis
import asyncio
import datetime

class Redis:
    def __init__(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self.Start())
        
    async def Start(self):
        return await aioredis.create_redis(('localhost',6379),
            encoding='utf8',db=2
        )

    async def Save(self,Bool):
        if not Bool:
            self.data = await self.Start()
        await self.data.bgsave()
        Current_Time = datetime.datetime.utcnow().strftime("%b/%d/%Y %H:%M:%S UTC")
        print(Current_Time)
        await asyncio.sleep(300)
        return await self.Save(True)
