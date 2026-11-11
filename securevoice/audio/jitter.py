"""
مخزن الارتعاش (Jitter Buffer).
الحزم عبر UDP قد تصل متأخرة أو بترتيب مختلف أو تضيع. هذا المخزن:
 1) يعيد ترتيب الإطارات حسب رقم التسلسل.
 2) ينتظر عدداً صغيراً من الإطارات (target_depth) قبل بدء التشغيل لامتصاص تذبذب التأخير.
 3) يخفي الإطارات المفقودة (Packet Loss Concealment) بتكرار الإطار السابق مع خفض صوته.
"""
import threading

import numpy as np


class JitterBuffer:
    def __init__(self, frame_bytes: int, target_depth: int = 3, max_depth: int = 25):
        self.frame_bytes = frame_bytes
        self.target_depth = target_depth
        self.max_depth = max_depth
        self.frames = {}
        self.next_seq = None
        self.playing = False
        self.last = bytes(frame_bytes)
        self.silence = bytes(frame_bytes)
        self.lock = threading.Lock()
        self.lost = 0
        self.late = 0
        self.concealed = 0
        self.played = 0
        self.dropped = 0

    def push(self, seq: int, pcm: bytes):
        with self.lock:
            if self.next_seq is not None and seq < self.next_seq:
                self.late += 1           # وصلت بعد وقت تشغيلها
                return
            self.frames[seq] = pcm
            if len(self.frames) > self.max_depth:          # تأخر كبير -> قفز للأمام
                drop = sorted(self.frames)[:len(self.frames) - self.target_depth]
                for s in drop:
                    del self.frames[s]
                self.next_seq = min(self.frames)

    def depth(self):
        with self.lock:
            return len(self.frames)

    def pop(self) -> bytes:
        with self.lock:
            if not self.playing:
                if len(self.frames) < self.target_depth:
                    return self.silence
                self.playing = True
                self.next_seq = min(self.frames)
            if not self.frames:
                # نفاد المخزن: إعادة التعبئة
                self.playing = False
                return self.silence
            # التحكم بالتأخير: إذا تراكمت الإطارات (اختلاف ساعتي كرتي الصوت) نتخطى إطاراً قديماً
            if len(self.frames) > self.target_depth + 4:
                oldest = min(self.frames)
                del self.frames[oldest]
                self.dropped += 1
                self.next_seq = min(self.frames)
            seq = self.next_seq
            self.next_seq += 1
            pcm = self.frames.pop(seq, None)
            if pcm is not None:
                self.last = pcm
                self.played += 1
                return pcm
            # إطار مفقود -> إخفاء الفقد (PLC)
            self.lost += 1
            self.concealed += 1
            faded = (np.frombuffer(self.last, dtype=np.int16) * 0.5).astype(np.int16).tobytes()
            self.last = faded
            return faded
