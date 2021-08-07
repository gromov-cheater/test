import time, asyncio
from location import Location
from modules.base_module import Module

class_name = "House"

class House(Module):
    prefix = 'h'
    def __init__(self, server):
        self.server = server
        self.commands = {'minfo': self.house_my_info,
                         'gr': self.house_get_room,
                         'r': self.room, 'rtd': self.room_target,
                         'oinfo': self.ovner_info, 'lkhs': self.close_house,
                         'ulkhs': self.open_house}
        self.kickeds = {}
        self.actions = ["ks", "hg", "gf",
                        "k", "sl", "lks",
                        "hs", "aks"]

    async def open_house(self, msg, client):
        if not await self.server.redis.get(f'uid:{client.uid}:house_close'):
            return
        await self.server.redis.delete(f'uid:{client.uid}:house_close')
        return await client.send({
            'data': {},
            'command': 'h.ulkhs'
        })

    async def close_house(self, msg, client):
        prises = {
            1200: {'gold': 0, 'silver': 0},
            3600: {'gold': 0, 'silver': 100},
            43200: {'gold': 1, 'silver': 0}}
        resurse = await Location(self.server, client).gen_plr()
        if msg['data']['lt'] not in prises or \
            resurse['res']['gld'] < prises[msg['data']['lt']]['gold'] or\
                    resurse['res']['slvr'] < prises[msg['data']['lt']]['silver']:
            return
        await self.server.redis.set(f'uid:{client.uid}:house_close',
                                        int(time.time()) + msg['data']['lt'])
        return await client.send({'data': {'lt': msg['data']['lt']}, 'command': 'h.lkhs'})

    async def room_target(self, msg, client):
        return await client.send({'data': {'tm': 1}, 'command': 'h.rtd'})

    async def ovner_info(self, msg, client):
        appearance = await self.server.get_appearance(msg['data']['uid'])
        plr = await Location(self.server, client).gen_plr(msg['data']['uid'])
        rooms = await self.server.rooms._get_rooms(msg['data']['uid'])
        wear = await Location(self.server, client).get_clothes(msg['data']['uid'], type_=1)
        clths = await Location(self.server, client).get_clothes(msg['data']['uid'], type_=2)

        if await self.server.redis.get(f'uid:{msg["data"]["uid"]}:house_close'):
            if msg["data"]["uid"] != client.uid:
                return await client.send({'data': {'l': True}, 'command': 'h.oinfo'})
        elif client.uid in self.kickeds:
            if msg['data']['uid'] in self.kickeds[client.uid]['uids']:
                tm = self.kickeds[client.uid]['uids'][msg['data']['uid']]['tm']
                if tm - int(time.time()) > 0:
                    return await client.send({'data': {'kc': True}, 'command': 'h.oinfo'})
                del self.kickeds[client.uid]['uids'][msg['data']['uid']]
        return await client.send({
            'data': {'ath': False, 'plr': {
                    'uid': msg['data']['uid'],
                    'locinfo': plr['locinfo'],
                    'res': plr['res'], 'apprnc': appearance,
                    'ci': plr['ci'], 'hs': rooms,
                    'onl': True, 'achc': {'ac': {}}, 'cs': wear,
                    'qc': {'q': []}, 'wi': {'wss': []},
                    'clths': clths, 'usrinf': plr['usrinf']
            }, 'hs': rooms},
            'command': 'h.oinfo'})

    async def house_my_info(self, msg, client):
        if msg['data']['onl']:
            return await client.send({
                'data': {'scs': True, 'politic': 'default'},
                'command': 'h.minfo'})
        appearance = await self.server.get_appearance(client.uid)
        if not appearance:
            return await client.send({
                'data': {'has.avtr': False},
                'command': 'h.minfo'})
        plr = await Location(self.server, client).gen_plr()
        inv = await Location(self.server, client)._get_inventory()
        wear = await Location(self.server, client).get_clothes(client.uid, type_=1)
        rooms = await self.server.rooms._get_rooms(client.uid)
        clths = await Location(self.server, client).get_clothes(client.uid, type_=2)
        bklst = await self.server.redis.smembers(f"bklst:{client.uid}")
        return await client.send({
                'data': {'bklst': {'uids': bklst},
                         'politic': 'default',
                         'plr': {'locinfo': plr['locinfo'],
                         'res': plr['res'], 'apprnc': appearance,
                         'ci': plr['ci'], 'hs': rooms,
                         'onl': True, 'achc': {'ac': {}}, 'cs': wear,
                         'inv': inv, 'uid': client.uid, 'qc': {'q': []}, 'wi': {'wss': []},
                         'clths': clths, 'usrinf': plr['usrinf']}, 'tm': 0},
               'command': 'h.minfo'})

    async def room(self, msg, client):
        subcommand = msg['command'].split(".")[-1]
        if subcommand == 'info':
            rmmb, room_items = [], []
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
                        'usrinf': plr['usrinf']})
            rooms = await self.server.rooms._get_rooms(msg['roomId'].split("_")[1])
            for room in rooms['r']:
                if room['id'] == client.room.split("_")[-1]:
                    room_items = room
                    break
            return await client.send({'data': {'rmmb': rmmb, 'rm': room_items, 'it': {}}, 'command': 'h.r.info'})
        elif subcommand == 'kc':
            if client.room != msg['roomId'] and \
                    client.uid != client.room.split("_")[1] or \
                    msg['data']['tmid'] not in self.server.online: return
            tmp = self.server.online[msg['data']['tmid']]
            await self.server.rooms.leave_room(tmp.room, tmp)
            if tmp.uid not in self.kickeds:
                self.kickeds[tmp.uid] = {'uids': {client.uid: {'tm': int(time.time()+10*60)}}}
            else:
                self.kickeds[tmp.uid]['uids'][client.uid] = {'tm': int(time.time()+10*60)}
            return await tmp.send({'data': {}, 'command': 'h.r.kc'})
        elif subcommand in ['m', 'u', 'sa'] + self.actions:
            return await self.server.modules['action'].avatar_actions(msg, client)
        elif subcommand == 'ra':
            return await Location(self.server, client).refresh_avatar()
        elif subcommand == 'rfr':
            roomId = msg['roomId'].split("_")[-1]
            return await self.server.rooms.refresh_room(roomId, client)

    async def house_get_room(self, msg, client):
        room = f"{msg['data']['lid']}_{msg['data']['gid']}_{msg['data']['rid']}"
        await self.server.rooms.join_room(room, client)
        if msg['data']['gid'] == client.uid:
            await client.send({
                    'data': {'ath': True},
                    'command': 'h.oah'})
        return await client.send({
                'data': {'rid': client.room},
                'command': 'h.gr'})
