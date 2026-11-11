"""
اختبار شامل: مكالمة حقيقية بين جهازين افتراضيين عبر الشبكة المحلية 127.0.0.1
(TCP + UDP حقيقيان، تشفير حقيقي، مصدر صوت اصطناعي بدل الميكروفون).
"""
import itertools
import time

import pytest

from securevoice.audio.devices import FakeAudioBackend
from securevoice.crypto.ciphers import CIPHERS
from securevoice.session import ENDED, IN_CALL, CallConfig, CallSession

_ports = itertools.count(47000, 10)


def wait_for(cond, timeout=8.0):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.05)
    return False


def make_pair(cipher_id=1, codec_id=1, pw_a="pw", pw_b="pw"):
    base = next(_ports)
    fa, fb = FakeAudioBackend(440), FakeAudioBackend(880)
    ev_a, ev_b = [], []
    a = CallSession(CallConfig(password=pw_a, tcp_port=base, udp_port=base + 1), lambda c: fa,
                    lambda k, d: ev_a.append((k, d)))
    b = CallSession(CallConfig(password=pw_b, cipher_id=cipher_id, codec_id=codec_id, tcp_port=base,
                               udp_port=base + 2), lambda c: fb, lambda k, d: ev_b.append((k, d)))
    a.start_listen()
    time.sleep(0.2)
    b.start_call("127.0.0.1")
    return a, b, fa, fb, ev_a, ev_b


@pytest.mark.parametrize("cid", list(CIPHERS))
def test_full_call_voice_delivered_bit_exact(cid):
    a, b, fa, fb, ev_a, ev_b = make_pair(cipher_id=cid)
    try:
        assert wait_for(lambda: a.state == IN_CALL and b.state == IN_CALL)
        assert a.info["sas"] == b.info["sas"]
        assert a.info["cipher"] == CIPHERS[cid].name
        time.sleep(1.5)
        sa, sb = a.snapshot(), b.snapshot()
        assert sa["rx_packets"] > 40 and sb["rx_packets"] > 40
        assert sa["auth_failures"] == 0 and sa["replays_blocked"] == 0
        # الصوت الذي شغّله A هو بالضبط ما التقطه B (بعد التشفير وفك التشفير)
        sent_by_b = set(fb.captured)
        delivered = [f for f in fa.played if f in sent_by_b]
        assert len(delivered) > 30
        sent_by_a = set(fa.captured)
        assert len([f for f in fb.played if f in sent_by_a]) > 30
    finally:
        b.hangup()
    assert wait_for(lambda: a.state == ENDED and b.state == ENDED)
    assert ("ended", "peer hangup") in ev_a


def test_ulaw_codec_call():
    a, b, fa, fb, *_ = make_pair(codec_id=2)
    try:
        assert wait_for(lambda: a.state == IN_CALL and b.state == IN_CALL)
        assert a.info["codec"].startswith("G.711")
        time.sleep(1.0)
        assert a.snapshot()["rx_packets"] > 20
    finally:
        b.hangup()


def test_attacks_are_detected_and_blocked():
    a, b, fa, fb, ev_a, ev_b = make_pair()
    try:
        assert wait_for(lambda: a.state == IN_CALL and b.state == IN_CALL)
        time.sleep(0.8)
        b.simulate_attack("tamper")
        b.simulate_attack("forge")
        b.simulate_attack("replay")
        assert wait_for(lambda: a.snapshot()["auth_failures"] >= 2 and a.snapshot()["replays_blocked"] >= 10)
        alerts = [d for k, d in ev_a if k == "alert"]
        assert any("فشل التحقق" in x for x in alerts)
        assert any("مكررة" in x for x in alerts)
        statuses = {p["status"] for p in a.packets}
        assert {"AUTH FAIL", "REPLAY"} <= statuses
        # المكالمة مستمرة بعد الهجمات
        before = a.snapshot()["rx_packets"]
        time.sleep(0.5)
        assert a.snapshot()["rx_packets"] > before and a.state == IN_CALL
    finally:
        b.hangup()


def test_encrypted_chat_and_mute():
    a, b, *_rest, ev_a, ev_b = make_pair()
    try:
        assert wait_for(lambda: a.state == IN_CALL and b.state == IN_CALL)
        b.send_chat("مرحبا 👋")
        a.send_chat("أهلاً")
        assert wait_for(lambda: ("chat", "مرحبا 👋") in ev_a and ("chat", "أهلاً") in ev_b)
        b.set_mute(True)
        assert wait_for(lambda: a.peer_muted)
    finally:
        a.hangup()
    assert wait_for(lambda: b.state == ENDED)


def test_wrong_password_no_call():
    a, b, *_rest, ev_a, ev_b = make_pair(pw_a="correct", pw_b="incorrect")
    assert wait_for(lambda: a.state == ENDED and b.state == ENDED)
    assert any(k == "error" for k, _ in ev_a) and any(k == "error" for k, _ in ev_b)
    assert not any(k == "connected" for k, _ in ev_a)


def test_eavesdrop_mode_plays_noise():
    import numpy as np
    a, b, fa, fb, *_ = make_pair()
    try:
        assert wait_for(lambda: a.state == IN_CALL and b.state == IN_CALL)
        a.eavesdrop = True
        time.sleep(0.4)
        n = len(fa.played)
        time.sleep(0.6)
        frames = fa.played[n:]
        sent = set(fb.captured)
        assert frames and not any(f in sent for f in frames)
        # الضجيج: توزيع شبه منتظم للقيم
        x = np.frombuffer(frames[-1], dtype=np.int16)
        assert np.std(x) > 10000
    finally:
        b.hangup()


def test_cancel_listening():
    s = CallSession(CallConfig(tcp_port=next(_ports), udp_port=0), lambda c: FakeAudioBackend())
    s.start_listen()
    assert wait_for(lambda: s.state == "listening")
    s.hangup()
    assert wait_for(lambda: s.state == ENDED)


def test_connect_to_nobody_reports_error():
    ev = []
    s = CallSession(CallConfig(tcp_port=next(_ports), udp_port=0), lambda c: FakeAudioBackend(),
                    lambda k, d: ev.append((k, d)))
    s.start_call("127.0.0.1")
    assert wait_for(lambda: s.state == ENDED)
    assert any(k == "error" for k, _ in ev)
