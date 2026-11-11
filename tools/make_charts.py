"""
يولّد ملفات النتائج والرسوم البيانية للتقرير:
  docs/results/benchmark.json  +  docs/results/e2e_results.json
  docs/images/charts/*.png
python tools/make_charts.py
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import matplotlib                                       # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                         # noqa: E402

from securevoice import benchmark                       # noqa: E402
from securevoice.audio.devices import FakeAudioBackend  # noqa: E402
from securevoice.crypto.ciphers import CIPHERS          # noqa: E402
from securevoice.session import IN_CALL, CallConfig, CallSession  # noqa: E402

OUT_IMG = "docs/images/charts"
OUT_RES = "docs/results"
os.makedirs(OUT_IMG, exist_ok=True); os.makedirs(OUT_RES, exist_ok=True)
COL = {"Ascon-128": "#10b981", "ChaCha20-Poly1305": "#0ea5e9", "AES-128-GCM": "#f59e0b"}
plt.rcParams.update({"figure.dpi": 150, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": .3, "font.size": 10})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_IMG, name), facecolor="white")
    plt.close(fig)
    print("chart", name)


# ------------------------------------------------------------ 1) micro-benchmark
rep = benchmark.run(iterations=400)
json.dump(rep, open(os.path.join(OUT_RES, "benchmark.json"), "w"), indent=2)
res = rep["results"]
names = list(COL)

fig, ax = plt.subplots(figsize=(8, 4.2))
w = 0.38
for j, fs in enumerate((320, 640)):
    vals = [next(r["enc_us"] for r in res if r["cipher"] == n and r["frame_bytes"] == fs) for n in names]
    xs = [i + (j - .5) * w for i in range(3)]
    bars = ax.bar(xs, vals, w, color=[COL[n] for n in names], alpha=1 if j else .55,
                  label=f"{fs}-byte frame" + (" (PCM16)" if fs == 640 else " (G.711)"))
    for x, v in zip(xs, vals):
        ax.text(x, v * 1.15, f"{v:.1f}", ha="center", fontsize=8)
ax.set_yscale("log"); ax.set_xticks(range(3)); ax.set_xticklabels(names)
ax.set_ylabel("Encryption time per frame (µs, log scale)")
ax.set_title("Encryption time per voice frame")
ax.legend()
save(fig, "01_encryption_time.png")

fig, ax = plt.subplots(figsize=(8, 4))
vals = [next(r["frame_budget_pct"] for r in res if r["cipher"] == n and r["frame_bytes"] == 640) for n in names]
ax.barh(names, vals, color=[COL[n] for n in names])
ax.axvline(100, color="#ef4444", ls="--"); ax.text(99, 2.35, "real-time limit (20 ms)", color="#ef4444", ha="right")
for i, v in enumerate(vals):
    ax.text(v + 1.5, i, f"{v:.2f}%", va="center")
ax.set_xlim(0, 110)
ax.set_xlabel("Encrypt + decrypt time as % of the 20 ms frame period")
ax.set_title("Real-time budget used by cryptography (640-byte frame)")
save(fig, "02_realtime_budget.png")

# ------------------------------------------------------------ 2) bandwidth
fig, ax = plt.subplots(figsize=(8, 4))
labels = ["PCM16 16 kHz", "G.711 μ-law"]
payload = [640, 320]
pps = 50
layers = [("Voice payload", payload, "#0ea5e9"), ("Auth tag (16 B)", [16, 16], "#10b981"),
          ("SecureVoice header (10 B)", [10, 10], "#a78bfa"), ("IPv4+UDP (28 B)", [28, 28], "#94a3b8")]
bottom = [0, 0]
for name, b, c in layers:
    kb = [x * 8 * pps / 1000 for x in b]
    ax.bar(labels, kb, bottom=bottom, color=c, label=name)
    bottom = [p + q for p, q in zip(bottom, kb)]
for i, t in enumerate(bottom):
    ax.text(i, t + 4, f"{t:.1f} kbit/s", ha="center", fontweight="bold")
ax.set_ylabel("kbit/s per direction"); ax.set_title("Bandwidth per direction (50 packets/s)")
ax.legend(fontsize=8); ax.set_ylim(0, 320)
save(fig, "03_bandwidth.png")

# ------------------------------------------------------------ 3) real end-to-end calls on loopback
e2e = []
port = 49000
for cid, cls in CIPHERS.items():
    fa, fb = FakeAudioBackend(440), FakeAudioBackend(880)
    a = CallSession(CallConfig(password="p", tcp_port=port, udp_port=port + 1), lambda c: fa)
    b = CallSession(CallConfig(password="p", cipher_id=cid, tcp_port=port, udp_port=port + 2), lambda c: fb)
    port += 10
    a.start_listen(); time.sleep(0.2); b.start_call("127.0.0.1")
    t0 = time.time()
    while not (a.state == IN_CALL and b.state == IN_CALL) and time.time() - t0 < 10:
        time.sleep(0.05)
    time.sleep(10)
    s = a.snapshot()
    sent = set(fb.captured)
    exact = sum(1 for f in fa.played if f in sent)
    e2e.append({"cipher": cls.name, "handshake_ms": a.info["handshake_ms"], "rx_packets": s["rx_packets"],
                "lost": s["lost"], "auth_failures": s["auth_failures"], "enc_us": s["enc_us"],
                "dec_us": s["dec_us"], "rtt_ms": s["rtt_ms"], "jitter_ms": s["jitter_ms"],
                "frames_bit_exact": exact, "duration_s": s["duration"]})
    b.hangup(); time.sleep(0.5)
    print("e2e", e2e[-1])
json.dump(e2e, open(os.path.join(OUT_RES, "e2e_results.json"), "w"), indent=2)

fig, axs = plt.subplots(1, 3, figsize=(11, 3.6))
for ax, key, title, unit in ((axs[0], "handshake_ms", "Handshake time", "ms"),
                             (axs[1], "rtt_ms", "Round-trip time (loopback)", "ms"),
                             (axs[2], "dec_us", "Decrypt time per frame (live call)", "µs")):
    vals = [x[key] for x in e2e]
    ax.bar([x["cipher"].split("-")[0] for x in e2e], vals, color=[COL[x["cipher"]] for x in e2e])
    for i, v in enumerate(vals):
        ax.text(i, v, f"{v:.1f}", ha="center", va="bottom", fontsize=8)
    ax.set_title(title); ax.set_ylabel(unit)
save(fig, "04_live_call_metrics.png")

# ------------------------------------------------------------ 4) latency budget (mouth-to-ear estimate)
asc = next(x for x in e2e if x["cipher"] == "Ascon-128")
parts = [("Frame capture (20 ms)", 20), ("Ascon encrypt", asc["enc_us"] / 1000), ("LAN transit", 1.0),
         ("Ascon decrypt", asc["dec_us"] / 1000), ("Jitter buffer (3 frames)", 60),
         ("Sound card output buffer", 20)]
fig, ax = plt.subplots(figsize=(9, 2.6))
left = 0
cols = ["#94a3b8", "#10b981", "#0ea5e9", "#10b981", "#a78bfa", "#f59e0b"]
for (n, v), c in zip(parts, cols):
    ax.barh([0], [v], left=left, color=c, label=f"{n}: {v:.1f} ms")
    left += v
ax.axvline(150, color="#ef4444", ls="--"); ax.text(152, 0, "ITU-T G.114\nlimit 150 ms", color="#ef4444", ha="left", va="center")
ax.set_yticks([]); ax.set_xlim(0, 185); ax.set_xlabel("ms")
ax.set_title(f"Estimated mouth-to-ear latency ≈ {left:.0f} ms")
ax.legend(fontsize=7, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.35))
save(fig, "05_latency_budget.png")
print("done")
