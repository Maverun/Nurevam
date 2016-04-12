import aioredis
import asyncio
import datetime

class Redis:
    def __init__(self):
        # self.data=redis.Redis(host='192.168.2.2',decode_responses=True,db=2)
        loop = asyncio.get_event_loop()
        loop.create_task(self.Start())

    async def Start(self):
        self.data = await aioredis.create_redis('localhost',
            encoding='utf8'
        )
        pass
    async def Save(self):
        self.data.bgsave()
        Current_Time = datetime.datetime.utcnow().strftime("%b/%d/%Y %H:%M:%S UTC")
        print(Current_Time)
        await asyncio.sleep(300)
        return await self.Save()
