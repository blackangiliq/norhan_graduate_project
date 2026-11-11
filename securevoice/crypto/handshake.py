"""
بروتوكول المصافحة وتبادل المفاتيح (Handshake / Key Exchange).

الخطوات:
 1) ClientHello  : المتصل يرسل مفتاحه العام X25519 المؤقت + رقم عشوائي + الخوارزمية المقترحة + منفذ UDP.
 2) ServerHello  : المستقبل يرد بمفتاحه العام المؤقت + رقمه العشوائي + منفذ UDP.
 3) كل طرف يحسب السر المشترك ECDH:  shared = X25519(my_private, peer_public)
 4) PSK = PBKDF2-HMAC-SHA256(password, salt = client_random || server_random, 100000 iterations)
 5) master = HKDF-Extract(salt=PSK, ikm=shared)
 6) مفاتيح الجلسة = HKDF-Expand(master, info="SecureVoice v1 keys" || transcript_hash)
       -> مفتاح + IV لكل اتجاه (C->S و S->C) للصوت، ومفتاح + IV للتحكم، ومفتاح للتأكيد، ورمز الأمان.
 7) Finished     : كل طرف يرسل HMAC(confirm_key, label || transcript_hash) ليثبت أنه يعرف كلمة السر
                   ويملك نفس المفاتيح. إذا لم يتطابق -> كلمة سر خاطئة أو هجوم رجل في المنتصف MITM.

الخصائص الأمنية:
 - السرية الأمامية Forward Secrecy: مفاتيح X25519 مؤقتة لكل مكالمة وتُحذف بعدها.
 - المصادقة المتبادلة: لا يمكن إكمال المصافحة بدون معرفة كلمة السر المشتركة.
 - رمز الأمان SAS: 6 أرقام تظهر على الشاشتين للتحقق الصوتي.
"""
import hashlib
import hmac
import os
import socket
import struct
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDFExpand
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .ciphers import get_cipher

MAGIC = b"SVC1"
PROTOCOL_VERSION = 1
PBKDF2_ITERATIONS = 100_000
HELLO_FMT = ">4sBBBH16s32s"     # magic, version, cipher_id, codec_id, udp_port, random, pubkey
HELLO_SIZE = struct.calcsize(HELLO_FMT)

# رموز الأخطاء في المصافحة
ERR_OK = 0
ERR_BAD_PASSWORD = 1
ERR_UNSUPPORTED = 2


class HandshakeError(Exception):
    pass


@dataclass
class SessionKeys:
    cipher_id: int
    codec_id: int
    is_initiator: bool
    tx_key: bytes
    tx_iv: bytes
    rx_key: bytes
    rx_iv: bytes
    ctl_tx_key: bytes
    ctl_tx_iv: bytes
    ctl_rx_key: bytes
    ctl_rx_iv: bytes
    sas: str                 # Short Authentication String (رمز الأمان)
    peer_udp_port: int
    transcript_hash: bytes
    fingerprint: str          # بصمة مختصرة لمفتاح الجلسة (للعرض فقط)


# ------------------------------------------------------------------ framing helpers
def send_frame(sock: socket.socket, data: bytes):
    sock.sendall(struct.pack(">H", len(data)) + data)


def recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("connection closed by peer")
        buf += chunk
    return bytes(buf)


def recv_frame(sock: socket.socket) -> bytes:
    (n,) = struct.unpack(">H", recv_exact(sock, 2))
    return recv_exact(sock, n)


# ------------------------------------------------------------------ key schedule
def derive_psk(password: str, client_random: bytes, server_random: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                               b"SecureVoice-PSK" + client_random + server_random,
                               PBKDF2_ITERATIONS, 32)


def derive_keys(shared: bytes, psk: bytes, transcript_hash: bytes):
    """يعيد قاموس المفاتيح المشتقة (كل الطول الذي نحتاجه في طلب HKDF واحد)."""
    master = hmac.new(psk, shared, hashlib.sha256).digest()                 # HKDF-Extract
    okm = HKDFExpand(hashes.SHA256(), 32 * 4 + 16 * 4 + 32 + 8,
                     b"SecureVoice v1 keys" + transcript_hash).derive(master)  # HKDF-Expand
    parts, pos = {}, 0
    for name, ln in (("c2s_key", 32), ("s2c_key", 32), ("ctl_c2s_key", 32), ("ctl_s2c_key", 32),
                     ("c2s_iv", 16), ("s2c_iv", 16), ("ctl_c2s_iv", 16), ("ctl_s2c_iv", 16),
                     ("confirm", 32), ("sas", 8)):
        parts[name] = okm[pos:pos + ln]; pos += ln
    return parts


def finished_mac(confirm_key: bytes, label: bytes, transcript_hash: bytes) -> bytes:
    return hmac.new(confirm_key, label + transcript_hash, hashlib.sha256).digest()


