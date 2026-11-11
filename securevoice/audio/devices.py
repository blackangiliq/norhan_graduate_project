"""
طبقة الصوت: التقاط الصوت من الميكروفون وتشغيله على السماعة.
- SoundDeviceBackend : يستخدم مكتبة sounddevice (PortAudio) - تعمل على Windows مباشرة.
- FakeAudioBackend   : مصدر صوت اصطناعي (نغمة) للاختبارات الآلية بدون ميكروفون.
"""
import threading
import time

import numpy as np

from .codec import FRAME_SAMPLES, PCM_FRAME_BYTES, SAMPLE_RATE

try:
    import sounddevice as sd
except Exception:          # PortAudio غير موجود (مثلاً خادم بدون صوت)
    sd = None


def audio_available() -> bool:
    if sd is None:
        return False
    try:
        return len(sd.query_devices()) > 0
    except Exception:
        return False


def list_devices():
    """قائمة أجهزة الإدخال والإخراج (من واجهة الصوت الافتراضية فقط لتجنب التكرار في Windows)."""
    inputs, outputs = [], []
    if not audio_available():
        return inputs, outputs, None, None
    default_api = sd.default.hostapi
    for i, d in enumerate(sd.query_devices()):
        if d["hostapi"] != default_api:
            continue
        if d["max_input_channels"] > 0:
            inputs.append((i, d["name"]))
        if d["max_output_channels"] > 0:
            outputs.append((i, d["name"]))
    din, dout = sd.default.device
    return inputs, outputs, din, dout


class SoundDeviceBackend:
    def __init__(self, input_device=None, output_device=None):
        self.input_device = None if input_device in (None, -1) else input_device
        self.output_device = None if output_device in (None, -1) else output_device
        self.in_stream = None
        self.out_stream = None

    def start(self, on_capture, on_playback):
        if sd is None:
            raise RuntimeError("sounddevice / PortAudio is not available")

        def in_cb(indata, frames, t, status):
            on_capture(bytes(indata))

        def out_cb(outdata, frames, t, status):
            data = on_playback()
            if len(data) < len(outdata):
                data = data + bytes(len(outdata) - len(data))
            outdata[:] = data[:len(outdata)]

        self.in_stream = sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=FRAME_SAMPLES, channels=1,
                                           dtype="int16", device=self.input_device, callback=in_cb,
                                           latency="low")
        self.out_stream = sd.RawOutputStream(samplerate=SAMPLE_RATE, blocksize=FRAME_SAMPLES, channels=1,
                                             dtype="int16", device=self.output_device, callback=out_cb,
                                             latency="low")
        self.in_stream.start()
        self.out_stream.start()

    def stop(self):
        for s in (self.in_stream, self.out_stream):
            if s is not None:
                try:
                    s.stop(); s.close()
                except Exception:
                    pass
        self.in_stream = self.out_stream = None


TEST_TONE = -2      # خيار "نغمة اختبار" بدل الميكروفون


class ToneInputBackend:
    """ميكروفون افتراضي (نغمة موسيقية) + سماعة حقيقية - للعرض على جهاز بدون ميكروفون."""

    def __init__(self, output_device=None):
        self.fake = FakeAudioBackend(freq=523.25, amplitude=6000)
        self.out = SoundDeviceBackend(None, output_device) if audio_available() else None

    def start(self, on_capture, on_playback):
        self._stop = threading.Event()

        def cap():
            n = 0
            nxt = time.perf_counter()
            while not self._stop.is_set():
                # نغمة متقطعة (نصف ثانية صوت / نصف ثانية صمت) ليسهل تمييزها
                f = self.fake.frame(n) if (n // 25) % 2 == 0 else bytes(PCM_FRAME_BYTES)
                n += 1
                on_capture(f)
                nxt += 0.02
                time.sleep(max(0, nxt - time.perf_counter()))
        threading.Thread(target=cap, daemon=True).start()
        if self.out is not None:
            def out_cb(outdata, frames, t, status):
                data = on_playback()
                outdata[:] = data[:len(outdata)].ljust(len(outdata), b"\0")
            self.out.out_stream = sd.RawOutputStream(samplerate=SAMPLE_RATE, blocksize=FRAME_SAMPLES,
                                                     channels=1, dtype="int16", device=self.out.output_device,
                                                     callback=out_cb, latency="low")
            self.out.out_stream.start()
        else:
            self._null = FakeAudioBackend()
            self._null.start(lambda f: None, on_playback)

    def stop(self):
        self._stop.set()
        if self.out is not None:
            self.out.stop()
        elif hasattr(self, "_null"):
            self._null.stop()


def make_backend(input_device=None, output_device=None):
    """اختيار طبقة الصوت المناسبة حسب الإعدادات والأجهزة المتوفرة."""
    if not audio_available():
        return FakeAudioBackend()
    if input_device == TEST_TONE:
        return ToneInputBackend(output_device)
    return SoundDeviceBackend(input_device, output_device)


class FakeAudioBackend:
    """يولّد نغمة جيبية كإطارات كل 20ms ويخزن ما يتم تشغيله - للاختبار."""

    def __init__(self, freq=440.0, amplitude=8000):
        self.freq = freq
        self.amplitude = amplitude
        self.played = []
        self.captured = []
        self._stop = threading.Event()
        self._threads = []

    def frame(self, n):
        t = (np.arange(FRAME_SAMPLES) + n * FRAME_SAMPLES) / SAMPLE_RATE
        return (self.amplitude * np.sin(2 * np.pi * self.freq * t)).astype(np.int16).tobytes()

    def start(self, on_capture, on_playback):
        def cap():
            n = 0
            nxt = time.perf_counter()
            while not self._stop.is_set():
                f = self.frame(n); n += 1
                self.captured.append(f)
                on_capture(f)
                nxt += 0.02
                time.sleep(max(0, nxt - time.perf_counter()))

        def play():
            nxt = time.perf_counter()
            while not self._stop.is_set():
                d = on_playback()
                assert len(d) == PCM_FRAME_BYTES
                self.played.append(d)
                nxt += 0.02
                time.sleep(max(0, nxt - time.perf_counter()))

        for fn in (cap, play):
            th = threading.Thread(target=fn, daemon=True); th.start(); self._threads.append(th)

    def stop(self):
        self._stop.set()
        for th in self._threads:
            th.join(timeout=1)
