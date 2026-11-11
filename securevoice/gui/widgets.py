"""عناصر واجهة مخصصة: رسم بياني حي، رسم أعمدة، بطاقات إحصائية، مؤشر مستوى الصوت."""
import collections

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

ACCENT = "#22d3ee"
GREEN = "#34d399"
RED = "#f87171"
AMBER = "#fbbf24"
VIOLET = "#a78bfa"
TEXT = "#e5e7eb"
MUTED = "#94a3b8"
CARD = "#111827"
BORDER = "#1f2937"


class StatCard(QFrame):
    def __init__(self, title, unit="", color=ACCENT):
        super().__init__()
        self.setObjectName("statCard")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)
        self.t = QLabel(title); self.t.setObjectName("statTitle")
        self.v = QLabel("—"); self.v.setObjectName("statValue")
        self.v.setStyleSheet(f"color:{color};")
        self.u = QLabel(unit); self.u.setObjectName("statUnit")
        for w in (self.t, self.v, self.u):
            lay.addWidget(w)

    def set(self, text):
        self.v.setText(str(text))


class LevelMeter(QWidget):
    """مؤشر مستوى الصوت بالديسيبل."""

    def __init__(self, label):
        super().__init__()
        self.label = label
        self.db = -90.0
        self.setMinimumHeight(26)
        self.setLayoutDirection(Qt.LeftToRight)

    def set_db(self, db):
        self.db = db
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setLayoutDirection(Qt.LeftToRight)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(0, 0, -1, -1)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(BORDER))
        p.drawRoundedRect(r, 6, 6)
        frac = max(0.0, min(1.0, (self.db + 60) / 60))
        w = r.width() * frac
        color = GREEN if self.db < -12 else (AMBER if self.db < -4 else RED)
        p.setBrush(QColor(color))
        # يملأ من اليسار دائماً (القياس رقمي)
        p.drawRoundedRect(QRectF(r.left(), r.top(), w, r.height()), 6, 6)
        p.setPen(QColor(TEXT))
        p.setFont(QFont(self.font().family(), 9))
        p.drawText(r.adjusted(8, 0, -8, 0), Qt.AlignVCenter | Qt.AlignRight | Qt.AlignAbsolute, self.label)
        p.drawText(r.adjusted(8, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft | Qt.AlignAbsolute, f"{self.db:.0f} dB")


class LiveChart(QWidget):
    """رسم بياني خطي حي لعدة سلاسل بيانات."""

    def __init__(self, title, series, points=120, unit=""):
        super().__init__()
        self.title = title
        self.unit = unit
        self.series = {name: (color, collections.deque([0.0] * points, maxlen=points)) for name, color in series}
        self.setMinimumHeight(200)
        self.setLayoutDirection(Qt.LeftToRight)

    def add(self, **values):
        for k, v in values.items():
            if k in self.series:
                self.series[k][1].append(float(v))
        self.update()

    def clear(self):
        for _, d in self.series.values():
            for i in range(len(d)):
                d[i] = 0.0
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setLayoutDirection(Qt.LeftToRight)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(CARD))
        m_l, m_r, m_t, m_b = 52, 12, 30, 22
        plot = QRectF(m_l, m_t, self.width() - m_l - m_r, self.height() - m_t - m_b)
        vmax = max([max(d) for _, d in self.series.values()] + [1e-9]) * 1.15
        p.setFont(QFont(self.font().family(), 8))
        for i in range(5):
            y = plot.bottom() - plot.height() * i / 4
            p.setPen(QPen(QColor(BORDER), 1))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(QColor(MUTED))
            p.drawText(QRectF(0, y - 8, m_l - 6, 16), Qt.AlignRight | Qt.AlignAbsolute | Qt.AlignVCenter, f"{vmax * i / 4:.0f}")
        p.setPen(QColor(TEXT))
        p.setFont(QFont(self.font().family(), 10, QFont.Bold))
        p.drawText(QRectF(m_l, 4, plot.width(), 22), Qt.AlignLeft | Qt.AlignAbsolute | Qt.AlignVCenter, f"{self.title}  ({self.unit})")
        lx = plot.right()
        p.setFont(QFont(self.font().family(), 9))
        for name, (color, data) in reversed(list(self.series.items())):
            n = len(data)
            path = QPainterPath()
            for i, v in enumerate(data):
                pt = QPointF(plot.left() + plot.width() * i / (n - 1), plot.bottom() - plot.height() * v / vmax)
                path.moveTo(pt) if i == 0 else path.lineTo(pt)
            p.setPen(QPen(QColor(color), 2))
            p.drawPath(path)
            tw = p.fontMetrics().horizontalAdvance(name) + 24
            lx -= tw
            p.fillRect(QRectF(lx, 10, 10, 10), QColor(color))
            p.setPen(QColor(TEXT))
            p.drawText(QPointF(lx + 14, 19), name)


class BarChart(QWidget):
    """رسم أعمدة أفقية لمقارنة الخوارزميات (مقياس لوغاريتمي اختياري)."""

    def __init__(self, title=""):
        super().__init__()
        self.title = title
        self.items = []      # (label, value, color, text)
        self.log = True
        self.setMinimumHeight(220)
        self.setLayoutDirection(Qt.LeftToRight)

    def set_items(self, items, title=None):
        self.items = items
        if title:
            self.title = title
        self.update()

    def paintEvent(self, e):
        import math
        p = QPainter(self)
        p.setLayoutDirection(Qt.LeftToRight)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(CARD))
        p.setPen(QColor(TEXT))
        p.setFont(QFont(self.font().family(), 10, QFont.Bold))
        p.drawText(QRectF(12, 4, self.width() - 24, 24), Qt.AlignLeft | Qt.AlignAbsolute | Qt.AlignVCenter, self.title)
        if not self.items:
            p.setPen(QColor(MUTED))
            p.drawText(self.rect(), Qt.AlignCenter, "اضغط «تشغيل المقارنة» لعرض النتائج")
            return
        label_w = 190
        top = 36
        h = (self.height() - top - 10) / len(self.items)
        vals = [v for _, v, _, _ in self.items]
        f = (lambda v: math.log10(max(v, 0.1)) + 1) if self.log else (lambda v: v)
        vmax = max(f(v) for v in vals) or 1
        p.setFont(QFont(self.font().family(), 9))
        for i, (label, v, color, text) in enumerate(self.items):
            y = top + i * h
            p.setPen(QColor(TEXT))
            p.drawText(QRectF(8, y, label_w - 12, h), Qt.AlignRight | Qt.AlignAbsolute | Qt.AlignVCenter, label)
            w = (self.width() - label_w - 110) * f(v) / vmax
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(color))
            p.drawRoundedRect(QRectF(label_w, y + h * 0.18, max(w, 2), h * 0.64), 4, 4)
            p.setPen(QColor(TEXT))
            p.drawText(QRectF(label_w + w + 8, y, 110, h), Qt.AlignLeft | Qt.AlignAbsolute | Qt.AlignVCenter, text)
