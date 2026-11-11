"""
محرك المكالمة (Call Session Engine) - مستقل عن الواجهة الرسومية.

القنوات بين الجهازين:
  1) قناة التحكم  (TCP, المنفذ 5000): المصافحة وتبادل المفاتيح، ثم رسائل التحكم المشفرة
     (إنهاء المكالمة BYE، كتم الصوت MUTE، الرسائل النصية CHAT).
  2) قناة الوسائط (UDP, المنفذ 5001): حزم الصوت المشفرة كل 20ms + حزم PING/PONG لقياس زمن الرحلة.

الخيوط (Threads):
  - control  : الاتصال + المصافحة + استقبال رسائل التحكم.
  - sender   : يأخذ الإطارات من الميكروفون -> ترميز -> تشفير -> إرسال UDP.
  - receiver : يستقبل UDP -> فحص إعادة الإرسال -> فك التشفير والتحقق -> مخزن الارتعاش.
  - audio callbacks (من مكتبة الصوت): الالتقاط والتشغيل.
"""
import collections
import os
import queue
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from .audio.codec import FRAME_MS, PCM_FRAME_BYTES, get_codec, level_db
from .audio.jitter import JitterBuffer
from .crypto import handshake as hs
from .crypto.ciphers import AuthenticationError, get_cipher, make_nonce
from .crypto.replay import ReplayWindow
from .net import packet as pk

DEFAULT_TCP_PORT = 5000
DEFAULT_UDP_PORT = 5001

# حالات المكالمة
IDLE, LISTENING, CONNECTING, HANDSHAKE, IN_CALL, ENDED = (
    "idle", "listening", "connecting", "handshake", "in_call", "ended")

# أنواع رسائل التحكم
CTL_CHAT, CTL_BYE, CTL_MUTE = 1, 2, 3


@dataclass
class CallConfig:
    password: str = "graduation2026"
    cipher_id: int = 1               # 1 = Ascon-128
    codec_id: int = 1                # 1 = PCM16
    tcp_port: int = DEFAULT_TCP_PORT
    udp_port: int = DEFAULT_UDP_PORT
    input_device: Optional[int] = None
    output_device: Optional[int] = None
    jitter_frames: int = 3


@dataclass
class Stats:
    tx_packets: int = 0
    tx_bytes: int = 0
    rx_packets: int = 0
    rx_bytes: int = 0
    auth_failures: int = 0
    replays_blocked: int = 0
    malformed: int = 0
    enc_time_us: float = 0.0          # مجموع زمن التشفير
    dec_time_us: float = 0.0
    enc_count: int = 0
    dec_count: int = 0
    rtt_ms: float = 0.0
    jitter_ms: float = 0.0
    mic_db: float = -90.0
    spk_db: float = -90.0
    started_at: float = 0.0
    last_rx_time: float = 0.0
    history: list = field(default_factory=list)


def local_ip_addresses():
    """عناوين IP المحلية للجهاز (لعرضها للمستخدم ليعطيها للطرف الآخر)."""
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))            # لا يرسل شيئاً فعلياً، فقط لمعرفة واجهة الشبكة
        ips.add(s.getsockname()[0]); s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    ips.discard("127.0.0.1")
    return sorted(ips) or ["127.0.0.1"]


