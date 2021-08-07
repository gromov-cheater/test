import time

class Location:
    def __init__(self, server, client):
        self.client = client
        self.server = server

    async def _get_inventory(self):
        self.inv = {"c": {"frn": {"id": "frn", "it": []},
                          "act": {"id": "act", "it": []},
                          "gm": {"id": "gm", "it": []},
                          "lt": {"id": "lt", "it": []},
                          "cls": {"id": "cls", "it": []}}}
        ctp = await self.server.redis.get(f"uid:{self.client.uid}:wearing")
        wearing = await self.server.redis.smembers(f"uid:{self.client.uid}:{ctp}")
        keys = []
        pipe = self.server.redis.pipeline()
        for item in await self.server.redis.smembers(f"uid:{self.client.uid}:items"):
            if item in wearing:
                continue
            pipe.lrange(f"uid:{self.client.uid}:items:{item}", 0, -1)
            keys.append(item)
        items = await pipe.execute()
        for i in range(len(keys)):
            name = keys[i]
            item = items[i]
            if not item:
                continue
            try:
                self.inv["c"][item[0]]["it"].append({"c": int(item[1]),
                                                         "iid": "",
                                                         "tid": name}
                                                        )
            except:
                r = self.server.redis
                await r.srem(f"uid:{self.client.uid}:items", name)
                await r.delete(f"uid:{self.client.uid}:items:{name}")
        return self.inv

    async def ntf_ci(self):
        plr = await self.gen_plr()
        return await self.client.send({'data': {'ci': plr['ci']}, 'command': 'ntf.ci'})

    async def get_clothes(self, uid, type_):
        clothes = []
        cur_ctp = await self.server.redis.get(f"uid:{uid}:wearing")
        for item in await self.server.redis.smembers(f"uid:{uid}:{cur_ctp}"):
            clothes.append({"id": item, "clid": ""})
        if type_ == 1:
            ctps = ["casual", "club", "official", "swimwear", "underdress"]
            clths = {"cc": cur_ctp, "ccltns": {}}
            clths["ccltns"][cur_ctp] = {"cct": [], "cn": "", "ctp": cur_ctp}
            for item in clothes:
                clths["ccltns"][cur_ctp]["cct"].append(item["id"])
            ctps.remove(cur_ctp)
            for ctp in ctps:
                clths["ccltns"][ctp] = {"cct": [], "cn": "", "ctp": ctp}
                clothes = []
                for item in await self.server.redis.smembers(f"uid:{uid}:{ctp}"):
                    clothes.append({"id": item, "clid": ""})
                for item in clothes:
                    clths["ccltns"][ctp]["cct"].append(item["id"])
        elif type_ == 2:
            clths = {"clths": []}
            for item in clothes:
                clths["clths"].append({"tpid": item["id"]})
        elif type_ == 3:
            clths = {"cct": [], "cn": "", "ctp": cur_ctp}
            for item in clothes:
                clths["cct"].append(item["id"])
        return clths

    async def change_wearing(self, cloth, wearing):
        redis = self.server.redis
        ctp = await redis.get(f"uid:{self.client.uid}:wearing")
        if wearing:
            await redis.sadd(f"uid:{self.client.uid}:{ctp}", cloth)
        else:
            weared = await redis.smembers(f"uid:{self.client.uid}:{ctp}")
            if cloth not in weared:
                return
            await redis.srem(f"uid:{self.client.uid}:{ctp}", cloth)

    async def refresh_avatar(self):
        plr = await self.gen_plr()
        clths = await self.get_clothes(self.client.uid, type_=2)
        apprnc = await self.server.get_appearance(self.client.uid)
        prefix = 'h' if self.client.zoneId == 'house' else 'o'
        for uid in self.server.online:
            tmp = self.server.online[uid]
            if tmp.room == self.client.room:
                await tmp.send({
                    'data': {'plr': {'uid': self.client.uid,
                             'locinfo': plr['locinfo'],
                             'apprnc': apprnc, 'clths': clths,
                             'ci': plr['ci'], 'usrinf': plr['usrinf']
                        }},
                    'command': f'{prefix}.r.ra'
                })

    async def ntf_res(self):
        gold = await self.server.redis.get(f"uid:{self.client.uid}:gld")
        slvr = await self.server.redis.get(f"uid:{self.client.uid}:slvr")
        enrg = await self.server.redis.get(f"uid:{self.client.uid}:enrg")
        emd = await self.server.redis.get(f"uid:{self.client.uid}:emd")

        res = {
            'gld': gold,
            'slvr': slvr,
            'enrg': enrg,
            'emd': emd
        }

        return await self.client.send({
            'data': {'res': res},
            'command': 'ntf.res'
        })

    async def gen_plr(self, uid=None):
        ci = {}

        if uid is None:
            uid = self.client.uid
        else:
            if uid in self.server.online:
                self.client = self.server.online[uid]

        emd = await self.server.redis.get(f"uid:{uid}:emd")
        gold = await self.server.redis.get(f"uid:{uid}:gld")
        slvr = await self.server.redis.get(f"uid:{uid}:slvr")
        enrg = await self.server.redis.get(f"uid:{uid}:enrg")
        eml = await self.server.redis.get(f"uid:{uid}:eml")
        fak = await self.server.redis.get(f"uid:{uid}:fak")
        tts = await self.server.redis.get(f"uid:{uid}:tts")
        ckid = await self.server.redis.get(f"uid:{uid}:ckid")
        ldrt = await self.server.redis.get(f"uid:{uid}:ldrt")
        dr = await self.server.redis.get(f"uid:{uid}:dr")
        premium = await self.server.redis.get(f"uid:{uid}:premium")
        ceid = await self.server.redis.get(f"uid:{uid}:ceid")
        crt = await self.server.redis.get(f"uid:{uid}:crt")
        exp = await self.server.redis.get(f"uid:{uid}:exp")
        cmid = await self.server.redis.get(f"uid:{uid}:cmid")
        hrt = await self.server.redis.get(f"uid:{uid}:hrt")
        rl = await self.server.redis.get(f"uid:{uid}:rl")

        if not ldrt:
            ldrt = 0
        if not dr:
            dr = True
        else:
            dr = False
        if not premium:
            vexp = 0
            fexp = 0
            vip = False
        else:
            vexp = int(premium)
            fexp = int(premium)
            vip = True
        if not ceid:
            ceid = 0
        if not crt:
            crt = 0
        if not exp:
            exp = 0
        if not cmid:
            cmid = 0
        if not hrt:
            hrt = 0
        if not rl:
            rl = 0

        ci['usrinf'] = {
                'gdr': 1, 'lng': 'default',
                'lcl': 'RU', 'rl': int(rl), 'al': 2,
                'sid': uid
        }
        ci['res'] = {
                'slvr': int(slvr),
                'gld': int(gold),
                'enrg': int(enrg),
                'emd': int(emd)
        }
        ci['locinfo'] = {
                "st": self.client.state, "s": "127.0.0.1",
                "at": self.client.action_tag, "d": self.client.direction,
                "x": self.client.position[0], "y": self.client.position[1],
                "pl":  self.client.room, "l":  self.client.room #"shlc": True,
        }
        ci['ci'] = {
              'eml': eml, 'ldrt': ldrt, 'dr': dr, 'vexp': int(vexp),
              'fak': fak, 'ceid': int(ceid), 'fexp': int(fexp), 'lgt': int(time.time()), 'ys': 0,
              'exp': int(exp), 'vret': 0, 'vip': vip, 'crt': int(crt), 'drli': 1, 'gdc': 0,
              'ldc': 19, 'cmid': int(cmid), 'hrt': int(hrt), 'ckid': ckid, 'shcr': True, 'spp': 0,
              'tts': tts, 'ysct': 0, 'llt': 0, 'vfgc': 3, 'drlp': 4
          }
        return ci
