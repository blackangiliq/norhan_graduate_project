"""
صيغة حزمة الصوت عبر UDP (القناة الناقلة للوسائط).

 0        1        2                 6                 10                         N-16      N
 +--------+--------+-----------------+-----------------+---------------------------+---------+
 |version |  type  |  sequence (u32) | timestamp (u32) |  ciphertext (encrypted)   | tag 16B |
 +--------+--------+-----------------+-----------------+---------------------------+---------+
 |<------------- header 10 bytes (AD: authenticated, not encrypted) ---------------->|

 - الترويسة Header غير مشفرة (يحتاجها المستقبل لمعرفة رقم التسلسل) لكنها موثّقة كـ Associated Data:
   أي تعديل عليها يُفشل التحقق من الوسم.
 - Nonce = IV_direction XOR sequence  (لا يُرسل على الشبكة إطلاقاً).
"""
import struct

VERSION = 1
HEADER_FMT = ">BBII"
HEADER_SIZE = struct.calcsize(HEADER_FMT)   # 10

T_VOICE = 1
T_PING = 2
T_PONG = 3
TYPE_NAMES = {T_VOICE: "VOICE", T_PING: "PING", T_PONG: "PONG"}


class PacketError(Exception):
    pass


def build_header(ptype: int, seq: int, ts: int) -> bytes:
    return struct.pack(HEADER_FMT, VERSION, ptype, seq & 0xFFFFFFFF, ts & 0xFFFFFFFF)


def parse(packet: bytes):
    if len(packet) < HEADER_SIZE + 16:
        raise PacketError("packet too short")
    ver, ptype, seq, ts = struct.unpack(HEADER_FMT, packet[:HEADER_SIZE])
    if ver != VERSION:
        raise PacketError("bad version")
    if ptype not in TYPE_NAMES:
        raise PacketError("bad type")
    return ptype, seq, ts, packet[:HEADER_SIZE], packet[HEADER_SIZE:]
