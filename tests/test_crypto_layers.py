"""اختبارات طبقة الخوارزميات، الـ Nonce، نافذة منع التكرار، والمصافحة."""
import os
import socket
import threading

import pytest

from securevoice.crypto import handshake as hs
from securevoice.crypto.ciphers import CIPHERS, AuthenticationError, make_nonce
from securevoice.crypto.replay import ReplayWindow


@pytest.mark.parametrize("cid", list(CIPHERS))
def test_cipher_roundtrip_and_auth(cid):
    cls = CIPHERS[cid]
    c = cls(os.urandom(32))
    n = os.urandom(c.nonce_size)
    ct = c.encrypt(n, b"voice" * 100, b"header")
    assert c.decrypt(n, ct, b"header") == b"voice" * 100
    bad = bytearray(ct); bad[0] ^= 1
    with pytest.raises(AuthenticationError):
        c.decrypt(n, bytes(bad), b"header")
    with pytest.raises(AuthenticationError):
        c.decrypt(n, ct, b"HEADER")


def test_nonce_unique_per_sequence():
    iv = os.urandom(16)
    nonces = {make_nonce(iv, s, 12) for s in range(1, 10000)}
    assert len(nonces) == 9999
    assert make_nonce(iv, 5, 16) != make_nonce(os.urandom(16), 5, 16)


def test_replay_window():
    w = ReplayWindow(64)

    def feed(seq):
        ok = w.check(seq)
        if ok:
            w.update(seq)
        return ok

    assert feed(1) and feed(2) and feed(3)
    assert not feed(3)                    # تكرار
    assert feed(10)
    assert feed(5)                        # متأخرة لكن جديدة -> مقبولة
    assert not feed(5)                    # تكرار
    assert feed(100)
    assert not feed(30)                   # أقدم من النافذة (100-30 >= 64)
    assert feed(40)                       # داخل النافذة ولم تُستلم
    assert not feed(0)


def _run_handshake(pw_client, pw_server, cipher_id=1):
    a, b = socket.socketpair()
    out = {}

    def server():
        try:
            out["s"] = hs.server_handshake(a, pw_server, 6001)
        except Exception as e:      # noqa: BLE001
            out["se"] = e

    t = threading.Thread(target=server)
    t.start()
    try:
        out["c"] = hs.client_handshake(b, pw_client, cipher_id, 1, 6002)
    except Exception as e:          # noqa: BLE001
        out["ce"] = e
    t.join(5)
    a.close(); b.close()
    return out


@pytest.mark.parametrize("cid", list(CIPHERS))
def test_handshake_success_derives_matching_keys(cid):
    out = _run_handshake("secret", "secret", cid)
    c, s = out["c"], out["s"]
    assert c.sas == s.sas and c.fingerprint == s.fingerprint
    assert c.tx_key == s.rx_key and c.rx_key == s.tx_key
    assert c.tx_iv == s.rx_iv and c.ctl_tx_key == s.ctl_rx_key
    assert c.tx_key != c.rx_key                       # مفتاح مختلف لكل اتجاه
    assert c.peer_udp_port == 6001 and s.peer_udp_port == 6002
    assert c.cipher_id == s.cipher_id == cid


def test_handshake_fresh_keys_each_call():
    k1 = _run_handshake("pw", "pw")["c"]
    k2 = _run_handshake("pw", "pw")["c"]
    assert k1.tx_key != k2.tx_key          # السرية الأمامية: مفاتيح جديدة لكل مكالمة


def test_handshake_wrong_password_fails_both_sides():
    out = _run_handshake("right", "wrong")
    assert isinstance(out.get("ce"), hs.HandshakeError)
    assert isinstance(out.get("se"), hs.HandshakeError)
    assert "c" not in out and "s" not in out


def test_handshake_rejects_garbage():
    a, b = socket.socketpair()
    out = {}
    t = threading.Thread(target=lambda: out.setdefault("e", _catch(lambda: hs.server_handshake(a, "x", 1))))
    t.start()
    hs.send_frame(b, b"GET / HTTP/1.1\r\n")
    t.join(5)
    assert isinstance(out["e"], hs.HandshakeError)


def _catch(fn):
    try:
        fn()
    except Exception as e:          # noqa: BLE001
        return e
