"""
الواجهة الرسومية الرئيسية لنظام الاتصال الصوتي الآمن (PySide6 / Qt).
"""
import html
import time

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QIcon
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QFormLayout, QFrame,
                               QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QMainWindow, QMessageBox, QPushButton, QRadioButton, QScrollArea, QSpinBox,
                               QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit, QVBoxLayout, QWidget)

from .. import APP_NAME, __version__
from .. import benchmark
from ..audio.codec import CODECS
from ..audio.devices import TEST_TONE, audio_available, list_devices, make_backend
from ..crypto.ciphers import CIPHERS
from ..session import (CONNECTING, ENDED, HANDSHAKE, IDLE, IN_CALL, LISTENING, CallConfig, CallSession,
                       local_ip_addresses)
from .styles import STYLE
from .widgets import ACCENT, AMBER, GREEN, RED, VIOLET, BarChart, LevelMeter, LiveChart, StatCard

STATE_TEXT = {
    IDLE: ("● غير متصل", "#94a3b8"),
    LISTENING: ("● بانتظار مكالمة واردة...", AMBER),
    CONNECTING: ("● جاري الاتصال...", AMBER),
    HANDSHAKE: ("● تبادل المفاتيح والمصادقة...", VIOLET),
    IN_CALL: ("● مكالمة آمنة جارية 🔒", GREEN),
    ENDED: ("● انتهت المكالمة", "#94a3b8"),
}

CIPHER_LABELS = {
    1: "Ascon-128  (خفيف - NIST) ✔",
    2: "ChaCha20-Poly1305  (خفيف برمجياً)",
    3: "AES-128-GCM  (تقليدي - للمقارنة)",
}

LOG_COLORS = {"info": "#cbd5e1", "ok": GREEN, "warn": AMBER, "error": RED, "alert": RED}


class Bridge(QObject):
    """ينقل أحداث محرك المكالمة (من خيوط الخلفية) إلى خيط الواجهة بأمان."""
    event = Signal(str, object)


