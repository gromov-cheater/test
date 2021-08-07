import time
from datetime import datetime
import asyncio, struct, binascii

class Encoder:
    def __init__(self, data):
        self.data = data

    def processFrame(self):
        if isinstance(self.data, dict):
            return self.encodeObject()
        return print(f"Не могу енкодить: {type(self.data)}")

    def encodeValue(self, data, forDict=False):
        final_data = b""
        if data is None:
            final_data += struct.pack(">b", 0)
        elif isinstance(data, bool):
            final_data += struct.pack(">b", 1)
            final_data += struct.pack(">b", int(data))
        elif isinstance(data, int):
            if data > 2147483647:
                final_data += struct.pack(">b", 3)
                final_data += struct.pack(">q", data)
            else:
                final_data += struct.pack(">b", 2)
                final_data += struct.pack(">i", data)
        elif isinstance(data, float):
            final_data += struct.pack(">b", 4)
            final_data += struct.pack(">d", data)
        elif isinstance(data, str):
            if not forDict:
                final_data += struct.pack(">b", 5)
            length = len(data.encode().hex())//2
            if len(data) >= 1000:
                final_data += struct.pack(">b", 4)
            while (length & 4294967168) != 0:
                final_data += struct.pack(">B", length & 127 | 128)
                length = length >> 7
            if len(data) < 1000:
                final_data += struct.pack(">h", length & 127)
            final_data += data.encode()
        elif isinstance(data, dict):
            final_data += struct.pack(">b", 6)
            final_data += self.encodeDict(data)
        elif isinstance(data, list):
            final_data += struct.pack(">b", 7)
            final_data += self.encodeArray(data)
        elif isinstance(data, datetime):
            final_data += struct.pack(">b", 8)
            final_data += struct.pack(">q", int(data.timestamp() * 1000))
        else:
            raise ValueError("Не могу энкодить "+str(type(data)))
        return final_data

    def encodeObject(self):
        final_data = struct.pack(">I", len(self.data))
        for item in self.data.keys():
            final_data += self.encodeValue(item, forDict=True)
            final_data += self.encodeValue(self.data[item])
        return final_data

    def encodeDict(self, data):
        final_data = struct.pack(">I", len(data))
        for item in data.keys():
            final_data += self.encodeValue(item, forDict=True)
            final_data += self.encodeValue(data[item])
        return final_data

    def encodeArray(self, data):
        final_data = struct.pack(">i", len(data))
        for item in data:
            final_data += self.encodeValue(item)
        return final_data
