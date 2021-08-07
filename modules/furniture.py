import const
from location import Location
from modules.base_module import Module

class_name = "Furniture"

class Furniture(Module):
    prefix = 'frn'
    def __init__(self, server):
        self.server = server
        self.commands = {'save': self.save_layout, 'buy': self.buy_furniture,
                         'rnmrm': self.rename_room}

    async def rename_room(self, msg, client):
        rooms = await self.server.redis.smembers(
                        f'rooms:{client.uid}')
        if msg['data']['id'] not in rooms or\
                len(msg['data']['nm'].strip()) > const.MAX_ROOM_NAME:
            return
        await self.server.redis.lset(f"rooms:{client.uid}:{msg['data']['id']}",
                                      0, msg['data']['nm'].strip())

    async def buy_furniture(self, msg, client):
        if msg['data']['tpid'] not in self.server.furniture:
            return
        gold, silver = (
            self.server.furniture[msg['data']['tpid']]['gold'],
            self.server.furniture[msg['data']['tpid']]['silver'])
        resurse = await Location(self.server, client).gen_plr()
        if resurse['res']['gld'] < gold or resurse['res']['slvr'] < silver:
            return
        if 'canBuy' in self.server.furniture[msg['data']['tpid']]:
            if self.server.furniture[msg['data']['tpid']]['canBuy'] == 0:
                return
        slot = 'frn'
        if 'slot' in self.server.furniture[msg['data']['tpid']]:
            if self.server.furniture[msg['data']['tpid']]['slot'] == 'present':
                slot = 'gm'
        await self.server.redis.set(f"uid:{client.uid}:gld", resurse['res']['gld'] - gold)
        await self.server.redis.set(f"uid:{client.uid}:slvr", resurse['res']['slvr'] - silver)
        await self.server.add_item(client.uid, msg['data']['tpid'], slot)
        await Location(self.server, client).ntf_res()
        inv = await Location(self.server, client)._get_inventory()
        return await client.send({'data': {'inv': inv}, 'command': 'ntf.inv'})

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

    async def save_layout(self, msg, client):
        if msg['roomId'].split("_")[1] != client.uid:
            return
        for item in msg['data']['f']:
            type_ = item['t']
            if type_ == 0:
                scs = False
                for tm in ['decor', 'paint', 'lamp', 'mirror', 'shelf']:
                    if tm in item['tpid']:
                        scs = True
                if not scs:
                    if 'aq' in item['tpid'].lower():
                        await self.add_aquarium(item, msg['roomId'].split("_"), client.uid, client)
                        scs = True
                    if not scs:
                        await self.type_add(item, msg['roomId'].split("_"), client.uid, client)
                else:
                    await self.server.take_item(item["tpid"], client.uid)
            elif type_ == 1:
                code = await self.type_update(item, msg['roomId'].split("_"), client.uid)
                if not code:
                    return await self.server.errors(type_=1, client=client)
            elif type_ == 2:
                await self.type_remove(item, msg['roomId'].split("_"), client.uid)
            elif type_ == 3:
                await self.type_replace_door(item, msg['roomId'].split("_"), client.uid)
        await self.check_house_rating(client.uid)
        plr = await Location(self.server, client).gen_plr()
        rooms = await self.server.rooms._get_rooms(client.uid)
        for room in rooms['r']:
            if room['id'] == client.room.split("_")[-1]:
                room_items = room
                break
        inv = await Location(self.server, client)._get_inventory()
        await client.send({
            'data': {'inv': inv},
            'command': 'ntf.inv'
        })
        return await client.send({
            'data': {'ci': plr['ci'], 'hs': room_items},
            'command': 'frn.save'
        })

    async def type_replace_door(self, item, room, uid):
        redis = self.server.redis
        items = await redis.smembers(f"rooms:{uid}:{room[2]}:items")
        found = None
        for tmp in items:
            oid = int(tmp.split("_")[1])
            if oid == item["oid"]:
                found = tmp
                break
        if not found:
            return
        await self.server.take_item(item["tpid"], uid)
        data = await redis.lrange(f"rooms:{uid}:{room[2]}:items:{found}",
                                  0, -1)
        options = await redis.smembers(f"rooms:{uid}:{room[2]}:items:{found}:"
                                       "options")
        if "rid" in options:
            rid = await redis.get(f"rooms:{uid}:{room[2]}:items:{found}:rid")
        else:
            rid = None
        await self.del_item(found, room[2], uid)
        await self.server.add_item(uid, found.split("_")[0], "frn")
        if "oid" in item:
            item['lid'] = item['oid']
            del item['oid']
        item.update({"x": float(data[0]), "y": float(data[1]),
                     "z": float(data[2]), "d": int(data[3]),
                     "rid": rid})
        await self.add_item(item, room[2], uid)

    async def check_house_rating(self, uid):
        rating = 0
        for room in await self.server.redis.smembers(f"rooms:{uid}"):
            for item in await self.server.redis.smembers(f"rooms:{uid}:{room}:items"):
                item = self.get_furniture(item)
                if item in self.server.furniture:
                    if 'rating' in self.server.furniture[item]:
                        rating += int(self.server.furniture[item]['rating'])
        await self.server.redis.set(f'uid:{uid}:hrt', rating)

    async def type_remove(self, item, room, uid):
        redis = self.server.redis
        items = await redis.smembers(f"rooms:{uid}:{room[2]}:items")
        name = f"{item['tpid']}_{item['oid']}"
        if name not in items:
            return
        if uid in self.server.online:
            client = self.server.online[uid]
        await self.del_item(name, room[2], uid)
        slot = 'frn'
        if 'slot' in self.server.furniture[item["tpid"]]:
            if self.server.furniture[item["tpid"]]['slot'] == 'present':
                slot = 'gm'
        await self.server.add_item(uid, item["tpid"], slot)

    def get_furniture(self, frn):
        el = 0
        item = ""
        if item not in self.server.furniture:
            while item not in self.server.furniture:
                if el > 100:
                    return 'error'
                if not item:
                    item = frn.split("_")[el]
                    el += 1
                    continue
                try:
                    item += "_" + frn.split("_")[el]
                    el += 1
                except Exception as e:
                    return self.get_furniture(frn)
        return item

    async def add_aquarium(self, item, room, uid, client):
        redis = self.server.redis
        await self.server.take_item(item["tpid"], uid)
        type_ = ""
        for wall in ['wll', 'wall']:
            if wall in item["tpid"].lower():
                type_ = 'wall'
                break
        for floor in ["flr", "floor"]:
            if floor in item["tpid"].lower():
                type_ = 'floor'
                break
        if not type_:
            return False
        if 'oid' in item:
            item['lid'] = item['oid']
            del item['oid']
        item["x"] = 0.0
        item["y"] = 0.0
        item["z"] = 0.0
        item["d"] = 3
        return await self.add_item(item, room[2], uid)

    async def type_add(self, item, room, uid, client):
        redis = self.server.redis
        await self.server.take_item(item["tpid"], uid)
        items = await redis.smembers(f"rooms:{uid}:{room[2]}:items")
        if any(ext in item["tpid"].lower() for ext in ["wll", "wall"]):
            walls = []
            for wall in ["wall", "wll"]:
                for room_item in items:
                    if wall in room_item.lower():
                        await self.del_item(room_item, room[2], uid)
                        tmp = self.get_furniture(room_item)
                        if tmp == 'error':
                            return self.server.errors(type_=2, client=client)
                        if tmp not in walls:
                            walls.append(tmp)
                            await self.server.add_item(uid, tmp, "frn")
            if 'oid' in item:
                item['lid'] = item['oid']
                del item['oid']
            item["x"] = 0.0
            item["y"] = 0.0
            item["z"] = 0.0
            item["d"] = 3
            await self.add_item(item, room[2], uid)
            item["x"] = 13.0
            item["d"] = 5
            if 'lid' in item:
                item["lid"] += 1
            await self.add_item(item, room[2], uid)
        elif any(ext in item["tpid"].lower() for ext in ["flr", "floor"]):
            for floor in ["flr", "floor"]:
                for room_item in items:
                    if floor in room_item.lower():
                        await self.del_item(room_item, room[2], uid)
                        tmp = self.get_furniture(room_item)
                        if tmp == 'error':
                            return self.server.errors(type_=2, client=client)
                        await self.server.add_item(uid, tmp, "frn")
            item["x"] = 0.0
            item["y"] = 0.0
            item["z"] = 0.0
            item["d"] = 5
            if 'oid' in item:
                item['lid'] = item['oid']
                del item['oid']
            await self.add_item(item, room[2], uid)

    async def del_item(self, item, room, uid):
        redis = self.server.redis
        items = await redis.smembers(f"rooms:{uid}:{room}:items")
        if item not in items:
            return
        options = await redis.smembers(f"rooms:{uid}:{room}:items:{item}"
                                       ":options")
        for op in options:
            await redis.delete(f"rooms:{uid}:{room}:items:{item}:{op}")
        await redis.delete(f"rooms:{uid}:{room}:items:{item}:options")
        await redis.srem(f"rooms:{uid}:{room}:items", item)
        await redis.delete(f"rooms:{uid}:{room}:items:{item}")

    async def type_update(self, item, room, uid):
        redis = self.server.redis
        items = await redis.smembers(f"rooms:{uid}:{room[2]}:items")
        if len(items) >= 70:
            prem = await redis.get(f"uid:{uid}:premium")
            if not prem:
                return False
            elif len(items) >= 120:
                return False
        name = f"{item['tpid']}_{item['oid']}"
        if name in items:
            await self.update_pos_and_params(name, room[2], uid, item)
        else:
            if 'oid' in item:
                item['lid'] = item['oid']
                del item['oid']
            await self.add_item(item, room[2], uid)
        return 1

    async def update_pos_and_params(self, name, room, uid, new_item):
        redis = self.server.redis
        await redis.delete(f"rooms:{uid}:{room}:items:{name}")
        await redis.rpush(f"rooms:{uid}:{room}:items:{name}",
                          new_item["x"], new_item["y"], new_item["z"],
                          new_item["d"])
