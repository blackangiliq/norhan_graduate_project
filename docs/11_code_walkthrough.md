<div dir="rtl">

# 11. شرح الكود ملفاً ملفاً

[⬅ العودة للصفحة الرئيسية](../README.md)

## 11.1 خريطة الملفات

</div>

```
securevoice/
├── __init__.py            اسم البرنامج والإصدار
├── __main__.py            python -m securevoice  → يشغل الواجهة
├── crypto/
│   ├── ascon.py           Ascon-128 من الصفر
│   ├── ciphers.py         واجهة AEAD موحدة + make_nonce
│   ├── handshake.py       المصافحة واشتقاق المفاتيح
│   └── replay.py          نافذة منع التكرار
├── audio/
│   ├── codec.py           PCM16 / μ-law / level_db
│   ├── jitter.py          JitterBuffer
│   └── devices.py         SoundDeviceBackend / ToneInputBackend / FakeAudioBackend
├── net/packet.py          بنية حزمة UDP
├── session.py             CallSession: محرك المكالمة
├── benchmark.py           قياس الأداء
├── cli.py                 واجهة سطر الأوامر
└── gui/
    ├── main_window.py     النافذة الرئيسية
    ├── widgets.py         الرسوم البيانية والبطاقات ومؤشرات المستوى
    └── styles.py          الثيم الداكن
```

<div dir="rtl">

## 11.2 `crypto/ascon.py`

| الدالة | الوظيفة |
|---|---|
| `permutation(s, rounds)` | دالة التبديل: لكل جولة ثابت + S-box (bitsliced) + انتشار خطي. تعمل على قائمة من 5 أعداد صحيحة 64 بت |
| `_pad(data)` | الحشو `0x80 00..` إلى مضاعفات 8 |
| `_initialize(key, nonce)` | `S = IV‖K‖N` ← p¹² ← XOR المفتاح |
| `_absorb_ad(s, ad)` | امتصاص الترويسة + فصل المجال `x4 ^= 1` |
| `_finalize(s, k0, k1)` | XOR المفتاح ← p¹² ← الوسم |
| `encrypt(key, nonce, ad, pt)` | يعيد `C ‖ Tag` |
| `decrypt(key, nonce, ad, ct)` | يعيد النص أو يرفع `AsconAuthError`، مع مقارنة زمن ثابت للوسم |

نقطة تقنية: Python لا يملك نوع 64 بت، لذلك نستخدم `& MASK64` بعد عمليات النفي والإزاحة لليسار.

## 11.3 `crypto/ciphers.py`

- `AEADCipher`: الصنف الأساسي (`id`, `name`, `key_size`, `nonce_size`, `encrypt`, `decrypt`).
- `Ascon128` / `ChaCha20Poly1305Cipher` / `AES128GCM`: تطبيقات، وكلها ترفع `AuthenticationError` الموحّد عند الفشل.
- `CIPHERS`: قاموس من رقم الخوارزمية (المرسل في المصافحة) إلى الصنف.
- `make_nonce(iv, seq, size)`: `IV ⊕ seq`.

## 11.4 `crypto/handshake.py`

| العنصر | الوظيفة |
|---|---|
| `HELLO_FMT = ">4sBBBH16s32s"` | بنية Hello (57 بايت) |
| `send_frame / recv_frame / recv_exact` | تأطير الرسائل على TCP بطول 2 بايت |
| `derive_psk` | PBKDF2-HMAC-SHA256 بـ 100,000 تكرار |
| `derive_keys` | HKDF-Extract + HKDF-Expand ← 10 أجزاء |
| `finished_mac` | HMAC للتأكيد |
| `client_handshake(sock, password, cipher_id, codec_id, udp_port)` | دور المتصل B |
| `server_handshake(sock, password, udp_port)` | دور المستقبل A |
| `SessionKeys` | المفاتيح الناتجة + SAS + البصمة + منفذ UDP للطرف الآخر |
| `_build_keys(..., initiator)` | يوزع المفاتيح: ما هو "إرسال" عند B هو "استقبال" عند A |

## 11.5 `crypto/replay.py`
`ReplayWindow.check(seq)` بدون تعديل، و `update(seq)` بعد نجاح التحقق. خريطة بتات بعرض 64.

## 11.6 `audio/codec.py`
ثوابت الصوت (`SAMPLE_RATE = 16000`، `FRAME_SAMPLES = 320`)، والصنفان `PCM16` و `ULaw` (جداول NumPy)، و `level_db`.

## 11.7 `audio/jitter.py`
`JitterBuffer.push(frame_no, pcm)` و `pop()`، مع عدادات `lost` و `late` و `concealed` و `dropped`. محمي بقفل لأن `push`
من خيط الاستقبال و `pop` من خيط كرت الصوت.

