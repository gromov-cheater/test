import time
from datetime import datetime
import asyncio, struct, binascii

class Decoder:
    def __init__(self, data):
        self.pos = 0
        self.data = data

    def read(self, amount):
        if self.pos + amount > len(self.data):
            raise Exception("Data is None")
        old_pos = self.pos
        self.pos = self.pos + amount
        return self.data[old_pos:self.pos]

    def decodeByte(self, byte):
        type, cnt = (">b", 1) if byte == "i8" else \
                    (">B", 1) if byte == "u8" else \
                    (">i", 4) if byte == "i32" else \
                    (">I", 4) if byte == "u32" else \
                    (">q", 8) if byte == "i64" else \
                    (">d", 8)
        return struct.unpack(type, self.read(cnt))[0]

    def processFrame(self):
        mask = self.read(9)
        return {
            'type': self.decodeByte('i8'),
            'msg': self.decodeObject()
        }

    def decodeValue(self):
        dataType = self.decodeByte('i8')
        if dataType == 0: return None
        elif dataType == 1:
            return True if self.decodeByte('i8') else False
        elif dataType == 2: return self.decodeByte('i32')
        elif dataType == 3: return self.decodeByte('i64')
        elif dataType == 4: return self.decodeByte('f64')
        elif dataType == 5: return self.decodeString()
        elif dataType == 6: return self.decodeDictionary()
        elif dataType == 7: return self.decodeArray()
        else: raise ValueError(f"Invalid data type signature = {dataType}")

    def decodeArray(self, element=0):
        array=[]
        elements = self.decodeByte('i32')
        while element < elements:
            array.append(self.decodeValue()); element += 1
        return array

    def decodeObject(self, element=0):
        object={}
        elements = self.decodeByte('i32')
        while element < elements:
            key = self.decodeString()
            object[key] = self.decodeValue(); element += 1
        return object

    def decodeDictionary(self, element=0):
        object={}
        elements = self.decodeByte('i32')
        while element < elements:
            key = self.decodeString()
            object[key] = self.decodeValue(); element += 1
        return object

    def decodeString(self):
        length = 1
        replaceBytes = self.read(2)
        while not isinstance(length, str):
            letter = self.getNextValue(length)
            if letter:
                length += 1
                continue
            break
        return self.read(length-1).decode('utf-8', 'ignore')

    def getNextValue(self, element):
        if not self.data[self.pos+(element-1):self.pos+(element-1)+1]:
            return None
        elements = struct.unpack(">b", self.data[self.pos+(element-1):self.pos+(element-1)+1])[0]
        if elements > 8 or elements < 0:
            return self.data[self.pos:self.pos+element]
        return None
