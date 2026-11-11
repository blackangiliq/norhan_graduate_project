# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec: pyinstaller --noconfirm SecureVoice.spec
a = Analysis(
    ['main.py'],
    pathex=[],
    datas=[('assets', 'assets')],
    hiddenimports=['_sounddevice_data'],
    excludes=['tkinter', 'matplotlib', 'pytest', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
              'PySide6.Qt3DCore', 'PySide6.QtQuick', 'PySide6.QtQml', 'PySide6.QtMultimedia', 'PySide6.QtCharts'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='SecureVoice',
    console=False,
    icon='assets/icon.ico',
)
coll = COLLECT(exe, a.binaries, a.datas, name='SecureVoice')
