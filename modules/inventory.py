import random, time
from location import Location
from modules.base_module import Module

class_name = "Inventory"

class Inventory(Module):
    prefix = 'tr'
    def __init__(self, server):
        self.server = server
        self.commands = {'bgch': self.buy_game_chips}

    async def buy_game_chips(self, msg, client):
        res = await Location(self.server, client).gen_plr()
        if res['res']['gld'] < msg['data']['gld']:
            return
        await self.server.redis.set(f'uid:{client.uid}.gld',
                        res['res']['gld'] - msg['data']['gld'])
        await self.server.add_item(client.uid, 'gameChips', 'gm', msg['data']['gld'])
        inv = await Location(self.server, client)._get_inventory()
        return await client.send({'data': {'inv': inv}, 'command': 'ntf.inv'})