## 11.8 `audio/devices.py`

| الصنف | الاستخدام |
|---|---|
| `SoundDeviceBackend` | ميكروفون وسماعة حقيقيان (`RawInputStream` / `RawOutputStream` بإطار 320 عينة) |
| `ToneInputBackend` | نغمة اختبار بدل الميكروفون + سماعة حقيقية |
| `FakeAudioBackend` | صوت اصطناعي بالكامل للاختبارات (يسجل ما التُقط وما شُغّل) |
| `make_backend()` | يختار المناسب تلقائياً (إذا لا توجد أجهزة صوت ← Fake) |
| `list_devices()` | أجهزة واجهة الصوت الافتراضية فقط (MME على Windows) لتجنب التكرار |

## 11.9 `net/packet.py`
`build_header(type, seq, ts)` و `parse(packet)` ← `(type, seq, ts, header, ciphertext)` أو `PacketError`.

## 11.10 `session.py` — قلب النظام

| الدالة | الخيط | الوظيفة |
|---|---|---|
| `start_listen()` / `start_call(host)` | الواجهة | تشغيل خيط `_run` |
| `_run(listen, host)` | control | ربط UDP ← TCP ← المصافحة ← `_start_media` ← حدث connected ← `_control_loop` |
| `_start_media()` | control | إنشاء 4 كائنات تشفير + الترميز + نافذة التكرار + مخزن الارتعاش + خيطي الإرسال والاستقبال + الصوت |
| `_on_capture(pcm)` | PortAudio | وضع الإطار في الطابور فقط |
| `_on_playback()` | PortAudio | `jitter.pop()` |
| `_seal(type, payload, ts)` | sender/receiver | رقم تسلسل جديد + ترويسة + Nonce + تشفير |
| `_sender_loop()` | sender | الإطار ← كتم؟ ← ترميز ← تشفير ← هجوم محاكى؟ ← إرسال ← PING |
| `_receiver_loop()` | receiver | تحليل ← تكرار؟ ← فك وتحقق ← PING/PONG/VOICE ← jitter |
| `_send_ctl / _control_loop` | control | رسائل التحكم المشفرة |
| `simulate_attack(kind)` | الواجهة | tamper / forge تُنفّذ على الحزمة التالية، replay فوراً |
| `snapshot()` | الواجهة | قاموس الإحصائيات للعرض |
| `hangup()` / `_shutdown()` | أي | BYE ← إيقاف الصوت ← إغلاق المنافذ ← حدث ended |

**الأحداث** المرسلة للواجهة عبر `on_event(kind, data)`: `state`، `log`، `connected`، `chat`، `alert`، `error`، `ended`.

## 11.11 `gui/main_window.py`

- `Bridge(QObject)` مع `Signal(str, object)`: ينقل أحداث المحرك من خيوط الخلفية إلى خيط الواجهة بأمان.
- `MainWindow`: يبني الترويسة، ولوحة الإعدادات، ولوحة الحالة، و7 تبويبات.
- `_start()`: يقرأ الإعدادات ← `CallConfig` ← `CallSession` ← listen أو call.
- `_on_event()`: يحدّث الواجهة حسب الحدث.
- `_tick()` كل 500ms: يحسب معدل البت من فرق البايتات، ويحدّث البطاقات والرسوم والمؤشرات وجدول الحزم.
- `BenchThread(QThread)`: يشغل المقارنة في الخلفية حتى لا تتجمد الواجهة.

## 11.12 `gui/widgets.py`
`StatCard`، `LevelMeter`، `LiveChart` (رسم خطي حي بـ QPainter)، `BarChart` (أعمدة بمقياس لوغاريتمي).

## 11.13 أدوات `tools/`

| الأداة | الوظيفة |
|---|---|
| `tools/screenshots.py` | يشغّل نافذتين ويُجري مكالمة وهجمات ويلتقط كل صور `docs/images` تلقائياً |
| `tools/make_charts.py` | يشغّل المقارنة و 3 مكالمات حقيقية ويرسم كل رسوم `docs/images/charts` |

## 11.14 إضافة خوارزمية جديدة (مثال للتوسعة)

1. أنشئ صنفاً يرث `AEADCipher` في `ciphers.py` مع `id` جديد (مثلاً 4).
2. أضفه إلى `CIPHERS`.
3. أضف اسمه في `CIPHER_LABELS` في `main_window.py`.

كل شيء آخر (المصافحة، الحزم، المقارنة، الاختبارات المعلمة بـ `CIPHERS`) يعمل تلقائياً.

</div>
