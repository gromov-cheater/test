import random, const
from location import Location
from modules.base_module import Module

class_name = "Avatar"

def get_exp(lvl):
    expSum = 0
    i = 0
    while i < lvl-1:
        i += 1
        expSum += i * 50
    return expSum

class Avatar(Module):
    prefix = 'a'
    def __init__(self, server):
        self.server = server
        self.commands = {'apprnc': self.appearance, "clths": self.clothes}

    async def appearance(self, msg, client):
        subcommand = msg['command'].split(".")[-1]
        if subcommand == 'chn':
            return await client.send({
                'data': {'unm': msg['data']['unm'].strip()},
                'command': 'a.apprnc.rnn'
            })
        elif subcommand == 'rnn':
            res = await Location(self.server, client).gen_plr()
            if res['res']['gld'] < const.PRICE_RENAME or \
                    len(msg['data']['unm'].strip()) > const.NAME_MAX_LENGTH or \
                    len(msg['data']['unm'].strip()) < const.NAME_MIN_LENGHT: 
					return
            await self.server.redis.lset(f"uid:{client.uid}:appearance",
                                         0, msg['data']['unm'].strip())
            await self.server.redis.set(
                    f"uid:{client.uid}:gld",
                    res['res']['gld'] - const.PRICE_RENAME)
            await Location(self.server, client).ntf_res()
            await Location(self.server, client).refresh_avatar()
            return await client.send({
                'data': {'unm': msg['data']['unm'].strip()},
                'command': 'a.apprnc.rnn'})
        elif subcommand == 'save':
            apprnc = msg['data']['apprnc']
            for attr in ['et', 'ht', 'brt', 'mt']:
                if apprnc[attr] == 0: return
            current_apprnc = await self.server.get_appearance(client.uid)
            if not current_apprnc:
                await self.create_avatar(client)
                await self.update_appearance(apprnc, client)
                await self.server.redis.set(f"uid:{client.uid}:wearing",
                                            "casual")
                if apprnc["g"] == 1:
                    weared = ["boyShoes8", "boyPants10", "boyShirt14"]
                    available = ["boyUnderdress1"]
                else:
                    weared = ["girlShoes14", "girlPants9", "girlShirt12"]
                    available = ["girlUnderdress1", "girlUnderdress2"]
                for item in weared+available:
                    if item in weared:
                        await self.change_crt(item, client.uid)
                        await Location(self.server, client).change_wearing(item, True)
                    await self.server.add_item(client.uid, item, "cls")
                for wear in const.wearing:
                    await self.server.redis.set(f"uid:{client.uid}:wearing", wear)
                    for item in available:
                        await Location(self.server, client).change_wearing(item, True)
                await self.server.redis.set(f"uid:{client.uid}:wearing",
                                            "casual")
            else:
                if apprnc['g'] != current_apprnc['g']: return
                await self.update_appearance(apprnc, client)
            apprnc = await self.server.get_appearance(client.uid)
            return await client.send({
                'data': {'apprnc': apprnc},
                'command': 'a.apprnc.save'})

    async def change_crt(self, item, uid):
        rating = 0
        try:
            ratings = int(await self.server.redis.get(f"uid:{uid}:crt"))
        except Exception:
            ratings = 0
        apprnc = await self.server.get_appearance(uid)
        gender = "boy" if apprnc["g"] == 1 else "girl"
        if item in self.server.clothes[gender]:
            if 'rating' in self.server.clothes[gender][item]:
                rating = int(self.server.clothes[gender][item]['rating'])
        await self.server.redis.set(f"uid:{uid}:crt", ratings + rating)

    async def clothes(self, msg, client):
        subcommand = msg['command'].split(".")[-1]
        if subcommand == 'wear':
            return await self.wear_cloth(msg, client)
        elif subcommand == 'buy':
            clothes = [{"tpid": msg['data']["tpid"], "clid": ""}]
            await self.buy_clothes(msg['command'], clothes, msg['data']["ctp"], client)
            await Location(self.server, client).ntf_res()
            return await Location(self.server, client).refresh_avatar()
        else: return print(msg['command'])

    async def buy_clothes(self, command, clothes, ctp, client):
        gold, silver, rating, to_buy = 0, 0, 0, []
        items = await self.server.redis.smembers(f"uid:{client.uid}:items")
        gender = "boy" if await self.server.get_appearance(client.uid))["g"] == 1 else "girl"
        resurse = await Location(self.server, client).gen_plr()
        for item in clothes:
            cloth, clid = item["tpid"], item["clid"]
            clid = item["clid"]
            name = f"{cloth}_{clid}" if clid else cloth
            if name and name not in self.server.clothes[gender] or \
                        'canBuy' in self.server.clothes[gender][name] or \
                        'vipOnly' in self.server.clothes[gender][name]:
                if 'canBuy' in self.server.clothes[gender][name]:
                    if int(self.server.clothes[gender][name]['canBuy']) != 1: return
                elif 'vipOnly' in self.server.clothes[gender][name]:
                    if int(self.server.clothes[gender][name]['vipOnly']) == 1:
                        if not await self.server.redis.get(f"uid:{client.uid}:premium"): return
                return
            for res in ['gold', 'silver', 'rating']:
                if res in self.server.clothes[gender][name]:
                    if res == 'gold': gold += int(self.server.clothes[gender][name][res])
                    elif res == 'silver': silver += int(self.server.clothes[gender][name][res])
                    elif res == 'rating': rating += int(self.server.clothes[gender][name][res])
            to_buy.append(name)
        if not to_buy or resurse['res']['gld'] < gold or\
                resurse['res']['slvr'] < silver: return
        await self.change_ctp(client.uid, ctp)
        await self.server.redis.set(f"uid:{client.uid}:gld", resurse['res']['gld'] - gold)
        await self.server.redis.set(f"uid:{client.uid}:slvr", resurse['res']['slvr'] - silver)
        for item in to_buy:
            await self.change_crt(item, client.uid)
            await self.server.add_item(client.uid, item, "cls")
            await Location(self.server, client).change_wearing(item, True)
        crt = await self.server.redis.get(f"uid:{client.uid}:crt")
        inv = await Location(self.server, client)._get_inventory()
        clths = await Location(self.server, client).get_clothes(client.uid, type_=2)
        ccltn = await Location(self.server, client).get_clothes(client.uid, type_=3)
        return await client.send({
            'data': {'inv': inv, 'clths': clths, 'ccltn': ccltn, 'crt': crt},
            'command': command})

    async def change_ctp(self, uid, new_ctp):
        ctp = await self.server.redis.get(f"uid:{uid}:wearing")
        if ctp == new_ctp: return
        await self.server.redis.set(f"uid:{uid}:wearing", new_ctp)

    async def wear_cloth(self, msg, client):
        ctp = msg['data']['ctp']
        if ctp not in ["casual", "club", "official",
                       "swimwear", "underdress"]: return
        await self.change_ctp(client.uid, ctp)
        wearing = await self.server.redis.smembers(f"uid:{client.uid}:{ctp}")
        for cloth in wearing:
            await Location(self.server, client).change_wearing(cloth, False)
        clths = msg['data']["clths"]
        for cloth in clths:
            await Location(self.server, client).change_wearing(f"{cloth['tpid']}_{cloth['clid']}" if "clid" in cloth else cloth["tpid"], True)
        inv = await Location(self.server, client)._get_inventory()
        clths = await Location(self.server, client).get_clothes(client.uid, type_=2)
        ccltn = await Location(self.server, client).get_clothes(client.uid, type_=3)
        return await client.send({
            'data': {'inv': inv, 'clths': clths, 'ccltn': ccltn},
            'command': 'a.clths.wear'})

    async def create_avatar(self, client):
        level = random.randint(10, 69)
        await self.server.redis.set(f"uid:{client.uid}:emd", 0)
        await self.server.redis.set(f"uid:{client.uid}:gld", 7)
        await self.server.redis.set(f"uid:{client.uid}:slvr", 10000)
        await self.server.redis.set(f"uid:{client.uid}:enrg", 100)
        await self.server.redis.set(f"uid:{client.uid}:hrt", 0*0)
        await self.server.redis.set(f"uid:{client.uid}:exp", get_exp(level))
        await self.server.redis.sadd(f"rooms:{client.uid}", "livingroom")
        await self.server.redis.rpush(f"rooms:{client.uid}:livingroom", "#livingRoom", 1)
        for i in range(1, 6):
            await self.server.redis.sadd(f"rooms:{client.uid}", f"room{i}")
            await self.server.redis.rpush(f"rooms:{client.uid}:room{i}", f"Комната {i}", 2)
        for item in const.room_items:
            await self.add_item(item, "livingroom", client.uid)
            for i in range(1, 6):
                await self.add_item(item, f"room{i}", client.uid)

    async def add_item(self, item, room, uid):
        redis = self.server.redis
        await redis.sadd(f"rooms:{uid}:{room}:items",
                         f"{item['tpid']}_{item['lid']}")
        if "rid" in item:
            await redis.sadd(f"rooms:{uid}:{room}:items:"
                             f"{item['tpid']}_{item['lid']}:options", "rid")
            if item["rid"]:
                await redis.set(f"rooms:{uid}:{room}:items:"
                                f"{item['tpid']}_{item['lid']}:rid",
                                item["rid"])
        await redis.rpush(f"rooms:{uid}:{room}:items:"
                          f"{item['tpid']}_{item['lid']}", item["x"],
                          item["y"], item["z"], item["d"])

    async def update_appearance(self, apprnc, client):
        old = await self.server.get_appearance(client.uid)
        if old:
            nick = old["n"]
        else:
            nick = apprnc["n"]
        await self.server.redis.delete(f"uid:{client.uid}:appearance")
        await self.server.redis.rpush(f"uid:{client.uid}:appearance", nick,
                          apprnc["g"], apprnc["hc"], apprnc["ec"],
                          apprnc["bc"], apprnc["sc"], apprnc["bt"],
                          apprnc["rg"], apprnc["et"], apprnc["brc"],
                          apprnc["ht"], apprnc["sh"], apprnc["ss"],
                          apprnc["mc"], apprnc["brt"], apprnc["rc"],
                          apprnc["shc"], apprnc["mt"])
