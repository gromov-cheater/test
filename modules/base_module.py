class Module:
    def __init__(self):
        self.commands = {}

    async def get_message(self, msg, client):
        command = msg['command'].split(".")[1]
        if command not in self.commands: print(f"В команде {msg['command'].split('.')[0]}, нет команды {command}"); return
        return await self.commands[command](msg, client)
