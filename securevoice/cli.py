"""
تشغيل المكالمة من سطر الأوامر (بدون واجهة) - مفيد للاختبار السريع.

  python -m securevoice.cli listen --password mykey
  python -m securevoice.cli call 192.168.1.10 --password mykey --cipher 1
"""
import argparse
import time

from .audio.devices import TEST_TONE, make_backend
from .crypto.ciphers import CIPHERS
from .session import ENDED, CallConfig, CallSession, local_ip_addresses


def main():
    ap = argparse.ArgumentParser(description="SecureVoice command-line client")
    ap.add_argument("mode", choices=["listen", "call"])
    ap.add_argument("host", nargs="?")
    ap.add_argument("--password", default="graduation2026")
    ap.add_argument("--cipher", type=int, default=1, choices=list(CIPHERS),
                    help="1=Ascon-128  2=ChaCha20-Poly1305  3=AES-128-GCM")
    ap.add_argument("--codec", type=int, default=1, choices=[1, 2], help="1=PCM16  2=G.711 u-law")
    ap.add_argument("--tcp-port", type=int, default=5000)
    ap.add_argument("--udp-port", type=int, default=5001)
    ap.add_argument("--tone", action="store_true", help="use a test tone instead of the microphone")
    a = ap.parse_args()
    if a.mode == "call" and not a.host:
        ap.error("host is required for call mode")

    cfg = CallConfig(password=a.password, cipher_id=a.cipher, codec_id=a.codec, tcp_port=a.tcp_port,
                     udp_port=a.udp_port, input_device=TEST_TONE if a.tone else None)

    def on_event(kind, data):
        if kind == "log":
            print(f"[{data[0]}] {data[1]}")
        elif kind == "chat":
            print(f"[chat] {data}")

    s = CallSession(cfg, lambda c: make_backend(c.input_device, c.output_device), on_event)
    print("Local IP:", ", ".join(local_ip_addresses()))
    s.start_listen() if a.mode == "listen" else s.start_call(a.host)
    try:
        while s.state != ENDED:
            time.sleep(2)
            if s.state == "in_call":
                x = s.snapshot()
                print(f"  tx={x['tx_packets']} rx={x['rx_packets']} lost={x['lost']} rejected={x['auth_failures']} "
                      f"replay={x['replays_blocked']} enc={x['enc_us']:.0f}us rtt={x['rtt_ms']:.1f}ms")
    except KeyboardInterrupt:
        s.hangup()
        time.sleep(0.3)


if __name__ == "__main__":
    main()
