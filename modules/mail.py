from modules.base_module import Module

class_name = "Mail"

class Mail(Module):
    prefix = 'mail'
    def __init__(self, server):
        self.server = server
        self.commands = {'gc': self.get_count}

    async def get_count(self, msg, client):
        return await client.send({
            'data': {'in': [], 'out': []},
            'command': 'mail.gc'
        })