class CallSession:
    def __init__(self, config: CallConfig, audio_factory: Callable, on_event: Callable = None):
        self.cfg = config
        self.audio_factory = audio_factory
        self.on_event = on_event or (lambda kind, data: None)
        self.state = IDLE
        self.stats = Stats()
        self.packets = collections.deque(maxlen=200)    # عينات للحزم (لعرضها في الواجهة)
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self.tcp = None
        self.udp = None
        self.audio = None
        self.keys = None
        self.peer_ip = None
        self.muted = False
        self.peer_muted = False
        self.eavesdrop = False         # تشغيل النص المشفر كما يسمعه المتنصت
        self._capture_q = queue.Queue(maxsize=50)
        self._tx_seq = 0
        self._frame_idx = 0
        self._ctl_tx_seq = 0
        self._ctl_rx_seq = 0
        self._sent_ring = collections.deque(maxlen=200)
        self._attacks = collections.deque()
        self._threads = []
        self._t0 = time.perf_counter()
        self._jit_prev = None
        self._alert_last = {}
        self._warned_no_media = False
        self.info = {}

    # ------------------------------------------------------------ public API
    def start_listen(self):
        self._spawn(self._run, True, None)

    def start_call(self, host: str):
        self._spawn(self._run, False, host)

    def hangup(self, reason="local hangup"):
        if self.state in (IN_CALL,) and self.tcp:
            try:
                self._send_ctl(CTL_BYE, b"")
            except Exception:
                pass
        self._shutdown(reason)

    def set_mute(self, muted: bool):
        self.muted = muted
        if self.state == IN_CALL:
            self._send_ctl(CTL_MUTE, b"\x01" if muted else b"\x00")
        self._log("info", "تم كتم الميكروفون" if muted else "تم إلغاء كتم الميكروفون")

    def send_chat(self, text: str):
        if self.state != IN_CALL:
            raise RuntimeError("not in a call")
        self._send_ctl(CTL_CHAT, text.encode("utf-8"))

    def simulate_attack(self, kind: str):
        """محاكاة هجوم على الطرف الآخر: tamper | forge | replay"""
        if self.state != IN_CALL:
            raise RuntimeError("not in a call")
        if kind == "replay":
            old = list(self._sent_ring)[:10]
            for p in old:
                self.udp.sendto(p, self._peer_addr())
            self._log("warn", f"[محاكاة هجوم] تم إعادة إرسال {len(old)} حزمة قديمة ملتقطة (Replay Attack)")
        else:
            self._attacks.append(kind)      # يُنفذ على الحزمة الصوتية التالية

    def snapshot(self) -> dict:
        s = self.stats
        now = time.time()
        dur = now - s.started_at if s.started_at else 0
        j = self._jitter
        return {
            "state": self.state, "duration": dur,
            "tx_packets": s.tx_packets, "rx_packets": s.rx_packets,
            "tx_bytes": s.tx_bytes, "rx_bytes": s.rx_bytes,
            "auth_failures": s.auth_failures, "replays_blocked": s.replays_blocked,
            "malformed": s.malformed,
            "lost": j.lost if j else 0, "late": j.late if j else 0,
            "jitter_depth": j.depth() if j else 0,
            "enc_us": s.enc_time_us / s.enc_count if s.enc_count else 0.0,
            "dec_us": s.dec_time_us / s.dec_count if s.dec_count else 0.0,
            "rtt_ms": s.rtt_ms, "jitter_ms": s.jitter_ms,
            "mic_db": s.mic_db, "spk_db": s.spk_db,
            "muted": self.muted, "peer_muted": self.peer_muted,
        }

    # ------------------------------------------------------------ internals
    _jitter = None

    def _spawn(self, fn, *args):
        th = threading.Thread(target=fn, args=args, daemon=True)
        self._threads.append(th)
        th.start()

    def _set_state(self, st):
        self.state = st
        self.on_event("state", st)

    def _log(self, level, msg):
        self.on_event("log", (level, msg))

    def _alert(self, key, msg):
        """تنبيه أمني مع تحديد المعدل (مرة كل ثانية لكل نوع)."""
        now = time.time()
        if now - self._alert_last.get(key, 0) > 1.0:
            self._alert_last[key] = now
            self.on_event("alert", msg)
            self._log("alert", msg)

    def _peer_addr(self):
        return (self.peer_ip, self.keys.peer_udp_port)

    def _ts(self):
        return int((time.perf_counter() - self._t0) * 1000)

    def _bind_udp(self):
        u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            u.bind(("0.0.0.0", self.cfg.udp_port))
        except OSError:
            u.bind(("0.0.0.0", 0))
            self._log("warn", f"المنفذ UDP {self.cfg.udp_port} مستخدم، تم اختيار منفذ آخر: {u.getsockname()[1]}")
        u.settimeout(0.2)
        return u

    def _run(self, listen: bool, host: Optional[str]):
        try:
            self.udp = self._bind_udp()
            udp_port = self.udp.getsockname()[1]
            if listen:
                self._set_state(LISTENING)
                srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                srv.bind(("0.0.0.0", self.cfg.tcp_port))
                srv.listen(1)
                srv.settimeout(0.3)
                self._log("info", f"بانتظار مكالمة على المنفذ TCP {self.cfg.tcp_port} / UDP {udp_port} ...")
                while not self._stop.is_set():
                    try:
                        self.tcp, addr = srv.accept()
                        break
                    except socket.timeout:
                        continue
                srv.close()
                if self._stop.is_set():
                    return
                self.peer_ip = addr[0]
                self._log("info", f"اتصال وارد من {self.peer_ip}")
            else:
                self._set_state(CONNECTING)
                self._log("info", f"جاري الاتصال بـ {host}:{self.cfg.tcp_port} ...")
                self.tcp = socket.create_connection((host, self.cfg.tcp_port), timeout=8)
                if self._stop.is_set():
                    self.tcp.close()
                    return
                self.peer_ip = self.tcp.getpeername()[0]

            self.tcp.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.tcp.settimeout(30)
            self._set_state(HANDSHAKE)
            self._log("info", "بدء المصافحة: تبادل مفاتيح X25519 + اشتقاق المفاتيح HKDF + التحقق من كلمة السر")
            t = time.perf_counter()
            if listen:
                self.keys = hs.server_handshake(self.tcp, self.cfg.password, udp_port)
            else:
                self.keys = hs.client_handshake(self.tcp, self.cfg.password, self.cfg.cipher_id,
                                                self.cfg.codec_id, udp_port)
            hs_ms = (time.perf_counter() - t) * 1000
            self._start_media()
            cipher_cls = get_cipher(self.keys.cipher_id)
            self.info = {
                "peer": self.peer_ip, "peer_udp": self.keys.peer_udp_port, "local_udp": udp_port,
                "cipher": cipher_cls.name, "codec": self.codec.name, "sas": self.keys.sas,
                "fingerprint": self.keys.fingerprint, "handshake_ms": hs_ms,
                "role": "initiator" if not listen else "responder",
            }
            self._set_state(IN_CALL)
            self._log("ok", f"تم إنشاء جلسة آمنة خلال {hs_ms:.0f}ms | الخوارزمية: {cipher_cls.name} | "
                            f"الترميز: {self.codec.name} | رمز الأمان: {self.keys.sas}")
            self.on_event("connected", self.info)
            self._control_loop()
        except hs.HandshakeError as e:
            self._log("error", f"فشلت المصافحة: {e}")
            self.on_event("error", f"فشلت المصافحة: {e}")
            self._shutdown("handshake failed")
        except (OSError, ConnectionError) as e:
            if not self._stop.is_set():
                self._log("error", f"خطأ في الشبكة: {e}")
                self.on_event("error", f"خطأ في الشبكة: {e}")
            self._shutdown("network error")
        except Exception as e:     # noqa: BLE001
            self._log("error", f"خطأ غير متوقع: {e!r}")
            self.on_event("error", f"خطأ غير متوقع: {e!r}")
            self._shutdown("error")

    def _start_media(self):
        k = self.keys
        cls = get_cipher(k.cipher_id)
        self.tx_cipher = cls(k.tx_key)
        self.rx_cipher = cls(k.rx_key)
        self.ctl_tx_cipher = cls(k.ctl_tx_key)
        self.ctl_rx_cipher = cls(k.ctl_rx_key)
        self.codec = get_codec(k.codec_id)
        self.replay = ReplayWindow()
        self._jitter = JitterBuffer(PCM_FRAME_BYTES, target_depth=self.cfg.jitter_frames)
        self.stats.started_at = time.time()
        self.stats.last_rx_time = time.time()
        self._spawn(self._sender_loop)
        self._spawn(self._receiver_loop)
        self.audio = self.audio_factory(self.cfg)
        self.audio.start(self._on_capture, self._on_playback)

    # ---------------- audio callbacks (يجب أن تكون سريعة جداً)
    def _on_capture(self, pcm: bytes):
        try:
            self._capture_q.put_nowait(pcm)
        except queue.Full:
            pass

    def _on_playback(self) -> bytes:
        if self._jitter is None:
            return bytes(PCM_FRAME_BYTES)
        pcm = self._jitter.pop()
        self.stats.spk_db = level_db(pcm)
        return pcm

    # ---------------- sender
    def _next_seq(self):
        with self._lock:
            self._tx_seq += 1
            if self._tx_seq >= 0xFFFFFFFF:
                raise RuntimeError("sequence space exhausted - rekey required")
            return self._tx_seq

    def _seal(self, ptype, payload, ts=None):
        seq = self._next_seq()
        header = pk.build_header(ptype, seq, self._ts() if ts is None else ts)
        nonce = make_nonce(self.keys.tx_iv, seq, self.tx_cipher.nonce_size)
        t = time.perf_counter()
        ct = self.tx_cipher.encrypt(nonce, payload, header)
        dt = (time.perf_counter() - t) * 1e6
        return seq, header, nonce, ct, dt

    def _sender_loop(self):
        last_ping = 0.0
        while not self._stop.is_set():
            try:
                pcm = self._capture_q.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                self.stats.mic_db = level_db(pcm)
                if self.muted:
                    pcm = bytes(len(pcm))
                payload = self.codec.encode(pcm)
                self._frame_idx += 1
                # في حزم الصوت: حقل timestamp = رقم الإطار الصوتي (كل إطار = 20ms)
                seq, header, nonce, ct, dt = self._seal(pk.T_VOICE, payload, ts=self._frame_idx)
                self.stats.enc_time_us += dt
                self.stats.enc_count += 1
                pkt = header + ct

                attack = self._attacks.popleft() if self._attacks else None
                if attack == "tamper":
                    bad = bytearray(pkt); bad[pk.HEADER_SIZE + 5] ^= 0x01   # قلب بت واحد في النص المشفر
                    self.udp.sendto(bytes(bad), self._peer_addr())
                    self._log("warn", f"[محاكاة هجوم] أُرسلت حزمة #{seq} بعد تعديل بت واحد في النص المشفر (Tampering)")
                elif attack == "forge":
                    fake_key = os.urandom(32)
                    forged = get_cipher(self.keys.cipher_id)(fake_key).encrypt(nonce, os.urandom(len(payload)), header)
                    self.udp.sendto(header + forged, self._peer_addr())
                    self._log("warn", f"[محاكاة هجوم] أُرسلت حزمة مزوّرة #{seq} مشفرة بمفتاح عشوائي (Forgery)")

                self.udp.sendto(pkt, self._peer_addr())
                self._sent_ring.append(pkt)
                self.stats.tx_packets += 1
                self.stats.tx_bytes += len(pkt) + 28        # + ترويسة IP/UDP
                if seq % 10 == 0:
                    self._record("TX", seq, pk.T_VOICE, len(pkt), payload, nonce, ct, "OK", dt)

                now = time.perf_counter()
                if now - last_ping > 1.0:
                    last_ping = now
                    _, h, _, c, _ = self._seal(pk.T_PING, struct.pack(">d", now))
                    self.udp.sendto(h + c, self._peer_addr())
            except Exception as e:     # noqa: BLE001
                if self._stop.is_set():
                    break
                self._log("error", f"خطأ في الإرسال: {e}")
                time.sleep(0.05)

    # ---------------- receiver
    def _receiver_loop(self):
        while not self._stop.is_set():
            try:
                data, addr = self.udp.recvfrom(4096)
            except socket.timeout:
                if (self.state == IN_CALL and time.time() - self.stats.last_rx_time > 4
                        and not self._warned_no_media):
                    self._warned_no_media = True
                    self._log("warn", "لم تصل أي حزمة صوت منذ 4 ثوانٍ - تحقق من الجدار الناري (منفذ UDP) على الجهاز الآخر")
                continue
            except OSError:
                if self._stop.is_set():
                    break
                continue
            arrival = time.perf_counter()
            try:
                ptype, seq, ts, header, ct = pk.parse(data)
            except pk.PacketError:
                self.stats.malformed += 1
                continue
            if not self.replay.check(seq):
                self.stats.replays_blocked += 1
                self._record("RX", seq, ptype, len(data), None, None, ct, "REPLAY", 0)
                self._alert("replay", f"⚠ تم رفض حزمة مكررة #{seq} (هجوم إعادة إرسال Replay Attack)")
                continue
            nonce = make_nonce(self.keys.rx_iv, seq, self.rx_cipher.nonce_size)
            t = time.perf_counter()
            try:
                payload = self.rx_cipher.decrypt(nonce, ct, header)
            except AuthenticationError:
                self.stats.auth_failures += 1
                self._record("RX", seq, ptype, len(data), None, nonce, ct, "AUTH FAIL", 0)
                self._alert("auth", f"⚠ تم رفض حزمة #{seq}: فشل التحقق من الوسم (حزمة معدّلة أو مزوّرة)")
                continue
            dt = (time.perf_counter() - t) * 1e6
            self.replay.update(seq)
            self.stats.last_rx_time = time.time()
            self._warned_no_media = False

            if ptype == pk.T_PING:
                _, h, _, c, _ = self._seal(pk.T_PONG, payload)
                self.udp.sendto(h + c, self._peer_addr())
                continue
            if ptype == pk.T_PONG:
                (sent,) = struct.unpack(">d", payload)
                rtt = (time.perf_counter() - sent) * 1000
                self.stats.rtt_ms = rtt if not self.stats.rtt_ms else 0.8 * self.stats.rtt_ms + 0.2 * rtt
                continue

            self.stats.dec_time_us += dt
            self.stats.dec_count += 1
            self.stats.rx_packets += 1
            self.stats.rx_bytes += len(data) + 28
            # الارتعاش حسب RFC 3550
            if self._jit_prev is not None:
                d = (arrival - self._jit_prev[0]) * 1000 - (ts - self._jit_prev[1]) * FRAME_MS
                self.stats.jitter_ms += (abs(d) - self.stats.jitter_ms) / 16
            self._jit_prev = (arrival, ts)
            if seq % 10 == 0:
                self._record("RX", seq, ptype, len(data), payload, nonce, ct, "OK", dt)
            if self.eavesdrop:
                # ما يسمعه المتنصت: البايتات المشفرة كأنها صوت -> ضجيج
                raw = (ct[:-16] * 2)[:PCM_FRAME_BYTES]
                pcm = raw + bytes(PCM_FRAME_BYTES - len(raw))
            else:
                pcm = self.codec.decode(payload)
            self._jitter.push(ts, pcm)      # الترتيب حسب رقم الإطار الصوتي

    def _record(self, direction, seq, ptype, size, payload, nonce, ct, status, us):
        self.packets.append({
            "time": time.strftime("%H:%M:%S"), "dir": direction, "seq": seq,
            "type": pk.TYPE_NAMES.get(ptype, "?"), "size": size,
            "plain": payload[:10].hex(" ") if payload else "—",
            "nonce": nonce.hex() if nonce else "—",
            "cipher": ct[:10].hex(" "), "tag": ct[-16:].hex(), "status": status, "us": us,
        })

    # ---------------- control channel (TCP, encrypted)
    def _send_ctl(self, mtype: int, body: bytes):
        with self._lock:
            self._ctl_tx_seq += 1
            seq = self._ctl_tx_seq
        ad = b"CTL" + struct.pack(">Q", seq)
        nonce = make_nonce(self.keys.ctl_tx_iv, seq, self.ctl_tx_cipher.nonce_size)
        ct = self.ctl_tx_cipher.encrypt(nonce, bytes([mtype]) + body, ad)
        hs.send_frame(self.tcp, struct.pack(">Q", seq) + ct)

    def _control_loop(self):
        self.tcp.settimeout(0.5)
        while not self._stop.is_set():
            try:
                frame = hs.recv_frame(self.tcp)
            except socket.timeout:
                continue
            except (ConnectionError, OSError):
                if not self._stop.is_set():
                    self._log("warn", "انقطع الاتصال بالطرف الآخر")
                    self._shutdown("peer disconnected")
                return
            (seq,) = struct.unpack(">Q", frame[:8])
            if seq <= self._ctl_rx_seq:
                self._alert("ctl_replay", "⚠ تم رفض رسالة تحكم مكررة")
                continue
            nonce = make_nonce(self.keys.ctl_rx_iv, seq, self.ctl_rx_cipher.nonce_size)
            try:
                msg = self.ctl_rx_cipher.decrypt(nonce, frame[8:], b"CTL" + frame[:8])
            except AuthenticationError:
                self._alert("ctl_auth", "⚠ تم رفض رسالة تحكم معدّلة")
                continue
            self._ctl_rx_seq = seq
            mtype, body = msg[0], msg[1:]
            if mtype == CTL_CHAT:
                self.on_event("chat", body.decode("utf-8", "replace"))
            elif mtype == CTL_MUTE:
                self.peer_muted = body == b"\x01"
                self._log("info", "الطرف الآخر كتم الميكروفون" if self.peer_muted else "الطرف الآخر ألغى الكتم")
            elif mtype == CTL_BYE:
                self._log("info", "الطرف الآخر أنهى المكالمة")
                self._shutdown("peer hangup")
                return

    def _shutdown(self, reason):
        if self._stop.is_set():
            return
        self._stop.set()
        if self.audio:
            try:
                self.audio.stop()
            except Exception:
                pass
        for s in (self.tcp, self.udp):
            if s:
                try:
                    s.close()
                except OSError:
                    pass
        self._set_state(ENDED)
        self.on_event("ended", reason)