class BenchThread(QThread):
    progress = Signal(int, int)
    done = Signal(object)

    def run(self):
        rep = benchmark.run(iterations=200, progress=lambda i, n: self.progress.emit(i, n))
        self.done.emit(rep)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — نظام الاتصال الصوتي الآمن بالتشفير خفيف الوزن  v{__version__}")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(1360, 860)
        self.session = None
        self.bridge = Bridge()
        self.bridge.event.connect(self._on_event)
        self._prev = None
        self._seen_packets = 0
        self._call_start = None

        root = QWidget(); root.setObjectName("root")
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(14, 12, 14, 8)
        main.addLayout(self._header())

        body = QHBoxLayout()
        body.setSpacing(12)
        left = QScrollArea(); left.setWidgetResizable(True); left.setFrameShape(QFrame.NoFrame)
        left.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left.setFixedWidth(450)
        side = QWidget(); side.setObjectName("side"); sl = QVBoxLayout(side); sl.setContentsMargins(0, 0, 4, 0)
        sl.addWidget(self._settings_box())
        sl.addStretch()
        left.setWidget(side)
        body.addWidget(left)
        right = QVBoxLayout(); right.setSpacing(10)
        right.addWidget(self._status_box())
        right.addWidget(self._tabs(), 1)
        body.addLayout(right, 1)
        main.addLayout(body, 1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(500)
        self._refresh_devices()
        self._update_mode()
        self._set_state(IDLE)
        self.log("info", f"مرحباً بك في {APP_NAME}. عناوين جهازك: {', '.join(local_ip_addresses())}")
        if not audio_available():
            self.log("warn", "لم يتم العثور على أجهزة صوت - سيتم استخدام نغمة اختبار بدل الميكروفون")

    # ================================================================ layout
    def _header(self):
        h = QHBoxLayout()
        icon = QLabel("🔐"); icon.setStyleSheet("font-size:34px;")
        col = QVBoxLayout()
        t = QLabel("نظام الاتصال الصوتي الآمن المعتمد على خوارزميات التشفير خفيفة الوزن"); t.setObjectName("title")
        s = QLabel("Secure Voice Communication System Based on Lightweight Encryption Algorithms  •  "
                   "Ascon-128 • X25519 • HKDF • UDP/TCP")
        s.setObjectName("subtitle")
        col.addWidget(t); col.addWidget(s)
        h.addWidget(icon); h.addLayout(col, 1)
        ips = QLabel("عنوان IP لجهازك:  " + "  |  ".join(local_ip_addresses()))
        ips.setStyleSheet("background:#0f172a;border:1px solid #1f2937;border-radius:8px;padding:8px 12px;"
                          "color:#22d3ee;font-weight:bold;")
        ips.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.ip_label = ips
        h.addWidget(ips)
        return h

    def _settings_box(self):
        g = QGroupBox("إعدادات الاتصال")
        f = QFormLayout(g)
        f.setLabelAlignment(Qt.AlignRight)
        f.setVerticalSpacing(9)

        self.rb_listen = QRadioButton("استقبال مكالمة (الجهاز A)")
        self.rb_call = QRadioButton("إجراء مكالمة (الجهاز B)")
        self.rb_listen.setChecked(True)
        grp = QButtonGroup(self); grp.addButton(self.rb_listen); grp.addButton(self.rb_call)
        self.rb_listen.toggled.connect(self._update_mode)
        mode = QVBoxLayout(); mode.addWidget(self.rb_listen); mode.addWidget(self.rb_call)
        f.addRow("الوضع:", mode)

        self.peer_ip = QLineEdit(); self.peer_ip.setPlaceholderText("مثال: 192.168.1.10")
        self.peer_ip.setLayoutDirection(Qt.LeftToRight)
        f.addRow("IP الطرف الآخر:", self.peer_ip)

        pw = QHBoxLayout()
        self.password = QLineEdit("graduation2026"); self.password.setEchoMode(QLineEdit.Password)
        self.password.setLayoutDirection(Qt.LeftToRight)
        show = QPushButton("👁"); show.setFixedWidth(40); show.setCheckable(True)
        show.toggled.connect(lambda on: self.password.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password))
        pw.addWidget(self.password); pw.addWidget(show)
        f.addRow("كلمة السر المشتركة:", pw)

        self.cipher = QComboBox()
        for cid in CIPHERS:
            self.cipher.addItem(CIPHER_LABELS[cid], cid)
        f.addRow("خوارزمية التشفير:", self.cipher)
        self.cipher_note = QLabel("في وضع الاستقبال يتم اعتماد الخوارزمية التي يختارها المتصل تلقائياً")
        self.cipher_note.setObjectName("muted"); self.cipher_note.setWordWrap(True)
        f.addRow("", self.cipher_note)

        self.codec = QComboBox()
        self.codec.addItem("PCM 16-bit  (256 kbps)", 1)
        self.codec.addItem("G.711 μ-law  (128 kbps)", 2)
        f.addRow("ترميز الصوت:", self.codec)

        self.mic = QComboBox(); self.spk = QComboBox()
        f.addRow("الميكروفون:", self.mic)
        f.addRow("السماعة:", self.spk)
        ref = QPushButton("🔄 تحديث قائمة الأجهزة"); ref.clicked.connect(self._refresh_devices)
        f.addRow("", ref)

        ports = QHBoxLayout()
        self.tcp_port = QSpinBox(); self.tcp_port.setRange(1024, 65535); self.tcp_port.setValue(5000)
        self.udp_port = QSpinBox(); self.udp_port.setRange(1024, 65535); self.udp_port.setValue(5001)
        ports.addWidget(QLabel("TCP")); ports.addWidget(self.tcp_port)
        ports.addWidget(QLabel("UDP")); ports.addWidget(self.udp_port)
        f.addRow("المنافذ:", ports)

        btns = QHBoxLayout()
        self.btn_start = QPushButton("📞 بدء الاستقبال"); self.btn_start.setObjectName("start")
        self.btn_start.clicked.connect(self._start)
        self.btn_hang = QPushButton("⛔ إنهاء"); self.btn_hang.setObjectName("hangup")
        self.btn_hang.clicked.connect(self._hangup)
        btns.addWidget(self.btn_start, 2); btns.addWidget(self.btn_hang, 1)
        f.addRow(btns)
        self.cb_mute = QCheckBox("🔇 كتم الميكروفون")
        self.cb_mute.toggled.connect(lambda on: self.session and self.session.set_mute(on))
        f.addRow("", self.cb_mute)
        return g

    def _status_box(self):
        g = QGroupBox("حالة المكالمة")
        h = QHBoxLayout(g)
        h.setSpacing(18)
        c1 = QVBoxLayout()
        self.state_lbl = QLabel(); self.state_lbl.setObjectName("state")
        self.timer_lbl = QLabel("00:00"); self.timer_lbl.setObjectName("timer"); self.timer_lbl.setAlignment(Qt.AlignCenter)
        c1.addWidget(self.state_lbl); c1.addWidget(self.timer_lbl)
        h.addLayout(c1)
        grid = QGridLayout(); grid.setVerticalSpacing(3)
        self.info_lbls = {}
        for i, (k, t) in enumerate([("peer", "الطرف الآخر"), ("cipher", "الخوارزمية"), ("codec", "الترميز"),
                                    ("handshake", "زمن المصافحة"), ("fingerprint", "بصمة الجلسة")]):
            a = QLabel(t + ":"); a.setObjectName("muted")
            b = QLabel("—"); b.setTextInteractionFlags(Qt.TextSelectableByMouse)
            grid.addWidget(a, i, 0); grid.addWidget(b, i, 1)
            self.info_lbls[k] = b
        h.addLayout(grid, 1)
        c3 = QVBoxLayout()
        sas_t = QLabel("رمز الأمان SAS (يجب أن يتطابق على الجهازين)"); sas_t.setObjectName("muted")
        sas_t.setAlignment(Qt.AlignCenter)
        self.sas_lbl = QLabel("--- ---"); self.sas_lbl.setObjectName("sas"); self.sas_lbl.setAlignment(Qt.AlignCenter)
        c3.addWidget(sas_t); c3.addWidget(self.sas_lbl)
        h.addLayout(c3, 1)
        c4 = QVBoxLayout()
        self.mic_meter = LevelMeter("🎤 الميكروفون")
        self.spk_meter = LevelMeter("🔊 السماعة")
        self.mic_meter.setMinimumWidth(220)
        c4.addWidget(self.mic_meter); c4.addWidget(self.spk_meter)
        h.addLayout(c4, 1)
        return g

    def _tabs(self):
        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_monitor(), "📊 لوحة المراقبة")
        self.tabs.addTab(self._tab_packets(), "📦 فاحص الحزم")
        self.tabs.addTab(self._tab_attacks(), "🛡 محاكاة الهجمات")
        self.tabs.addTab(self._tab_chat(), "💬 رسائل مشفرة")
        self.tabs.addTab(self._tab_bench(), "⚡ مقارنة الخوارزميات")
        self.tabs.addTab(self._tab_log(), "📜 سجل الأحداث")
        self.tabs.addTab(self._tab_about(), "ℹ حول النظام")
        return self.tabs

    def _tab_monitor(self):
        w = QWidget(); v = QVBoxLayout(w)
        grid = QGridLayout(); grid.setSpacing(8)
        defs = [("tx", "حزم مرسلة", "packet", ACCENT), ("rx", "حزم مستقبلة", "packet", ACCENT),
                ("up", "معدل الإرسال", "kbit/s", GREEN), ("down", "معدل الاستقبال", "kbit/s", GREEN),
                ("enc", "زمن التشفير / إطار", "µs", VIOLET), ("dec", "زمن فك التشفير / إطار", "µs", VIOLET),
                ("rtt", "زمن الرحلة RTT", "ms", AMBER), ("jit", "الارتعاش Jitter", "ms", AMBER),
                ("lost", "حزم مفقودة", "packet", AMBER), ("auth", "حزم مرفوضة (تزوير/تعديل)", "packet", RED),
                ("replay", "هجمات إعادة إرسال محجوبة", "packet", RED), ("buf", "عمق مخزن الارتعاش", "frame × 20ms", ACCENT)]
        self.cards = {}
        for i, (k, t, u, c) in enumerate(defs):
            card = StatCard(t, u, c)
            self.cards[k] = card
            grid.addWidget(card, i // 4, i % 4)
        v.addLayout(grid)
        self.chart_rate = LiveChart("Bitrate", [("Upload", GREEN), ("Download", ACCENT)], unit="kbit/s")
        self.chart_crypto = LiveChart("Crypto time per frame", [("Encrypt", VIOLET), ("Decrypt", AMBER)], unit="µs")
        v.addWidget(self.chart_rate, 1)
        v.addWidget(self.chart_crypto, 1)
        return w

    def _tab_packets(self):
        w = QWidget(); v = QVBoxLayout(w)
        info = QLabel(
            "بنية حزمة الصوت عبر UDP:   [ الإصدار 1B | النوع 1B | رقم التسلسل 4B | رقم الإطار 4B ]  ←  ترويسة موثّقة غير مشفرة (AD)"
            "   +   [ الصوت المشفّر ]   +   [ الوسم Tag 16B ]   (الحجم بالبايت)\n"
            "Nonce = IV (سري، مشتق من المفتاح)  XOR  رقم التسلسل  — لا يُرسل على الشبكة. تُعرض عينة كل 10 حزم + كل حزمة مرفوضة.")
        info.setWordWrap(True); info.setObjectName("muted")
        v.addWidget(info)
        self.tbl = QTableWidget(0, 10)
        self.tbl.setHorizontalHeaderLabels(["الوقت", "الاتجاه", "التسلسل", "النوع", "الحجم", "الحالة",
                                            "النص الأصلي (hex)", "النص المشفر (hex)", "الوسم Tag", "Nonce"])
        self.tbl.setLayoutDirection(Qt.LeftToRight)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        hh = self.tbl.horizontalHeader()
        for i in range(10):
            hh.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        hh.setStretchLastSection(True)
        v.addWidget(self.tbl, 1)
        bar = QHBoxLayout()
        self.cb_rejected = QCheckBox("عرض الحزم المرفوضة فقط (الهجمات)")
        self.cb_rejected.toggled.connect(self._filter_packets)
        clr = QPushButton("مسح الجدول"); clr.clicked.connect(lambda: self.tbl.setRowCount(0))
        bar.addWidget(self.cb_rejected); bar.addStretch(); bar.addWidget(clr)
        v.addLayout(bar)
        return w

    def _tab_attacks(self):
        w = QWidget(); v = QVBoxLayout(w)
        intro = QLabel("هذه الأدوات ترسل حزماً هجومية حقيقية إلى الجهاز الآخر أثناء المكالمة لإثبات أن النظام يكتشفها ويرفضها. "
                       "راقب «سجل الأحداث» و«فاحص الحزم» وعدادات الرفض على الجهاز الآخر.")
        intro.setWordWrap(True); intro.setObjectName("muted")
        v.addWidget(intro)
        attacks = [
            ("tamper", "① هجوم التعديل (Tampering / Bit-flipping)",
             "يلتقط حزمة صوت ويقلب بتاً واحداً فقط في النص المشفر ثم يرسلها. → وسم المصادقة لن يتطابق فترفض الحزمة."),
            ("forge", "② هجوم التزوير (Forgery بمفتاح خاطئ)",
             "مهاجم لا يعرف مفتاح الجلسة يصنع حزمة صوت مزيفة بمفتاح عشوائي. → فشل التحقق والرفض."),
            ("replay", "③ هجوم إعادة الإرسال (Replay Attack)",
             "يعيد إرسال 10 حزم قديمة صحيحة تماماً تم التقاطها سابقاً. → نافذة منع التكرار ترفضها."),
        ]
        for key, title, desc in attacks:
            b = QPushButton(f"{title}\n{desc}"); b.setObjectName("attack")
            b.setMinimumHeight(64)
            b.clicked.connect(lambda _=False, k=key: self._attack(k))
            v.addWidget(b)
        eav = QGroupBox("④ وضع المتنصت (Eavesdropper)")
        ev = QVBoxLayout(eav)
        self.cb_eav = QCheckBox("تشغيل الحزم المشفرة كما هي في السماعة (ما يسمعه من يلتقط الحزم بدون المفتاح)")
        self.cb_eav.toggled.connect(self._toggle_eav)
        ev.addWidget(self.cb_eav)
        n = QLabel("عند التفعيل ستسمع ضجيجاً عشوائياً فقط بدل صوت الطرف الآخر — وهذا بالضبط ما يحصل عليه "
                   "المتنصت باستخدام Wireshark. ألغِ التفعيل لتعود للصوت الواضح.")
        n.setWordWrap(True); n.setObjectName("muted")
        ev.addWidget(n)
        v.addWidget(eav)
        mitm = QGroupBox("⑤ هجوم رجل في المنتصف / كلمة سر خاطئة")
        mv = QVBoxLayout(mitm)
        m = QLabel("أنهِ المكالمة ثم غيّر كلمة السر في أحد الجهازين وحاول الاتصال: ستفشل المصافحة فوراً "
                   "(Finished MAC لا يتطابق) ولن يتم إنشاء أي مفتاح أو إرسال أي صوت.")
        m.setWordWrap(True); m.setObjectName("muted")
        mv.addWidget(m)
        v.addWidget(mitm)
        v.addStretch()
        return w

    def _tab_chat(self):
        w = QWidget(); v = QVBoxLayout(w)
        n = QLabel("الرسائل النصية تُرسل عبر قناة التحكم TCP مشفرة بنفس خوارزمية الجلسة وبمفتاح منفصل.")
        n.setObjectName("muted"); v.addWidget(n)
        self.chat_view = QTextEdit(); self.chat_view.setReadOnly(True)
        v.addWidget(self.chat_view, 1)
        h = QHBoxLayout()
        self.chat_in = QLineEdit(); self.chat_in.setPlaceholderText("اكتب رسالة...")
        self.chat_in.returnPressed.connect(self._send_chat)
        b = QPushButton("إرسال 🔒"); b.clicked.connect(self._send_chat)
        h.addWidget(self.chat_in, 1); h.addWidget(b)
        v.addLayout(h)
        return w

    def _tab_bench(self):
        w = QWidget(); v = QVBoxLayout(w)
        top = QHBoxLayout()
        self.btn_bench = QPushButton("▶ تشغيل المقارنة"); self.btn_bench.clicked.connect(self._run_bench)
        self.bench_status = QLabel("تقيس زمن تشفير وفك تشفير إطار صوتي حقيقي الحجم لكل خوارزمية على هذا الجهاز")
        self.bench_status.setObjectName("muted")
        top.addWidget(self.btn_bench); top.addWidget(self.bench_status, 1)
        v.addLayout(top)
        self.bench_tbl = QTableWidget(0, 8)
        self.bench_tbl.setHorizontalHeaderLabels(["الخوارزمية", "حجم الإطار (بايت)", "تشفير µs", "فك µs", "Mbit/s",
                                                  "إضافي (بايت)", "% من 20ms", "المفتاح/Nonce"])
        self.bench_tbl.verticalHeader().setVisible(False)
        self.bench_tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.bench_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.bench_tbl.setMinimumHeight(250)
        self.bench_tbl.setMaximumHeight(260)
        v.addWidget(self.bench_tbl)
        self.bench_chart = BarChart("Encryption time per 640-byte voice frame (µs, log scale)")
        v.addWidget(self.bench_chart, 1)
        note = QLabel("ملاحظة: Ascon-128 هنا مكتوب بالكامل بلغة Python داخل المشروع (لأغراض تعليمية وشفافية)، بينما AES و ChaCha20 "
                      "مكتوبتان بلغة C مع تسريع العتاد (AES-NI). ميزة Ascon الحقيقية تظهر في العتاد والمعالجات الصغيرة. "
                      "المهم أن زمن Ascon أقل بكثير من 20ms المتاحة لكل إطار ← مناسب للاتصال الآني.")
        note.setWordWrap(True); note.setObjectName("muted")
        v.addWidget(note)
        return w

    def _tab_log(self):
        w = QWidget(); v = QVBoxLayout(w)
        self.log_view = QTextEdit(); self.log_view.setReadOnly(True)
        v.addWidget(self.log_view)
        return w

    def _tab_about(self):
        w = QWidget(); v = QVBoxLayout(w)
        t = QTextEdit(); t.setReadOnly(True)
        t.setHtml("""
<h2 style='color:#22d3ee'>كيف يعمل النظام؟</h2>
<ol>
<li><b>الاتصال:</b> الجهاز B يفتح اتصال TCP بالجهاز A على المنفذ 5000 (قناة التحكم).</li>
<li><b>المصافحة:</b> يتبادل الجهازان مفاتيح عامة مؤقتة <b>X25519</b> ويحسبان سراً مشتركاً دون إرساله.</li>
<li><b>اشتقاق المفاتيح:</b> PBKDF2(كلمة السر) + HKDF-SHA256 ← مفتاح لكل اتجاه + IV + مفتاح تحكم + رمز أمان.</li>
<li><b>المصادقة:</b> يرسل كل طرف HMAC يثبت معرفته بكلمة السر؛ أي اختلاف = رفض (حماية من رجل في المنتصف).</li>
<li><b>الصوت:</b> الميكروفون ← إطارات 20ms (320 عينة @16kHz) ← ترميز ← تشفير <b>Ascon-128</b> ← UDP منفذ 5001.</li>
<li><b>الاستقبال:</b> فحص التكرار ← التحقق من الوسم وفك التشفير ← مخزن الارتعاش ← السماعة.</li>
</ol>
<h3 style='color:#22d3ee'>الخصائص الأمنية</h3>
<ul>
<li>السرية Confidentiality: التشفير بـ Ascon-128 / ChaCha20 / AES-GCM.</li>
<li>السلامة والأصالة Integrity &amp; Authenticity: وسم 128 بت لكل حزمة (AEAD).</li>
<li>منع إعادة الإرسال: نافذة انزلاقية 64 حزمة.</li>
<li>السرية الأمامية Forward Secrecy: مفاتيح جديدة لكل مكالمة.</li>
<li>المصادقة المتبادلة بكلمة سر مشتركة + رمز أمان SAS للتحقق الصوتي.</li>
</ul>
<p style='color:#94a3b8'>مشروع تخرج — Secure Voice Communication System Based on Lightweight Encryption Algorithms</p>
""")
        v.addWidget(t)
        return w

    # ================================================================ actions
    def _update_mode(self):
        listen = self.rb_listen.isChecked()
        self.peer_ip.setEnabled(not listen)
        self.cipher_note.setVisible(listen)
        self.btn_start.setText("📞 بدء الاستقبال" if listen else "📞 اتصال")

    def _refresh_devices(self):
        ins, outs, din, dout = list_devices()
        self.mic.clear(); self.spk.clear()
        self.mic.addItem("الافتراضي (Default)", None)
        for i, n in ins:
            self.mic.addItem(n, i)
        self.mic.addItem("🎵 نغمة اختبار (بدون ميكروفون)", TEST_TONE)
        self.spk.addItem("الافتراضي (Default)", None)
        for i, n in outs:
            self.spk.addItem(n, i)
        if not ins:
            self.mic.setCurrentIndex(self.mic.count() - 1)

    def _config(self):
        return CallConfig(password=self.password.text(), cipher_id=self.cipher.currentData(),
                          codec_id=self.codec.currentData(), tcp_port=self.tcp_port.value(),
                          udp_port=self.udp_port.value(), input_device=self.mic.currentData(),
                          output_device=self.spk.currentData())

    def _start(self):
        if self.session and self.session.state not in (IDLE, ENDED):
            return
        if not self.password.text():
            QMessageBox.warning(self, APP_NAME, "يجب إدخال كلمة السر المشتركة")
            return
        cfg = self._config()
        if self.rb_call.isChecked() and not self.peer_ip.text().strip():
            QMessageBox.warning(self, APP_NAME, "أدخل عنوان IP للجهاز الآخر (يظهر أعلى الشاشة في ذلك الجهاز)")
            return
        self.session = CallSession(cfg, lambda c: make_backend(c.input_device, c.output_device),
                                   lambda k, d: self.bridge.event.emit(k, d))
        self._prev = None
        self._seen_packets = 0
        self.chart_rate.clear(); self.chart_crypto.clear()
        self.cb_mute.setChecked(False); self.cb_eav.setChecked(False)
        self.timer_lbl.setText("00:00")
        if self.rb_listen.isChecked():
            self.session.start_listen()
        else:
            self.session.start_call(self.peer_ip.text().strip())

    def _hangup(self):
        if self.session:
            self.session.hangup()

    def _attack(self, kind):
        if not self.session or self.session.state != IN_CALL:
            QMessageBox.information(self, APP_NAME, "يجب أن تكون في مكالمة جارية لتنفيذ محاكاة الهجوم")
            return
        self.session.simulate_attack(kind)
        self.tabs.setCurrentIndex(5)

    def _toggle_eav(self, on):
        if self.session:
            self.session.eavesdrop = on
        self.log("warn" if on else "info", "وضع المتنصت مفعّل: تسمع الآن النص المشفر (ضجيج)" if on
                 else "تم إيقاف وضع المتنصت: عودة للصوت المفكوك")

    def _send_chat(self):
        text = self.chat_in.text().strip()
        if not text:
            return
        if not self.session or self.session.state != IN_CALL:
            QMessageBox.information(self, APP_NAME, "يجب أن تكون في مكالمة لإرسال رسائل")
            return
        self.session.send_chat(text)
        self._chat_line("أنا", text, GREEN)
        self.chat_in.clear()

    def _chat_line(self, who, text, color):
        self.chat_view.append(f"<p><span style='color:#64748b'>{time.strftime('%H:%M:%S')}</span> "
                              f"<b style='color:{color}'>{who}:</b> {html.escape(text)}</p>")

    def _run_bench(self):
        self.btn_bench.setEnabled(False)
        self.bench_status.setText("جاري القياس...")
        self.bt = BenchThread()
        self.bt.progress.connect(lambda i, n: self.bench_status.setText(f"جاري القياس... {i}/{n}"))
        self.bt.done.connect(self._bench_done)
        self.bt.start()

    def _bench_done(self, rep):
        self.btn_bench.setEnabled(True)
        self.bench_status.setText(f"المنصة: {rep['platform']}  |  Python {rep['python']}  |  {rep['iterations']} تكرار")
        self.show_bench(rep)

    def show_bench(self, rep):
        res = rep["results"]
        self.bench_tbl.setRowCount(len(res))
        for r, x in enumerate(res):
            vals = [x["cipher"], str(x["frame_bytes"]), f"{x['enc_us']:.1f}", f"{x['dec_us']:.1f}",
                    f"{x['throughput_mbps']:.2f}", str(x["overhead_bytes"]), f"{x['frame_budget_pct']:.2f}%",
                    f"{x['key_bits']}/{x['nonce_bits']}"]
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val); it.setTextAlignment(Qt.AlignCenter)
                self.bench_tbl.setItem(r, c, it)
        colors = {"Ascon-128": GREEN, "ChaCha20-Poly1305": ACCENT, "AES-128-GCM": AMBER}
        items = [(x["cipher"], x["enc_us"], colors[x["cipher"]], f"{x['enc_us']:.1f} µs")
                 for x in res if x["frame_bytes"] == 640]
        self.bench_chart.set_items(items)

    # ================================================================ events
    def log(self, level, msg):
        color = LOG_COLORS.get(level, "#cbd5e1")
        self.log_view.append(f"<span style='color:#64748b'>{time.strftime('%H:%M:%S')}</span> "
                             f"<span style='color:{color}'>{html.escape(msg)}</span>")
        self.statusBar().showMessage(msg, 6000)

    def _on_event(self, kind, data):
        if kind == "state":
            self._set_state(data)
        elif kind == "log":
            self.log(*data)
        elif kind == "connected":
            self._call_start = time.time()
            self.info_lbls["peer"].setText(f"{data['peer']}  (UDP {data['peer_udp']})")
            self.info_lbls["cipher"].setText(data["cipher"])
            self.info_lbls["codec"].setText(data["codec"])
            self.info_lbls["handshake"].setText(f"{data['handshake_ms']:.0f} ms")
            self.info_lbls["fingerprint"].setText(data["fingerprint"])
            self.sas_lbl.setText(data["sas"].replace("-", " "))
            idx = self.cipher.findData(next(k for k, c in CIPHERS.items() if c.name == data["cipher"]))
            self.cipher.setCurrentIndex(idx)
        elif kind == "chat":
            self._chat_line("الطرف الآخر", data, ACCENT)
            self.tabs.setTabText(3, "💬 رسائل مشفرة •")
        elif kind == "alert":
            self.statusBar().setStyleSheet("color:#f87171;font-weight:bold;")
            self.statusBar().showMessage(data, 5000)
            QTimer.singleShot(5000, lambda: self.statusBar().setStyleSheet(""))
        elif kind == "error":
            QMessageBox.critical(self, APP_NAME, data)
        elif kind == "ended":
            self._call_start = None
            self.mic_meter.set_db(-90); self.spk_meter.set_db(-90)

    def _set_state(self, st):
        text, color = STATE_TEXT.get(st, (st, "#94a3b8"))
        self.state_lbl.setText(text)
        self.state_lbl.setStyleSheet(f"color:{color};")
        busy = st in (LISTENING, CONNECTING, HANDSHAKE, IN_CALL)
        self.btn_start.setEnabled(not busy)
        self.btn_hang.setEnabled(busy)
        for wdg in (self.rb_listen, self.rb_call, self.peer_ip, self.password, self.cipher, self.codec,
                    self.mic, self.spk, self.tcp_port, self.udp_port):
            wdg.setEnabled(not busy)
        if not busy:
            self._update_mode()
        if st in (IDLE, LISTENING, CONNECTING):
            self.sas_lbl.setText("--- ---")
            for b in self.info_lbls.values():
                b.setText("—")

    def _tick(self):
        if self.tabs.tabText(3).endswith("•") and self.tabs.currentIndex() == 3:
            self.tabs.setTabText(3, "💬 رسائل مشفرة")
        if not self.session:
            return
        s = self.session.snapshot()
        if self._call_start:
            d = int(time.time() - self._call_start)
            self.timer_lbl.setText(f"{d // 60:02d}:{d % 60:02d}")
        if s["state"] != IN_CALL:
            return
        now = time.time()
        up = down = 0.0
        if self._prev:
            dt = now - self._prev[0]
            up = (s["tx_bytes"] - self._prev[1]) * 8 / dt / 1000
            down = (s["rx_bytes"] - self._prev[2]) * 8 / dt / 1000
        self._prev = (now, s["tx_bytes"], s["rx_bytes"])
        c = self.cards
        c["tx"].set(s["tx_packets"]); c["rx"].set(s["rx_packets"])
        c["up"].set(f"{up:.1f}"); c["down"].set(f"{down:.1f}")
        c["enc"].set(f"{s['enc_us']:.0f}"); c["dec"].set(f"{s['dec_us']:.0f}")
        c["rtt"].set(f"{s['rtt_ms']:.1f}"); c["jit"].set(f"{s['jitter_ms']:.1f}")
        c["lost"].set(s["lost"]); c["auth"].set(s["auth_failures"]); c["replay"].set(s["replays_blocked"])
        c["buf"].set(s["jitter_depth"])
        self.chart_rate.add(Upload=up, Download=down)
        self.chart_crypto.add(Encrypt=s["enc_us"], Decrypt=s["dec_us"])
        self.mic_meter.set_db(-90 if s["muted"] else s["mic_db"])
        self.spk_meter.set_db(s["spk_db"])
        self._update_packets()

    def _update_packets(self):
        pkts = list(self.session.packets)
        new = pkts[max(0, len(pkts) - 30):] if self._seen_packets == 0 else \
            [p for p in pkts if id(p) not in self._seen_ids]
        self._seen_ids = {id(p) for p in pkts}
        self._seen_packets += len(new)
        for p in new:
            self.tbl.insertRow(0)
            vals = [p["time"], p["dir"], str(p["seq"]), p["type"], str(p["size"]), p["status"], p["plain"],
                    p["cipher"], p["tag"][:16] + "…", p["nonce"][:12] + "…" if p["nonce"] != "—" else "—"]
            color = None if p["status"] == "OK" else QColor("#7f1d1d")
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if color:
                    it.setBackground(color)
                if c == 1:
                    it.setForeground(QColor(GREEN if val == "TX" else ACCENT))
                if c == 5:
                    it.setForeground(QColor(GREEN if val == "OK" else "#fecaca"))
                if c == 7:
                    it.setForeground(QColor(AMBER))
                self.tbl.setItem(0, c, it)
            if self.cb_rejected.isChecked() and p["status"] == "OK":
                self.tbl.setRowHidden(0, True)
        while self.tbl.rowCount() > 300:
            self.tbl.removeRow(self.tbl.rowCount() - 1)

    _seen_ids = set()

    def _filter_packets(self, only_rejected):
        for r in range(self.tbl.rowCount()):
            it = self.tbl.item(r, 5)
            self.tbl.setRowHidden(r, bool(only_rejected and it and it.text() == "OK"))

    def closeEvent(self, e):
        if self.session and self.session.state in (LISTENING, CONNECTING, HANDSHAKE, IN_CALL):
            self.session.hangup("window closed")
        e.accept()


def run():
    import sys
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setLayoutDirection(Qt.RightToLeft)
    f = QFont()
    f.setFamilies(["Segoe UI", "Tahoma", "Noto Sans Arabic", "Noto Sans", "DejaVu Sans"])
    f.setPointSize(10)
    app.setFont(f)
    app.setStyleSheet(STYLE)
    import os
    icon = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "assets", "icon.png")
    if hasattr(sys, "_MEIPASS"):
        icon = os.path.join(sys._MEIPASS, "assets", "icon.png")
    if os.path.exists(icon):
        app.setWindowIcon(QIcon(icon))
    w = MainWindow()
    w.show()
    return app.exec()
