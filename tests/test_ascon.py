"""اختبارات خوارزمية Ascon-128 مقابل متجهات الاختبار الرسمية (Known Answer Tests)."""
import os

import pytest

from securevoice.crypto import ascon

KEY = bytes(range(16))
NONCE = bytes(range(16))

# من ملف LWC_AEAD_KAT_128_128.txt الرسمي لـ Ascon-128 v1.2
KAT = [
    # (PT, AD, CT||TAG)
    (b"", b"", "E355159F292911F794CB1432A0103A8A"),
    (b"", bytes([0]), "944DF887CD4901614C5DEDBC42FC0DA0"),
    (bytes([0]), b"", "BC18C3F4E39ECA7222490D967C79BFFC92"),
]


@pytest.mark.parametrize("pt,ad,expected", KAT)
def test_known_answer_vectors(pt, ad, expected):
    assert ascon.encrypt(KEY, NONCE, ad, pt).hex().upper() == expected
    assert ascon.decrypt(KEY, NONCE, ad, bytes.fromhex(expected)) == pt


@pytest.mark.parametrize("length", [0, 1, 7, 8, 9, 15, 16, 31, 320, 640, 1000])
def test_roundtrip_lengths(length):
    k, n, ad, pt = os.urandom(16), os.urandom(16), os.urandom(10), os.urandom(length)
    ct = ascon.encrypt(k, n, ad, pt)
    assert len(ct) == length + 16
    assert ascon.decrypt(k, n, ad, ct) == pt


def test_matches_reference_implementation():
    ref = pytest.importorskip("ascon", reason="reference package 'ascon' (pyascon) not installed")
    if not hasattr(ref, "encrypt"):
        pytest.skip("different 'ascon' package")
    for length in range(0, 40):
        k, n, ad, pt = os.urandom(16), os.urandom(16), os.urandom(length % 13), os.urandom(length)
        assert ascon.encrypt(k, n, ad, pt) == ref.encrypt(k, n, ad, pt, "Ascon-128")


def test_tamper_ciphertext_rejected():
    k, n = os.urandom(16), os.urandom(16)
    ct = bytearray(ascon.encrypt(k, n, b"hdr", b"secret voice frame"))
    ct[3] ^= 1
    with pytest.raises(ascon.AsconAuthError):
        ascon.decrypt(k, n, b"hdr", bytes(ct))


def test_tamper_tag_and_ad_rejected():
    k, n = os.urandom(16), os.urandom(16)
    ct = ascon.encrypt(k, n, b"hdr", b"x" * 50)
    with pytest.raises(ascon.AsconAuthError):
        ascon.decrypt(k, n, b"hdr", ct[:-1] + bytes([ct[-1] ^ 0x80]))
    with pytest.raises(ascon.AsconAuthError):
        ascon.decrypt(k, n, b"hdX", ct)


def test_wrong_key_or_nonce_rejected():
    k, n = os.urandom(16), os.urandom(16)
    ct = ascon.encrypt(k, n, b"", b"hello")
    with pytest.raises(ascon.AsconAuthError):
        ascon.decrypt(os.urandom(16), n, b"", ct)
    with pytest.raises(ascon.AsconAuthError):
        ascon.decrypt(k, os.urandom(16), b"", ct)


def test_ciphertext_looks_random():
    """نفس النص بـ nonce مختلف يعطي نصاً مشفراً مختلفاً تماماً."""
    k = os.urandom(16)
    pt = bytes(640)  # صمت كامل
    c1 = ascon.encrypt(k, os.urandom(16), b"", pt)
    c2 = ascon.encrypt(k, os.urandom(16), b"", pt)
    assert c1 != c2
    assert len(set(c1[:-16])) > 200       # توزيع بايتات واسع رغم أن الأصل أصفار


def test_invalid_sizes():
    with pytest.raises(ValueError):
        ascon.encrypt(b"short", bytes(16), b"", b"")
    with pytest.raises(ValueError):
        ascon.encrypt(bytes(16), b"short", b"", b"")
