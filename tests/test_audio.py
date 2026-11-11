"""اختبارات الترميز ومخزن الارتعاش وبنية الحزمة."""
import numpy as np
import pytest

from securevoice.audio.codec import FRAME_SAMPLES, PCM_FRAME_BYTES, get_codec, level_db
from securevoice.audio.jitter import JitterBuffer
from securevoice.net import packet as pk


def tone():
    t = np.arange(FRAME_SAMPLES) / 16000
    return (10000 * np.sin(2 * np.pi * 440 * t)).astype(np.int16).tobytes()


def test_pcm_codec_lossless():
    c = get_codec(1)
    assert c.decode(c.encode(tone())) == tone()


def test_ulaw_codec_halves_size_and_low_error():
    c = get_codec(2)
    enc = c.encode(tone())
    assert len(enc) == FRAME_SAMPLES == PCM_FRAME_BYTES // 2
    dec = np.frombuffer(c.decode(enc), dtype=np.int16).astype(int)
    orig = np.frombuffer(tone(), dtype=np.int16).astype(int)
    snr = 10 * np.log10(np.sum(orig ** 2) / np.sum((orig - dec) ** 2))
    assert snr > 30            # جودة G.711 النموذجية ~ 38 dB


def test_level_db():
    assert level_db(bytes(640)) == -90.0
    assert -20 < level_db(tone()) < -5


def test_jitter_reorders_and_conceals():
    j = JitterBuffer(4, target_depth=2)
    for s in (1, 3, 2, 5):
        j.push(s, bytes([s]) * 4)
    out = [j.pop() for _ in range(5)]
    assert out[0][0] == 1 and out[1][0] == 2 and out[2][0] == 3
    assert out[4][0] == 5
    assert j.lost == 1            # الإطار 4 مفقود -> إخفاء
    j.push(2, b"late")
    assert j.late == 1


def test_jitter_prebuffer_returns_silence():
    j = JitterBuffer(4, target_depth=3)
    j.push(1, b"aaaa")
    assert j.pop() == bytes(4)


def test_packet_header_roundtrip():
    h = pk.build_header(pk.T_VOICE, 123456, 789)
    assert len(h) == pk.HEADER_SIZE == 10
    ptype, seq, ts, hdr, body = pk.parse(h + bytes(32))
    assert (ptype, seq, ts, hdr) == (pk.T_VOICE, 123456, 789, h)
    with pytest.raises(pk.PacketError):
        pk.parse(b"\x09" + h[1:] + bytes(32))
    with pytest.raises(pk.PacketError):
        pk.parse(h)
