from location import Location
import asyncio, struct, binascii
from protocol.decoder import Decoder
from protocol.encoder import Encoder

class Client:
    def __init__(self, server):
        self.ip = None
        self.room = ""
        self.uid = None
        self.state = 0
        self.old_type = 0
        self.direction = 4
        self.action_tag = ""
        self.server = server
        self.zoneId = "house"
        self.getLocation = False
        self.position = (-1.0, -1.0)
        self.step_to_activate = False

    async def listen_server(self, reader, writer):
        self.reader, self.writer = reader, writer
        self.ip = self.writer.get_extra_info('peername')[0]
        self.server.logging(f"Connection from {self.ip}")
        buffer = b""
        while True:
            await asyncio.sleep(0.2)
            try:
                data = await self.reader.read(8096)
            except OSError:
                break
            if not data:
                break
            try:
                final_data = Decoder(buffer + data).processFrame()
                if final_data:
                    print(f"Client sent: {final_data}")
                    await self.server.process_data(final_data, self)
            except Exception as e:
                continue
        await self._close_connection()

    async def send(self, data, type_=34):
        print(f"Server send: {data}")
        final_data = struct.pack(">b", type_)
        final_data += Encoder(data).processFrame()
        final_data = self._make_header(final_data) + final_data
        try:
            self.writer.write(final_data)
            await self.writer.drain()
        except (BrokenPipeError, ConnectionResetError, AssertionError,
                TimeoutError, OSError, AttributeError):
            self.writer.close()

    def _make_header(self, msg):
        buf = struct.pack(">i", len(msg)+5)
        buf += struct.pack(">B", 8)
        buf += struct.pack(">I", binascii.crc32(msg))
        return buf

    async def _close_connection(self):
        if self.uid in self.server.online:
            if self.room:
                await self.server.rooms.leave_room(self.room, self)
            del self.server.online[self.uid]
        self.server.logging(f"Connection close with {self.ip}")
        return self.writer.close()
