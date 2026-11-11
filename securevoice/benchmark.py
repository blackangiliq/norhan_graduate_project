"""
مقارنة أداء خوارزميات التشفير على إطارات صوتية حقيقية الحجم.
يقيس: زمن التشفير وفك التشفير لكل إطار، الإنتاجية، الحجم الإضافي، ونسبة استهلاك زمن الإطار (20ms).

التشغيل:  python -m securevoice.benchmark
"""
import json
import os
import platform
import sys
import time

from .crypto.ciphers import CIPHERS, make_nonce

FRAME_SIZES = {"G.711 μ-law (320 B)": 320, "PCM16 (640 B)": 640}


def bench_cipher(cls, frame_size: int, iterations: int):
    key = os.urandom(32)
    iv = os.urandom(16)
    c = cls(key)
    frame = os.urandom(frame_size)
    ad = os.urandom(10)
    nonces = [make_nonce(iv, i + 1, c.nonce_size) for i in range(iterations)]
    # إحماء
    for n in nonces[:20]:
        c.decrypt(n, c.encrypt(n, frame, ad), ad)
    t = time.perf_counter()
    cts = [c.encrypt(n, frame, ad) for n in nonces]
    enc = (time.perf_counter() - t) / iterations
    t = time.perf_counter()
    for n, ct in zip(nonces, cts):
        c.decrypt(n, ct, ad)
    dec = (time.perf_counter() - t) / iterations
    return {
        "cipher": cls.name, "frame_bytes": frame_size,
        "enc_us": enc * 1e6, "dec_us": dec * 1e6,
        "throughput_mbps": frame_size * 8 / enc / 1e6,
        "overhead_bytes": len(cts[0]) - frame_size,
        "frame_budget_pct": (enc + dec) / 0.020 * 100,    # من زمن الإطار 20ms
        "key_bits": cls.key_size * 8, "nonce_bits": cls.nonce_size * 8,
        "lightweight": cls.lightweight,
    }


def run(iterations: int = 300, progress=None):
    results = []
    jobs = [(cls, fs) for fs in FRAME_SIZES.values() for cls in CIPHERS.values()]
    for i, (cls, fs) in enumerate(jobs):
        results.append(bench_cipher(cls, fs, iterations))
        if progress:
            progress(i + 1, len(jobs))
    return {
        "platform": f"{platform.system()} {platform.release()} | {platform.processor() or platform.machine()}",
        "python": sys.version.split()[0], "iterations": iterations, "results": results,
    }


def main():
    rep = run()
    print(f"Platform: {rep['platform']}  Python {rep['python']}  iterations={rep['iterations']}\n")
    print(f"{'Cipher':20}{'Frame':>7}{'Enc µs':>10}{'Dec µs':>10}{'Mbit/s':>10}{'Overhead':>10}{'% of 20ms':>11}")
    for r in rep["results"]:
        print(f"{r['cipher']:20}{r['frame_bytes']:>7}{r['enc_us']:>10.1f}{r['dec_us']:>10.1f}"
              f"{r['throughput_mbps']:>10.2f}{r['overhead_bytes']:>9}B{r['frame_budget_pct']:>10.2f}%")
    if "--json" in sys.argv:
        out = sys.argv[sys.argv.index("--json") + 1]
        with open(out, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
