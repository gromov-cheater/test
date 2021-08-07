from location import Location
from modules.base_module import Module

class_name = "Billing"

class Billing(Module):
    prefix = 'b'
    def __init__(self, server):
        self.server = server
        self.commands = {'bs': self.buy_silver, 'ren': self.buy_energy}

    async def buy_coint(self, msg, client):
        packs = {
            'AvaCoin1': {'gld': 144, 'coin': 1200},
            'AvaCoin2': {'gld': 288, 'coin': 2500},
            'AvaCoin3': {'gld': 1320, 'coin': 12000},
            'AvaCoin4': {'gld': 2700, 'coin': 25000}}
        res = await Location(self.server, client).gen_plr()
        if msg['data']['pk'] not in packs or \
                res['res']['gld'] < packs[msg['data']['pk']]['gld']: return
        await self.server.redis.set(f"uid:{client.uid}:gld",
                res['res']['gld'] - packs[msg['data']['pk']]['gld'])
        await self.server.add_item(client.uid, 'AvaCoin', 'lt', packs[msg['data']['pk']]['coin'])
        await Location(self.server, client).ntf_res()
        inv = await Location(self.server, client)._get_inventory()
        await client.send({'data': {'inv': inv}, 'command': 'ntf.inv'})
        return await client.send({'broadcast': False, 'text': f"Хэй, {packs[msg['data']['pk']]['coin']} коинов уже у тебя на счету!"}, type_=36)

    async def buy_silver(self, msg, client):
        resurse = await Location(self.server, client).gen_plr()
        if resurse['res']['gld'] < msg['data']['gld']: return
        await self.server.redis.set(f"uid:{client.uid}:gld",
                    resurse['res']['gld'] - msg['data']['gld'])
        await self.server.redis.set(f"uid:{client.uid}:slvr",
                    resurse['res']['slvr'] + msg['data']['gld'] * 100)
        await Location(self.server, client).ntf_res()
        return await client.send({'data': {
            'slvr': resurse['res']['slvr'] + msg['data']['gld'] * 100,
            'inslv': msg['data']['gld'] * 100
            }, 'command': 'b.inslv'
        }, type_=34)

    async def buy_energy(self, msg, client):
        packs = {
            'energy': {'enrg': 100, 'gld': 3},
            'energy2': {'enrg': 480, 'gld': 14},
            'energy3': {'enrg': 1555, 'gld': 45},
            'energy4': {'enrg': 4800, 'gld': 135}
        }
        res = await Location(self.server, client).gen_plr()
        if msg['data']['pk'] not in packs or \
                res['res']['gld'] < packs[msg['data']['pk']]['gld']: return
        await self.server.redis.set(f'uid:{client.uid}:gld',
                    res['res']['gld'] - packs[msg['data']['pk']]['gld'])
        await self.server.redis.set(f'uid:{client.uid}:enrg',
                    res['res']['enrg'] + packs[msg['data']['pk']]['enrg'])
        await Location(self.server, client).ntf_res()
        return await client.send({'broadcast': False, 'text': f"Вы получили {packs[msg['data']['pk']]['enrg']} энергии."}, type_=36)

    async def buy_gold(self, msg, client):
        packs = {'pack1': 160,
                'pack2': 350,
                'pack3': 800,
                'pack4': 2700,}
        if msg['data']['pk'] not in packs: return
        resurse = await Location(self.server, client).gen_plr()
        await self.server.redis.set(f"uid:{client.uid}:gld",
                    resurse['res']['gld'] + packs[msg['data']['pk']])
        await Location(self.server, client).ntf_res()
        return await client.send({'broadcast': False, 'text': f"На ваш счёт поступило {packs[msg['data']['pk']]} золотых монет."}, type_=36)
