from modules.base_module import Module

class_name = "UserConfirm"


class UserConfirm(Module):
    prefix = "cf"

    def __init__(self, server):
        self.server = server
        self.commands = {"uc": self.user_confirm,
                         "uca": self.user_confirm_approve,
                         "ucd": self.user_confirm_decline}
        self.confirms = {}

    async def user_confirm(self, msg, client):
        if msg['data']["uid"] == client.uid: return
        if msg['data']["uid"] in self.server.online:
            tmp = self.server.online[msg['data']["uid"]]
            self.confirms[client.uid] = {"uid": msg['data']["uid"],
                                         "at": msg['data']["at"],
                                         "completed": False}
            return await tmp.send({'data': {"uid": client.uid, "at": msg['data']["at"]}, 'command': 'cf.uc'})

    async def user_confirm_approve(self, msg, client):
        if msg['data']["uid"] in self.server.online and \
           msg['data']["uid"] in self.confirms:
            tmp = self.server.online[msg['data']["uid"]]
            if self.confirms[tmp.uid]["at"] != msg['data']["at"] or \
                            self.confirms[tmp.uid]["uid"] != client.uid: return
            self.confirms[tmp.uid]["completed"] = True
            return await tmp.send({'data': {"uid": client.uid, "at": msg['data']["at"]}, 'command': 'cf.uca'})

    async def user_confirm_decline(self, msg, client):
        if msg['data']["uid"] in self.server.online and \
           msg['data']["uid"] in self.confirms:
            tmp = self.server.online[msg['data']["uid"]]
            if self.confirms[tmp.uid]["at"] != msg['data']["at"] or \
                            self.confirms[tmp.uid]["uid"] != client.uid: return
            del self.confirms[tmp.uid]
            return await tmp.send({'data': {"uid": client.uid, "at": msg['data']["at"]}, 'command': 'cf.ucd'})
