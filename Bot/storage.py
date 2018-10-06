from cogs.utils import utils
import aioredis
import asyncio
import sqlite3

class Redis:
    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.Start())

    async def Start(self):
        utils.prYellow("AIOREDIS")
        self.redis = await aioredis.create_redis((utils.secret["Redis"],6379),encoding='utf8')


class SQL:
    def __init__(self,name):
        self.db = sqlite3.connect(name)
        self.db.row_factory = sqlite3.Row #So I can get more info from getting values such as column name etc.
        self.cursor = self.db.cursor()

    def create_table(self,query):
        try:
            self.cursor.execute(query)
        except sqlite3.Error as e:
            utils.prRed(e)

    def add(self,query,value):
        self.cursor.execute(query,value)
        self.db.commit()
        return self.cursor.lastrowid

    def update(self,query,value):
        self.cursor.execute(query,value)
        self.db.commit()
        return self.cursor.lastrowid

    def delete(self,query,value):
        self.cursor.execute(query,value)
        self.db.commit()

    def get(self,query,value = (),isAll = False):
        result = self.cursor.execute(query,value)
        if isAll:
            if isinstance(isAll,int):#checking if it int, if it , then we can fetch certain amount
                return result.fetchmany(isAll)
            return result.fetchall()
        return result.fetchone()

    """
    This is DOC for references so I can always check here to get query I want.
    A common one at least.
    
    getting values:
    
    SELECT * FROM {TABLE} WHERE user_ID = ?
    
    SELECT * FROM {TABLE} WHERE guild_ID = ?
    
    
    Add values:
    
    INSERT into {TABLE} values (?,?)
    
    Update:
    
    UPDATE {TABLE} SET {COL1} = ?,{COL2} = ? WHERE {CONDITIONS}
    ***CONDITIONS IS MUST!
    
    
    
    
    """
