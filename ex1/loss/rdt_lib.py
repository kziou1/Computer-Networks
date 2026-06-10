import struct

SYN  = 8  # 0000 1000
ACK  = 4  # 0000 0100
FIN  = 2  # 0000 0010
DATA = 1  # 0000 0001

class UDPSeg:

    def __init__(self, seq, ack, flag, data=b''):
        self.seq = seq
        self.ack = ack
        self.flag = flag
        self.length = len(data)
        self.data = data

    def encapsulation(self):

        header = struct.pack("!IIBH", self.seq, self.ack, self.flag, self.length)
        return header + self.data

    def is_syn(self):
        return (self.flag >> 3) & 1

    def is_ack(self):
        return (self.flag >> 2) & 1

    def is_fin(self):
        return (self.flag >> 1) & 1

def decapsulation(packet_bytes):
    header_size = struct.calcsize('!IIBH')

    if len(packet_bytes) < header_size:
        return None

    header_bytes = packet_bytes[:header_size]
    data_bytes = packet_bytes[header_size:]

    seq, ack, flags, length = struct.unpack('!IIBH', header_bytes)

    return UDPSeg(seq, ack, flags, data_bytes)
