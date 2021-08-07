from location import Location
from modules.base_module import Module

class_name = "Player"

class Player(Module):
    prefix = 'pl'
    def __init__(self, server):
        self.server = server
        self.commands = {'gid': self.players_by_id, 'flw': self.follow}

    async def players_by_id(self, msg, client):
        players = []
        for uid in msg['data']["uids"]:
            plr = await Location(self.server, client).gen_plr(uid)
            appearance = await self.server.get_appearance(uid)
            clths = await Location(self.server, client).get_clothes(uid, type_=2)
            if not plr:
                continue
            players.append({
                'uid': uid,
                'apprnc': appearance,
                'clths': clths,
                'ci': plr['ci'],
                'usrinf': plr['usrinf']
            })
        return await client.send({
            'data': {'plrs': players, 'clid': msg['data']['clid']},
            'command': 'pl.get'
        })

    async def follow(self, msg, client):
        uid = msg['data']["uid"]
        if uid in self.server.online:
            try:
                user = self.server.online[uid]
            except KeyError:
                return await self.error(client, uid)
            locinfo = {"st": 0, "s": "127.0.0.1", "at": None, "d": 0,
                       "x": -1.0, "y": -1.0, "shlc": True, "pl": user.room,
                       "l": user.room}
        else:
            return await self.error(client, uid)
        return await client.send({'data': {'locinfo': locinfo}, 'command': 'pl.flw'})

    async def error(self, client, uid):
        return await client.send({'data': {'code': 155, 'message': f'code: 155; msg : user with id {uid} is offline.'}, 'command': 'err'})
