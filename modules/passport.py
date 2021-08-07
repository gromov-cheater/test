from location import Location
from modules.base_module import Module

class_name = "Passport"

class Passport(Module):
    prefix = 'psp'
    def __init__(self, server):
        self.server = server
        self.commands = {'psp': self.passport, 'pspdr': self.dress_passport}

    async def dress_passport(self, msg, client):
        if not await self.server.redis.get(f"uid:{client.uid}:premium"):
            return
        if msg['data']['dr']:
            await self.server.redis.delete(f"uid:{client.uid}:dr")
        else:
            await self.server.redis.set(f"uid:{client.uid}:dr", 1)
        return await Location(self.server, client).ntf_ci()

    async def passport(self, msg, client):
        return await client.send({
            'data': {'psp': {'uid': msg['data']['uid'],
                             'ach': {'ac': {}}, 'rel': {}}},
            'command': 'psp.psp'
        })
