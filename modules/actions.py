from location import Location
from modules.base_module import Module

class_name = "Actions"

class Actions(Module):
    prefix = 'action'

    def __init__(self, server):
        self.server = server
        self.halle = {'hallTipLow': {'gld': 0, 'slvr': 250},
                      'hallTipMedium': {'gld': 1, 'slvr': 0},
                      'hallTipHigh': {'gld': 3, 'slvr': 0}}
        self.actions = ["ks", "hg", "gf",
                        "k", "sl", "lks",
                        "hs", "aks"]

    async def avatar_actions(self, msg, client):
        subcommand = msg['command'].split(".")[-1]
        if subcommand in ['m', 'u', 'ca', 'sa'] + self.actions:
            if subcommand == 'ca':
                msg['data']['uid'] = client.uid
                if msg['data']['at'] in self.halle:
                    res = await Location(self.server, client).gen_plr()
                    if res['res']['gld'] >= self.halle[msg['data']['at']]['gld'] or\
                            res['res']['slvr'] >= self.halle[msg['data']['at']]['slvr']:
                        await self.server.redis.set(f'uid:{client.uid}:gld',
                                res['res']['gld'] - self.halle[msg['data']['at']]['gld'])
                        await self.server.redis.set(f'uid:{client.uid}:slvr',
                                res['res']['slvr'] - self.halle[msg['data']['at']]['slvr'])
                        await Location(self.server, client).ntf_res()
            elif subcommand == 'sa':
                if 'at' in msg['data']:
                    if 'dpck' in msg['data']['at']:
                        ckid = msg['data']['at'].split("_")[1]
                        uid = msg['data']['at'].split(":")[1].split("_")[0]
                        await self.server.redis.set(f"uid:{uid}:ckid", ckid)
                        try:
                            tmp = self.server.online[uid]
                            await Location(self.server, tmp).ntf_ci()
                        except Exception as e:
                            if uid in self.server.online:
                                del self.server.online[uid]
                            return
                    elif 'wsfc' in msg['data']['at']:
                        if await self.server.redis.get(f"uid:{client.uid}:ckid"):
                            await self.server.redis.delete(f"uid:{client.uid}:ckid")
                del msg['data']['tmid']
                msg['data']['uid'] = client.uid
            elif subcommand == 'u':
                if 'at' in msg['data']:
                    if msg['data']['at'] in ['dance', 'crying', 'angry']:
                        res = await Location(self.server, client).gen_plr()
                        if res['res']['enrg'] < 5: return
                        await self.server.redis.set(f"uid:{client.uid}:enrg",
                                                        res['res']['enrg'] - 5)
                        await Location(self.server, client).ntf_res()
            elif subcommand in self.actions:
                res = await Location(self.server, client).gen_plr()
                if res['res']['enrg'] < 10: return
                await self.server.redis.set(f"uid:{client.uid}:enrg",
                                                    res['res']['enrg'] - 10)
                await Location(self.server, client).ntf_res()
            for uid in self.server.online:
                tmp = self.server.online[uid]
                if 'at' in msg['data']:
                    if msg['data']['at']:
                        client.action_tag = msg['data']['at']
                else:
                    client.action_tag = None
                if 'st' in msg['data']:
                    client.state = msg['data']['st']
                else:
                    client.state = 0
                position = ""
                positions = {'one': 'x',
                             'two': 'sx'}
                position = "one" if positions["one"] in \
                                    msg['data'] else "two"
                if position == 'one':
                    client.position = (msg['data']['x'],
                                       msg['data']['y'])
                    if 'd' in msg['data']:
                        client.direction = msg['data']['d']
                elif position == 'two':
                    client.position = (msg['data']['sx'],
                                       msg['data']['sy'])
                    if 'dx' in msg['data']:
                        client.direction = msg['data']['dx']
                if tmp.room == client.room:
                    await tmp.send(msg)
