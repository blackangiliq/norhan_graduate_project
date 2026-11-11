"""
نافذة منع إعادة الإرسال (Anti-Replay Sliding Window) - نفس فكرة IPsec (RFC 4303) و DTLS.
تتذكر آخر 64 رقم تسلسل؛ أي حزمة مكررة أو أقدم من النافذة تُرفض.
"""


class ReplayWindow:
    def __init__(self, size: int = 64):
        self.size = size
        self.highest = 0      # أعلى رقم تسلسل مقبول
        self.bitmap = 0       # البت i = 1 يعني أن الحزمة (highest - i) استُلمت

    def check(self, seq: int) -> bool:
        """هل الحزمة جديدة؟ (بدون تعديل الحالة - يُستدعى قبل فك التشفير)"""
        if seq == 0:
            return False
        if seq > self.highest:
            return True
        offset = self.highest - seq
        if offset >= self.size:
            return False                       # قديمة جداً
        return not (self.bitmap >> offset) & 1  # مكررة؟

    def update(self, seq: int):
        """تسجيل الحزمة كمستلمة (يُستدعى فقط بعد نجاح التحقق من الوسم)."""
        if seq > self.highest:
            shift = seq - self.highest
            self.bitmap = ((self.bitmap << shift) | 1) & ((1 << self.size) - 1) if shift < self.size else 1
            self.highest = seq
        else:
            self.bitmap |= 1 << (self.highest - seq)
