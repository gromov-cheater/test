import subprocess
import base64
import const
import random
import importlib
import time, aioredis
from client import Client
from index.main import Web
from modules.room import Room
from location import Location
from datetime import datetime
from xml_parser import Parser
import asyncio, struct, binascii
from string import ascii_letters as string
from protocol.get_mobile_address import MobileToken

def get_exp(lvl):
    expSum = 0
    i = 0
    while i < lvl-1:
        i += 1
        expSum += i * 50
    return expSum

modules = ['relations', 'mail', 'house', 'avatar',
           'furniture', 'user_rating', 'player',
           'billing', 'passport', 'outside',
           'actions', 'craft', 'work', 'inventory',
           'event', 'confirm', 'vip', 'shop']

class Server:
    def __init__(self):
        self.online = {}
        self.modules = {}
        self.parser = Parser()
        self.rooms = Room(self)
        for item in modules:
            module = importlib.import_module(f"modules.{item}")
            class_ = getattr(module, module.class_name)
            self.modules[class_.prefix] = class_(self)
        self.clothes = self.parser.parse_clothes()
        self.furniture = self.parser.parse_furniture()
        self.game_items = self.parser.parse_game_items()

    async def open_connections(self):
        self.logging("AvaTropic успешно запущен!")
        self.redis = await aioredis.create_redis_pool(
            "redis://localhost",
            encoding="utf-8"
        )
        self.server = await asyncio.start_server(
            self.new_connection,
            "127.0.0.1", 8123
        )
        asyncio.create_task(self._background())

    async def check_outside_get_room(self, client):
        element = 0
        old_type = client.old_type
        while element < 5:
            if old_type == client.old_type:
                element += 1
            else:
                return False
            await asyncio.sleep(0.5)
        client.old_type = 0
        await client.send({
                'secretKey': None,
                'zoneId': client.zoneId,
                'user': {'roomIds': [],
                         'name': None,
                         'zoneId': client.zoneId,
                         'userId': client.uid},
                'userId': client.uid
        }, type_=1)

    async def process_data(self, msg, client):
        client.old_type = msg['type']
        if msg['type'] == 1:
            if client.uid is None:
                if 'login' not in msg['msg']:
                    return self.logging(f"Ошибка авторизации!")
                return await self.auth(msg['msg'], client)
            return await self.auth(msg['msg'], client)
        elif msg['type'] == 2 or msg['type'] == 17:
            return asyncio.create_task(self.check_outside_get_room(client))
        elif msg['type'] == 32:
            if msg['msg']['text'].startswith('!'):
                await self.chat_command(msg['msg']['text'], client)
                if 'recipients' in msg['msg']:
                    del msg['msg']['recipients']
                msg['msg']['text'] = "Ввёл команду."
            return await self.chat(msg['msg'], client)
        elif msg['type'] == 34:
            prefix = msg['msg']['command'].split(".")[0]
            if prefix not in self.modules:
                return self.logging(f"Command {msg['msg']['command']} not found.")
            if msg['msg']['command'] == 'crt.bcp':
                if 'avacoin' not in msg['msg']['data']['pk'].lower():
                    return await self.modules['b'].buy_gold(msg['msg'], client)
                return await self.modules['b'].buy_coint(msg['msg'], client)
            return await self.modules[prefix].get_message(msg['msg'], client)
        return self.logging(f"Type error: {msg['type']}")

    async def chat_command(self, msg, client):
        subcommand = msg[1:]
        if " " in msg:
            subcommand = msg.split()[0][1:]
        if subcommand == 'ssm':
            return await self.send_system_message(subcommand, msg, client)
        elif subcommand == 'ban':
            return await self.user_ban(subcommand, msg, client)
        elif subcommand == 'lvl':
            return await self.change_avatar_level(subcommand, msg, client)

    async def change_avatar_level(self, subcommand, msg, client):
        level = msg.split(subcommand)[1].strip()
        if not level.isdigit():
            return await self.error(type_=1, client=client)
        premium = await self.redis.get(f"uid:{client.uid}:premium")
        premium = False if not premium else True
        if not premium and int(level) > 69 or int(level) < 10:
            return await self.error(type_=2, client=client)
        elif premium and int(level) > 998 or int(level) < 10:
            level = 998
        await self.redis.set(f"uid:{client.uid}:exp", get_exp(int(level)))
        await Location(self, client).refresh_avatar()
        await Location(self, client).ntf_ci()
        return await client.send({'broadcast': False, 'text': f'Ваш уровень изменился на {level}.'}, type_=36)

    async def error(self, type_=1, client=None):
        message = ""
        if type_ == 1:
            message = "Ошибка в команде"
        elif type_ == 2:
            message = "Вам доступна смена уровня от 10 до 69. Купите премиум."
        return await client.send({'broadcast': False, 'text': message}, type_=36)

    async def user_ban(self, subcommand, msg, client):
        gen_plr = await Location(self, client).gen_plr()
        if gen_plr['usrinf']['rl'] != const.BAN_PRIVILEGIES:
            return
        try:
            uid = msg.split("uid=")[1].split("&")[0]
            reason = msg.split("reason=")[1].split("&")[0]
            minutes = msg.split("minutes=")[1].split("&")[0]
        except IndexError:
            return
        if uid and reason and minutes:
            await self.redis.set(f'uid:{uid}:banned', client.uid)
            await self.redis.set(f'uid:{uid}:reason_ban', reason)
            await self.redis.set(f'uid:{uid}:time_ban', minutes)
            await self.redis.set(f'uid:{uid}:times', int(time.time()))
            await self.redis.set(f'uid:{uid}:left_ban', int(time.time()) + int(minutes) * 60)
        if uid in self.online:
            tmp = self.online[uid]
            await tmp.send({
                'zoneId': tmp.zoneId,
                'error': {'code': 10, 'data': {'duration': int(minutes),
                        'reason': reason, 'banTime': int(time.time()),
                        'reasonId': 4, 'unbanType': 'admin panel',
                        'leftTime': int(time.time()) * 1000, 'userId': tmp.uid,
                        'moderatorId': client.uid},
                'message': 'User is banned'}}, type_=2)
        return await client.send({'broadcast': False, 'text': f"{uid} получил бан"}, type_=36)

    async def send_system_message(self, subcommand, msg, client):
        gen_plr = await Location(self, client).gen_plr()
        if gen_plr['usrinf']['rl'] != const.SEND_SYSTEM_MESSAGE:
            return
        message = msg.split(subcommand)[1].strip()
        for user in self.online:
            tmp = self.online[user]
            await tmp.send({'broadcast': False, 'text': message}, type_=36)

    async def chat(self, msg, client):
        apprnc = await self.get_appearance(client.uid)
        if not apprnc or not apprnc['n']:
            return
        broadcast = True
        if 'recipients' in msg:
            broadcast, uidS = False, msg['recipients'][0]
        for uid in self.online:
            if not broadcast and\
                    uid not in [uidS, client.uid]:
                continue
            tmp = self.online[uid]
            if tmp.room == client.room:
                await tmp.send({'broadcast': broadcast, 'sender': {
                    'roomIds': [client.room], 'name': apprnc['n'],
                    'zoneId': client.zoneId, 'userId': client.uid},
                    'text': msg['text']
                }, type_=32)

    async def technical_working(self, client):
        return await client.send({
                'zoneId': 'house',
                'error': {'code': 10, 'data': {'duration': 120,
                            'reason': "Технические работы.", 'banTime': int(time.time()),
                            'reasonId': 4, 'unbanType': 'admin panel',
                            'leftTime': 0, 'userId': None,
                            'moderatorId': "1"},
                'message': 'User is banned'}}, type_=2)

    async def auth(self, msg, client):
        if not await self.redis.get(f"login:{msg['login']}"):
            uid, password = await self._new_account(msg['login'])
        else:
            uid = await self.redis.get(f"login:{msg['login']}")
            password = await self.redis.get(f"uid:{uid}:password")
        role = await self.redis.get(f'uid:{uid}:rl')
        if const.TECHNICAL_WORKING and not role:
            return await self.technical_working(client)
        if client.uid:
            apprnc = await self.get_appearance(client.uid)
            await client.send({'reason': 2, 'data': {}, 'zoneId': client.zoneId,
                                'user': {'roomIds': [], 'name': apprnc['n'],
                                'userId': client.uid}}, type_=3)
        if not client.uid:
            banned = await self.redis.get(f'uid:{uid}:banned')
            if banned:
                times = await self.redis.get(f'uid:{uid}:times')
                reason = await self.redis.get(f'uid:{uid}:reason_ban')
                time_ban = await self.redis.get(f'uid:{uid}:time_ban')
                left_ban = await self.redis.get(f'uid:{uid}:left_ban')
                if int(time.time()) - int(left_ban) > 0:
                    for banType in ['banned', 'times', 'reason_ban',
                                    'time_ban', 'left_ban']:
                        await self.redis.delete(f'uid:{uid}:{banType}')
                    banned = False
                if banned:
                    return await client.send({
                            'zoneId': msg['zoneId'],
                            'error': {'code': 10, 'data': {'duration': int(time_ban),
                                    'reason': reason, 'banTime': int(times),
                                    'reasonId': 4, 'unbanType': 'admin panel',
                                    'leftTime': int(times) * 1000, 'userId': uid,
                                    'moderatorId': banned},
                            'message': 'User is banned'}}, type_=2)
            if uid in self.online:
                tmp = self.online[uid]
                await tmp.writer.close()
                del self.online[uid]
            client.uid = str(uid)
        if client.uid not in self.online:
            self.online[client.uid] = client
        client.zoneId = msg['zoneId']
        client.step_to_activate = False
        await self.check_new_act(client)
        return await client.send({
                'secretKey': password,
                'zoneId': msg['zoneId'],
                'user': {'roomIds': [],
                         'name': None,
                         'zoneId': msg['zoneId'],
                         'userId': client.uid},
                'userId': client.uid
        }, type_=1)

    async def check_new_act(self, client):
        premium = await self.redis.get(f"uid:{client.uid}:premium")
        if not premium:
            return
        if int(time.time()) - int(premium) > 0:
            self.redis.delete(f"uid:{client.uid}:dr")
            self.redis.delete(f"uid:{client.uid}:premium")

    async def get_appearance(self, uid):
        apprnc = await self.redis.lrange(f"uid:{uid}:appearance", 0, -1)
        if not apprnc:
            return False
        return {"n": apprnc[0], "g": int(apprnc[1]), "hc": int(apprnc[2]),
                "ec": int(apprnc[3]), "bc": int(apprnc[4]),
                "sc": int(apprnc[5]), "bt": int(apprnc[6]),
                "rg": int(apprnc[7]), "et": int(apprnc[8]),
                "brc": int(apprnc[9]), "ht": int(apprnc[10]),
                "sh": int(apprnc[11]), "ss": int(apprnc[12]),
                "mc": int(apprnc[13]), "brt": int(apprnc[14]),
                "rc": int(apprnc[15]), "shc": int(apprnc[16]),
                "mt": int(apprnc[17])}

    async def add_item(self, uid, name, type_, amount=1):
        redis = self.redis
        item = await redis.lrange(f"uid:{uid}:items:{name}", 0, -1)
        if item:
            if type_ == "cls":
                return
            await redis.lset(f"uid:{uid}:items:{name}", 1,
                             int(item[1])+amount)
        else:
            await redis.sadd(f"uid:{uid}:items", name)
            await redis.rpush(f"uid:{uid}:items:{name}", type_, amount)

    async def take_item(self, item, uid, amount=1):
        redis = self.redis
        items = await redis.smembers(f"uid:{uid}:items")
        if item not in items:
            return False
        tmp = await redis.lrange(f"uid:{uid}:items:{item}", 0, -1)
        if not tmp:
            await redis.srem(f"uid:{uid}:items", item)
            return False
        type_ = tmp[0]
        have = int(tmp[1])
        if have < amount:
            return False
        if have > amount:
            await redis.lset(f"uid:{uid}:items:{item}", 1, have - amount)
        else:
            await redis.delete(f"uid:{uid}:items:{item}")
            await redis.srem(f"uid:{uid}:items", item)
        return True

    async def errors(self, type_=0, client=None):
        message = "Произошла какая-то ошибка."
        if type_ == 1:
            message = "Превышен лимит предметов."
        elif type_ == 2:
            message = "Произошла ошибка при поиске мебели."
        return await client.send({'broadcast': False, 'text': message}, type_=36)

    async def _new_account(self, login, pswdlnght=20):
        uid = await self.redis.incr("uids")
        passwd = "".join(random.choice(string) for i in range(pswdlnght))
        await self.redis.set(f"login:{login}", uid)
        await self.redis.set(f"uid:{uid}:login", login)
        await self.redis.set(f"uid:{uid}:password", passwd)
        return uid, passwd

    async def stop(self):
        self.server.close()
        await self.server.wait_closed()

    async def new_connection(self, reader, writer):
        loop = asyncio.get_event_loop()
        loop.create_task(Client(self).listen_server(reader, writer))

    def logging(self, message):
        return print(f"INFO [{time.strftime('%X')}] {message}")

    async def _background(self):
        while True:
            self.logging(f"Игроков онлайн: {len(self.online)}")
            self.logging(f"Игроков зареганых: {await self.redis.get('uids')}")
            await asyncio.sleep(60)
        return self.logging("Произошла ошибка, перезапустите сервер!")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(Web().main())
    loop.create_task(Server().open_connections())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(Server().stop())
    loop.close()
