"""
ترميز الصوت (Audio Codecs).
- PCM16  : الصوت الخام 16-bit، جودة كاملة، 256 kbit/s عند 16 kHz.
- G.711 μ-law : ضغط لوغاريتمي (معيار ITU-T G.711) من 16 بت إلى 8 بت لكل عينة -> نصف عرض النطاق 128 kbit/s.
"""
import numpy as np

SAMPLE_RATE = 16000          # 16 kHz (Wideband voice)
FRAME_MS = 20                 # مدة الإطار الواحد
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000   # 320 عينة
PCM_FRAME_BYTES = FRAME_SAMPLES * 2              # 640 بايت

_BIAS = 0x84
_CLIP = 32635


def _build_ulaw_tables():
    # جدول فك الترميز: 256 قيمة
    dec = np.zeros(256, dtype=np.int16)
    for i in range(256):
        u = ~i & 0xFF
        sign = u & 0x80
        exponent = (u >> 4) & 0x07
        mantissa = u & 0x0F
        sample = (((mantissa << 3) + _BIAS) << exponent) - _BIAS
        dec[i] = -sample if sign else sample
    # جدول الترميز: لكل قيمة 16 بت ممكنة (65536)
    x = np.arange(-32768, 32768, dtype=np.int32)
    sign = (x < 0).astype(np.int32) << 7
    mag = np.minimum(np.abs(x), _CLIP) + _BIAS
    exponent = np.floor(np.log2(mag)).astype(np.int32) - 7
    exponent = np.clip(exponent, 0, 7)
    mantissa = (mag >> (exponent + 3)) & 0x0F
    enc = (~(sign | (exponent << 4) | mantissa) & 0xFF).astype(np.uint8)
    return enc, dec


_ULAW_ENC, _ULAW_DEC = _build_ulaw_tables()


class Codec:
    id = 0
    name = ""
    bytes_per_frame = 0

    def encode(self, pcm: bytes) -> bytes: ...
    def decode(self, data: bytes) -> bytes: ...


class PCM16(Codec):
    id = 1
    name = "PCM 16-bit"
    bytes_per_frame = PCM_FRAME_BYTES

    def encode(self, pcm): return pcm
    def decode(self, data): return data


class ULaw(Codec):
    id = 2
    name = "G.711 μ-law"
    bytes_per_frame = FRAME_SAMPLES

    def encode(self, pcm):
        s = np.frombuffer(pcm, dtype=np.int16).astype(np.int32) + 32768
        return _ULAW_ENC[s].tobytes()

    def decode(self, data):
        return _ULAW_DEC[np.frombuffer(data, dtype=np.uint8)].tobytes()


CODECS = {c.id: c for c in (PCM16, ULaw)}


def get_codec(codec_id: int) -> Codec:
    try:
        return CODECS[codec_id]()
    except KeyError:
        raise ValueError(f"unknown codec {codec_id}") from None


def level_db(pcm: bytes) -> float:
    """مستوى الصوت RMS بالديسيبل (من -90 إلى 0 dBFS) لعرضه في مؤشر المستوى."""
    s = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
    if s.size == 0:
        return -90.0
    rms = float(np.sqrt(np.mean(s * s))) / 32768.0
    return float(max(-90.0, 20 * np.log10(rms + 1e-9)))
