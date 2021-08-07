import base64

class MobileToken:
    def __init__(self):
        self.pos = 0

    def get_address(self, login):
        string = ""
        audit = None
        for element in login:
            string += login[self.pos:self.pos+1]
            self.pos += 1
            try:
                decode = base64.b64decode(string).decode()
            except:
                continue
        if 'aud' in decode:
            audit = decode.split('"aud":')[1].split(",")[0]
            if '"' in audit:
                audit = "".join(audit.split('"'))
        self.pos = 0
        return audit
