"""
طبقة موحّدة لخوارزميات التشفير الموثّق AEAD المدعومة في النظام.
Unified AEAD interface for the supported ciphers.

| ID | الاسم            | النوع                    | المفتاح | Nonce | Tag |
|----|------------------|--------------------------|---------|-------|-----|
| 1  | Ascon-128        | خفيف الوزن (NIST LWC)    | 128     | 128   | 128 |
| 2  | ChaCha20-Poly1305| خفيف برمجياً (RFC 8439)  | 256     | 96    | 128 |
| 3  | AES-128-GCM      | المعيار التقليدي (مرجع)  | 128     | 96    | 128 |
"""
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305

from . import ascon


class AuthenticationError(Exception):
    """فشل التحقق: الحزمة معدّلة أو مزوّرة أو مشفّرة بمفتاح مختلف."""


class AEADCipher:
    id = 0
    name = ""
    key_size = 16
    nonce_size = 12
    tag_size = 16
    lightweight = False
    description = ""

    def __init__(self, key: bytes):
        if len(key) < self.key_size:
            raise ValueError("key too short")
        self.key = key[:self.key_size]

    def encrypt(self, nonce: bytes, plaintext: bytes, ad: bytes = b"") -> bytes:
        raise NotImplementedError

    def decrypt(self, nonce: bytes, ciphertext: bytes, ad: bytes = b"") -> bytes:
        raise NotImplementedError


class Ascon128(AEADCipher):
    id = 1
    name = "Ascon-128"
    key_size = 16
    nonce_size = 16
    lightweight = True
    description = "Ascon v1.2 - NIST Lightweight Cryptography winner (basis of SP 800-232), sponge-based, 320-bit state"

    def encrypt(self, nonce, plaintext, ad=b""):
        return ascon.encrypt(self.key, nonce, ad, plaintext)

    def decrypt(self, nonce, ciphertext, ad=b""):
        try:
            return ascon.decrypt(self.key, nonce, ad, ciphertext)
        except ascon.AsconAuthError as e:
            raise AuthenticationError(str(e)) from None


class ChaCha20Poly1305Cipher(AEADCipher):
    id = 2
    name = "ChaCha20-Poly1305"
    key_size = 32
    nonce_size = 12
    lightweight = True
    description = "ARX stream cipher + Poly1305 MAC (RFC 8439), fast in software without hardware AES"

    def __init__(self, key):
        super().__init__(key)
        self._c = ChaCha20Poly1305(self.key)

    def encrypt(self, nonce, plaintext, ad=b""):
        return self._c.encrypt(nonce, plaintext, ad)

    def decrypt(self, nonce, ciphertext, ad=b""):
        try:
            return self._c.decrypt(nonce, ciphertext, ad)
        except InvalidTag:
            raise AuthenticationError("authentication tag mismatch") from None


class AES128GCM(AEADCipher):
    id = 3
    name = "AES-128-GCM"
    key_size = 16
    nonce_size = 12
    lightweight = False
    description = "Conventional block cipher baseline (FIPS 197 + SP 800-38D), used for comparison"

    def __init__(self, key):
        super().__init__(key)
        self._c = AESGCM(self.key)

    def encrypt(self, nonce, plaintext, ad=b""):
        return self._c.encrypt(nonce, plaintext, ad)

    def decrypt(self, nonce, ciphertext, ad=b""):
        try:
            return self._c.decrypt(nonce, ciphertext, ad)
        except InvalidTag:
            raise AuthenticationError("authentication tag mismatch") from None


CIPHERS = {c.id: c for c in (Ascon128, ChaCha20Poly1305Cipher, AES128GCM)}
CIPHERS_BY_NAME = {c.name: c for c in CIPHERS.values()}


def get_cipher(cipher_id: int):
    try:
        return CIPHERS[cipher_id]
    except KeyError:
        raise ValueError(f"unknown cipher id {cipher_id}") from None


def make_nonce(iv: bytes, seq: int, size: int) -> bytes:
    """بناء الـ Nonce: IV سري (مشتق من المفتاح) XOR رقم التسلسل - نفس أسلوب TLS 1.3.
    يضمن عدم تكرار الـ Nonce أبداً طالما رقم التسلسل لا يتكرر."""
    iv = iv[:size]
    return (int.from_bytes(iv, "big") ^ seq).to_bytes(size, "big")