def _pub_bytes(priv: X25519PrivateKey) -> bytes:
    return priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def _build_keys(parts, initiator, cipher_id, codec_id, peer_udp, th) -> SessionKeys:
    p = parts
    if initiator:
        tx, rx, ctx, crx = "c2s", "s2c", "ctl_c2s", "ctl_s2c"
    else:
        tx, rx, ctx, crx = "s2c", "c2s", "ctl_s2c", "ctl_c2s"
    sas_num = int.from_bytes(p["sas"], "big") % 1_000_000
    return SessionKeys(
        cipher_id=cipher_id, codec_id=codec_id, is_initiator=initiator,
        tx_key=p[tx + "_key"], tx_iv=p[tx + "_iv"], rx_key=p[rx + "_key"], rx_iv=p[rx + "_iv"],
        ctl_tx_key=p[ctx + "_key"], ctl_tx_iv=p[ctx + "_iv"],
        ctl_rx_key=p[crx + "_key"], ctl_rx_iv=p[crx + "_iv"],
        sas=f"{sas_num // 1000:03d}-{sas_num % 1000:03d}", peer_udp_port=peer_udp, transcript_hash=th,
        fingerprint=hashlib.sha256(p["c2s_key"] + p["s2c_key"]).hexdigest()[:16].upper())


# ------------------------------------------------------------------ roles
def client_handshake(sock, password: str, cipher_id: int, codec_id: int, udp_port: int) -> SessionKeys:
    """دور المتصل (Initiator)."""
    get_cipher(cipher_id)
    priv = X25519PrivateKey.generate()
    c_random = os.urandom(16)
    ch = struct.pack(HELLO_FMT, MAGIC, PROTOCOL_VERSION, cipher_id, codec_id, udp_port, c_random, _pub_bytes(priv))
    send_frame(sock, ch)

    sh = recv_frame(sock)
    if len(sh) != HELLO_SIZE:
        raise HandshakeError("malformed ServerHello")
    magic, ver, s_cipher, s_codec, s_udp, s_random, s_pub = struct.unpack(HELLO_FMT, sh)
    if magic != MAGIC or ver != PROTOCOL_VERSION:
        raise HandshakeError("peer is not a SecureVoice v1 endpoint")
    if s_cipher != cipher_id or s_codec != codec_id:
        raise HandshakeError("peer changed negotiated parameters (downgrade attempt?)")

    th = hashlib.sha256(ch + sh).digest()
    shared = priv.exchange(X25519PublicKey.from_public_bytes(s_pub))
    parts = derive_keys(shared, derive_psk(password, c_random, s_random), th)

    send_frame(sock, finished_mac(parts["confirm"], b"client finished", th))
    resp = recv_frame(sock)
    if len(resp) == 1:
        raise HandshakeError("wrong password (rejected by peer)" if resp[0] == ERR_BAD_PASSWORD
                             else "rejected by peer")
    if not hmac.compare_digest(resp, finished_mac(parts["confirm"], b"server finished", th)):
        raise HandshakeError("server authentication failed - possible MITM attack")
    return _build_keys(parts, True, cipher_id, codec_id, s_udp, th)


def server_handshake(sock, password: str, udp_port: int, allowed_ciphers=None) -> SessionKeys:
    """دور المستقبل (Responder). يقبل الخوارزمية التي يقترحها المتصل إن كانت مدعومة."""
    ch = recv_frame(sock)
    if len(ch) != HELLO_SIZE:
        raise HandshakeError("malformed ClientHello")
    magic, ver, cipher_id, codec_id, c_udp, c_random, c_pub = struct.unpack(HELLO_FMT, ch)
    if magic != MAGIC or ver != PROTOCOL_VERSION:
        raise HandshakeError("peer is not a SecureVoice v1 endpoint")
    try:
        get_cipher(cipher_id)
    except ValueError:
        send_frame(sock, bytes([ERR_UNSUPPORTED])); raise HandshakeError("unsupported cipher")
    if allowed_ciphers is not None and cipher_id not in allowed_ciphers:
        send_frame(sock, bytes([ERR_UNSUPPORTED])); raise HandshakeError("cipher not allowed by policy")

    priv = X25519PrivateKey.generate()
    s_random = os.urandom(16)
    sh = struct.pack(HELLO_FMT, MAGIC, PROTOCOL_VERSION, cipher_id, codec_id, udp_port, s_random, _pub_bytes(priv))
    send_frame(sock, sh)

    th = hashlib.sha256(ch + sh).digest()
    shared = priv.exchange(X25519PublicKey.from_public_bytes(c_pub))
    parts = derive_keys(shared, derive_psk(password, c_random, s_random), th)

    fin = recv_frame(sock)
    if not hmac.compare_digest(fin, finished_mac(parts["confirm"], b"client finished", th)):
        send_frame(sock, bytes([ERR_BAD_PASSWORD]))
        raise HandshakeError("client authentication failed - wrong password or MITM attack")
    send_frame(sock, finished_mac(parts["confirm"], b"server finished", th))
    return _build_keys(parts, False, cipher_id, codec_id, c_udp, th)
