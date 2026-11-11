"""
يلتقط صوراً حقيقية للبرنامج أثناء مكالمة فعلية بين نافذتين على نفس الجهاز (127.0.0.1).
python tools/screenshots.py  [مجلد الإخراج]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PySide6.QtCore import QTimer, Qt                        # noqa: E402
from PySide6.QtGui import QFont                               # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox       # noqa: E402

from securevoice import benchmark                             # noqa: E402
from securevoice.audio.devices import TEST_TONE               # noqa: E402
from securevoice.gui import main_window as mw                 # noqa: E402
from securevoice.gui.styles import STYLE                      # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/images"
os.makedirs(OUT, exist_ok=True)
QMessageBox.critical = staticmethod(lambda *a, **k: None)
QMessageBox.warning = staticmethod(lambda *a, **k: None)
mw.local_ip_addresses = lambda: ["192.168.1.10"]

app = QApplication(sys.argv)
app.setLayoutDirection(Qt.RightToLeft)
f = QFont(); f.setFamilies(["Segoe UI", "Noto Sans Arabic", "Noto Sans", "DejaVu Sans"]); f.setPointSize(10)
app.setFont(f)
app.setStyleSheet(STYLE)

A = mw.MainWindow(); A.setWindowTitle(A.windowTitle() + "  [Device A]")
mw.local_ip_addresses = lambda: ["192.168.1.20"]
B = mw.MainWindow(); B.setWindowTitle(B.windowTitle() + "  [Device B]")
for w in (A, B):
    w.resize(1440, 900)
    w.show()
    w.mic.setCurrentIndex(w.mic.findData(TEST_TONE))
B.rb_call.setChecked(True)
B.peer_ip.setText("127.0.0.1")
B.udp_port.setValue(5002)
B.tcp_port.setValue(5000)


def shot(win, name, tab=None):
    if tab is not None:
        win.tabs.setCurrentIndex(tab)
    for _ in range(3):
        app.processEvents()
    win.repaint()
    win.grab().save(os.path.join(OUT, name))
    print("saved", name)


steps = []


def at(delay_ms, fn):
    """الخطوات تُنفذ بالتتابع: كل خطوة بعد انتهاء السابقة بـ delay_ms."""
    steps.append((delay_ms, fn))


at(800, lambda: shot(A, "01_idle_listen_mode.png", 0))
at(100, lambda: shot(B, "02_idle_call_mode.png", 0))
at(100, A._start)
at(600, lambda: shot(A, "03_waiting_for_call.png", 5))
at(100, B._start)
at(8000, lambda: shot(A, "04_in_call_monitor_A.png", 0))
at(100, lambda: shot(B, "05_in_call_monitor_B.png", 0))
at(300, lambda: B.session.simulate_attack("tamper"))
at(500, lambda: B.session.simulate_attack("forge"))
at(500, lambda: B.session.simulate_attack("replay"))
at(300, lambda: (B.chat_in.setText("مرحباً، هل تسمعني بوضوح؟"), B._send_chat()))
at(700, lambda: (A.chat_in.setText("نعم، الصوت واضح والمكالمة مشفرة بـ Ascon-128 🔒"), A._send_chat()))
at(1500, lambda: shot(A, "06_packet_inspector.png", 1))
at(100, lambda: A.cb_rejected.setChecked(True))
at(100, lambda: shot(A, "06b_packet_inspector_rejected_only.png", 1))
at(100, lambda: A.cb_rejected.setChecked(False))
at(100, lambda: shot(B, "07_attack_simulation.png", 2))
at(100, lambda: shot(A, "08_encrypted_chat.png", 3))
at(100, lambda: shot(A, "09_event_log_attacks_blocked.png", 5))
at(100, lambda: shot(B, "09b_event_log_attacker_side.png", 5))
at(100, lambda: shot(A, "12_monitor_after_attacks.png", 0))
at(100, lambda: B.session.hangup())
at(1000, lambda: A.show_bench(benchmark.run(iterations=150)))
at(300, lambda: shot(A, "10_benchmark.png", 4))
at(100, lambda: shot(A, "11_about.png", 6))
at(100, lambda: (B.password.setText("wrong-password"), A._start()))
at(500, B._start)
at(2000, lambda: shot(B, "13_wrong_password_rejected.png", 5))
at(100, lambda: shot(A, "14_wrong_password_server_side.png", 5))
at(100, lambda: (A._hangup(), app.quit()))


def run_step(i=0):
    if i >= len(steps):
        return
    steps[i][1]()
    if i + 1 < len(steps):
        QTimer.singleShot(steps[i + 1][0], lambda: run_step(i + 1))


QTimer.singleShot(steps[0][0], run_step)
sys.exit(app.exec())
