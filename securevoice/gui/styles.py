"""ثيم داكن للواجهة."""
STYLE = """
* { font-size: 13px; color: #e5e7eb; }
QMainWindow, QWidget#root, QWidget#side { background: #0b1220; }
QScrollArea { background: transparent; border: none; }
QGroupBox { background: #0f172a; border: 1px solid #1f2937; border-radius: 10px; margin-top: 18px; padding: 10px; padding-top: 16px; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top right; right: 12px; padding: 0 6px; color: #22d3ee; font-weight: bold; }
QLabel#title { font-size: 21px; font-weight: bold; color: #f8fafc; }
QLabel#subtitle { color: #94a3b8; font-size: 12px; }
QLabel#muted { color: #94a3b8; }
QLabel#sas { font-size: 30px; font-weight: bold; color: #34d399; letter-spacing: 4px; font-family: Consolas, 'DejaVu Sans Mono', monospace; }
QLabel#state { font-size: 15px; font-weight: bold; }
QLabel#timer { font-size: 22px; font-family: Consolas, 'DejaVu Sans Mono', monospace; color: #f8fafc; }
QFrame#statCard { background: #111827; border: 1px solid #1f2937; border-radius: 10px; }
QLabel#statTitle { color: #94a3b8; font-size: 12px; }
QLabel#statValue { font-size: 20px; font-weight: bold; font-family: Consolas, 'DejaVu Sans Mono', monospace; }
QLabel#statUnit { color: #64748b; font-size: 11px; }
QLineEdit, QComboBox, QSpinBox, QPlainTextEdit, QTextEdit, QTableWidget {
  background: #111827; border: 1px solid #334155; border-radius: 6px; padding: 5px; selection-background-color: #0e7490; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid #22d3ee; }
QComboBox QAbstractItemView { background: #111827; border: 1px solid #334155; selection-background-color: #0e7490; }
QPushButton { background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 7px 14px; }
QPushButton:hover { background: #273449; border-color: #22d3ee; }
QPushButton:disabled { color: #475569; border-color: #1f2937; }
QPushButton#start { background: #059669; border: none; font-size: 15px; font-weight: bold; padding: 11px; }
QPushButton#start:hover { background: #10b981; }
QPushButton#hangup { background: #dc2626; border: none; font-size: 15px; font-weight: bold; padding: 11px; }
QPushButton#hangup:hover { background: #ef4444; }
QPushButton#start:disabled, QPushButton#hangup:disabled { background: #1e293b; color: #475569; }
QPushButton#attack { background: #3b1d1d; border: 1px solid #7f1d1d; text-align: right; padding: 10px; }
QPushButton#attack:hover { background: #4c1d1d; border-color: #f87171; }
QTabWidget::pane { border: 1px solid #1f2937; border-radius: 8px; background: #0f172a; top: -1px; }
QTabBar::tab { background: #111827; border: 1px solid #1f2937; padding: 8px 14px; margin-left: 2px; border-top-left-radius: 8px; border-top-right-radius: 8px; color: #94a3b8; }
QTabBar::tab:selected { background: #0f172a; color: #22d3ee; border-bottom-color: #0f172a; font-weight: bold; }
QHeaderView::section { background: #1e293b; color: #cbd5e1; border: none; padding: 6px; font-weight: bold; }
QTableWidget { gridline-color: #1f2937; font-family: Consolas, 'DejaVu Sans Mono', monospace; font-size: 12px; }
QRadioButton, QCheckBox { spacing: 8px; }
QProgressBar { background: #111827; border: 1px solid #334155; border-radius: 6px; text-align: center; }
QProgressBar::chunk { background: #22d3ee; border-radius: 6px; }
QScrollBar:vertical { background: #0f172a; width: 10px; }
QScrollBar::handle:vertical { background: #334155; border-radius: 5px; min-height: 20px; }
QStatusBar { background: #0f172a; color: #94a3b8; }
"""
