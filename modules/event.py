import const, time
from modules.base_module import Module

class_name = "Event"

class Event(Module):
    prefix = 'ev'
    def __init__(self, server):
        self.server = server
        self.events = {}
        self.commands = {'get': self.get_events, 'crt': self.event_create,
                        'gse': self.get_self_event, 'cse': self.event_close}

    async def get_events(self, msg, client):
        events_category = msg['data']['c']
        evlst = []
        for uid in self.events:
            event = self.events[uid]
            if int(time.time()) - event['ft'] > 0:
                del self.events[uid]
                continue
            if events_category == -1:
                evlst.append(event)
                continue
            elif event['c'] == events_category:
                evlst.append(event)
        return await client.send({'data': {'c': events_category, 'evlst': evlst}, 'command': 'ev.get'})

    async def event_create(self, msg, client):
        event = msg['data']['ev']
        if client.uid in self.events:
            return await self.errors(type_=3, client=client)
        if not event['ds'].strip() or not event['tt'].strip():
            return await self.errors(type_=1, client=client)
        elif len(event['ds'].strip()) > const.EVENT_DESCRIPTION or \
                len(event['tt'].strip()) > const.EVENT_TITLE:
            return await self.errors(type_=2, client=client)
        apprnc = await self.server.get_appearance(client.uid)
        self.events[client.uid] = {
            'ds': event['ds'].strip(), 'uid': client.uid,
            'tt': event['tt'].strip(), 'c': event['c'], 'ml': event['ml'],
            'id': int(client.uid), 'lg': event['lg'], 'st': int(time.time()),
            'l': event['l'], 'ft': int(time.time()) + event['lg'] * 60,
            'unm': apprnc['n'], 'r': event['r'], 'tp': event['tp']
        }
        return await client.send({'data': {'ev': self.events[client.uid]}, 'command': 'ev.crt'})

    async def get_self_event(self, msg, client):
        if client.uid not in self.events:
            return await client.send({'data': {}, 'command': 'ev.gse'})
        return await client.send({'data': {'ev': self.events[client.uid]}, 'command': 'ev.gse'})

    async def event_close(self, msg, client):
        if client.uid not in self.events:
            return
        del self.events[client.uid]
        return await client.send({'data': {}, 'command': 'ev.cse'})

    async def errors(self, type_=1, client=None):
        message = ""
        if type_ == 1:
            message = 'Пустое описание, или название.'
        elif type_ == 2:
            message = 'Слишком большое описание, или название.'
        elif type_ == 3:
            message = 'Вы уже создали событие, сначала удалите старое.'
        return await client.send({'broadcast': False, 'text': message}, type_=36)
