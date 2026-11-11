"""اختبار دخاني للواجهة الرسومية (بدون شاشة - offscreen)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture(scope="module")
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_two_windows_make_a_call(app):
    import time

    from securevoice.audio.devices import TEST_TONE
    from securevoice.gui.main_window import MainWindow
    from securevoice.session import IN_CALL

    a, b = MainWindow(), MainWindow()
    for w in (a, b):
        w.mic.setCurrentIndex(w.mic.findData(TEST_TONE))
        w.tcp_port.setValue(48100)
    a.udp_port.setValue(48101)
    b.udp_port.setValue(48102)
    b.rb_call.setChecked(True)
    b.peer_ip.setText("127.0.0.1")
    a._start()
    time.sleep(0.2)
    b._start()
    end = time.time() + 8
    while time.time() < end and not (a.session.state == IN_CALL and b.session.state == IN_CALL):
        app.processEvents(); time.sleep(0.05)
    assert a.session.state == IN_CALL
    for _ in range(30):
        app.processEvents(); time.sleep(0.05)
    a._tick(); b._tick()
    assert a.sas_lbl.text() == b.sas_lbl.text() != "--- ---"
    assert int(a.cards["rx"].v.text()) > 0
    b._hangup()
    for _ in range(20):
        app.processEvents(); time.sleep(0.05)
    assert a.session.state == "ended"
