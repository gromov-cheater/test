import const, random
from location import Location
from modules.base_module import Module

class_name = "Outside"

class Outside(Module):
    prefix = 'o'
    def __init__(self, server):
        self.server = server
        self.slots = {}
        self.commands = {'gr': self.get_room, 'r': self.room,
                         'bi': self.buy_energy}
        self.zoneBuyEnergy = {'cf': {
                'cfCak': {'gld': 0, 'slvr': 150, 'enrg': 15},
                'cfCof': {'gld': 1, 'slvr': 0, 'enrg': 30},
                'cfPiz': {'gld': 3, 'slvr': 0, 'enrg': 100}
            },
            'cl': {
                'clMoc': {'gld': 0, 'slvr': 150, 'enrg': 15},
                'clBlr': {'gld': 1, 'slvr': 0, 'enrg': 30},
                'clB52': {'gld': 3, 'slvr': 0, 'enrg': 100}
            }
        }
        self.actions = ["ks", "hg", "gf",
                        "k", "sl", "lks",
                        "hs", "aks"]

    async def buy_energy(self, msg, client):
        prefix = msg['data']['tpid'][0:2]
        if prefix not in self.zoneBuyEnergy:
            return
        res = await Location(self.server, client).gen_plr()
        if res['res']['gld'] < self.zoneBuyEnergy[prefix][
                                msg['data']['tpid']]['gld'] or\
            res['res']['slvr'] < self.zoneBuyEnergy[prefix][
                                    msg['data']['tpid']]['slvr'] or\
                msg['data']['tpid'] not in self.zoneBuyEnergy[prefix]:
            return
        await self.server.redis.set(f'uid:{client.uid}:gld',
                res['res']['gld'] - self.zoneBuyEnergy[prefix][
                                        msg['data']['tpid']]['gld'])
        await self.server.redis.set(f'uid:{client.uid}:slvr',
                res['res']['slvr'] - self.zoneBuyEnergy[prefix][
                                        msg['data']['tpid']]['slvr'])
        await self.server.redis.set(f'uid:{client.uid}:enrg',
                res['res']['enrg'] + self.zoneBuyEnergy[prefix][
                                        msg['data']['tpid']]['enrg'])
        return await Location(self.server, client).ntf_res()

    async def get_room(self, msg, client):
        if msg['data']['lid'] not in self.slots:
            self.slots[msg['data']['lid']] = ['1']
        spare_slots = []
        for slot in self.slots[msg['data']['lid']]:
            users = self.get_user_location(msg['data'], slot)
            if users < const.LOCATION_LIMIT:
                spare_slots.append(slot)
        if not spare_slots:
            slot = str(len(self.slots[msg['data']['lid']]) + 1)
            if slot:
                spare_slots.append(slot)
                self.slots[msg['data']['lid']].append(slot)
        room = f"{msg['data']['lid']}_{msg['data']['gid']}_{random.choice(spare_slots)}"

        await self.server.rooms.join_room(room, client)

        client.step_to_activate = True
        client.position = (msg['data']['dx'],
                           msg['data']['dy'])

        return await client.send({'data': {'rid': client.room}, 'command': 'o.gr'})

    async def room(self, msg, client):
        subcommand = msg['command'].split(".")[-1]
        if subcommand == 'info':
            rmmb = []
            room_items = []
            for uid in self.server.online:
                tmp = self.server.online[uid]
                if tmp.room == client.room:
                    appearance = await self.server.get_appearance(tmp.uid)
                    plr = await Location(self.server, client).gen_plr(tmp.uid)
                    clths = await Location(self.server, client).get_clothes(tmp.uid, type_=2)
                    rmmb.append({
                        'uid': tmp.uid,
                        'locinfo': plr['locinfo'],
                        'apprnc': appearance,
                        'clths': clths, 'ci': plr['ci'],
                        'usrinf': plr['usrinf']
                    })
            return await client.send({'data': {'rmmb': rmmb}, 'command': 'o.r.info'})
        elif subcommand in ['m', 'u', 'ca', 'sa'] + self.actions:
            return await self.server.modules['action'].avatar_actions(msg, client)
        elif subcommand == 'ra':
            return await Location(self.server, client).refresh_avatar()

    def get_user_location(self, data, roomId):
        users = 0
        location = f"{data['lid']}_{data['gid']}_{roomId}"
        for uid in self.server.online:
            tmp = self.server.online[uid]
            if tmp.room == location:
                users += 1
        return users
