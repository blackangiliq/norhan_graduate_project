<div dir="rtl">

# 6. التثبيت والتشغيل على Windows — دليل مفصّل لجهازين

[⬅ العودة للصفحة الرئيسية](../README.md)

## 6.1 المتطلبات

| | الحد الأدنى |
|---|---|
| نظام التشغيل | Windows 10 أو 11 (64-bit) |
| المعالج / الذاكرة | أي معالج حديث / 4 GB RAM |
| الصوت | ميكروفون وسماعة (يُفضّل سماعة رأس بميكروفون لكل جهاز) |
| الشبكة | الجهازان على نفس الشبكة المحلية |
| البرامج | Python 3.10+ (غير مطلوب إذا استخدمت ملف exe) |

## 6.2 الخيار A: ملف exe الجاهز (بدون Python)

1. افتح صفحة المستودع ← **Actions** ← **Test & Build Windows EXE** ← آخر تشغيل باللون الأخضر.
2. أسفل الصفحة في **Artifacts** نزّل **SecureVoice-Windows** (يتطلب تسجيل الدخول في GitHub).
   وإذا كان هناك **Release** منشور فالملف موجود أيضاً في صفحة Releases.
3. فك الضغط مرتين حتى تصل إلى مجلد `SecureVoice`.
4. انسخ المجلد كاملاً إلى الجهازين (عبر USB مثلاً) وشغّل `SecureVoice.exe`.
5. إذا ظهرت رسالة **Windows protected your PC** ← More info ← Run anyway (لأن البرنامج غير موقّع رقمياً).

## 6.3 الخيار B: من الكود المصدري

### 1) تثبيت Python
- <https://www.python.org/downloads/> ← Download Python 3.12.
- في أول شاشة ✅ **Add python.exe to PATH** ثم Install Now.
- للتحقق افتح CMD واكتب:

</div>

```bash
python --version
```

<div dir="rtl">

### 2) تنزيل المشروع
GitHub ← زر **Code** ← **Download ZIP** ← فك الضغط في مكان بسيط مثل `C:\SecureVoice`.

### 3) التثبيت
انقر مرتين على `install.bat`. سيُنشئ مجلد `.venv` ويثبت المكتبات (≈ 200 MB، مرة واحدة فقط). أو يدوياً:

</div>

```bash
cd C:\SecureVoice
```

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

<div dir="rtl">

### 4) التشغيل
انقر مرتين على `run.bat`، أو:

</div>

```bash
python main.py
```

<div dir="rtl">

### 5) بناء exe بنفسك (اختياري)
`build_exe.bat` ← الناتج `dist\SecureVoice\SecureVoice.exe`. انسخ مجلد `dist\SecureVoice` كاملاً للجهاز الآخر.

## 6.4 تجهيز الشبكة

### الخيار 1: نفس الراوتر/Wi-Fi
اربط الجهازين بنفس الشبكة. في كل جهاز افتح CMD:

</div>

```bash
ipconfig
```

<div dir="rtl">

ابحث عن **IPv4 Address** تحت محول Wi-Fi أو Ethernet (مثل `192.168.1.10`). البرنامج يعرضه أيضاً أعلى الشاشة.

### الخيار 2 (الأضمن يوم المناقشة): Hotspot من الهاتف
فعّل نقطة الاتصال في الهاتف واربط الجهازين بها. لا يحتاج إنترنت فعلياً (البيانات بين الجهازين لا تمر بالإنترنت).
مفيد لأن شبكات الجامعات غالباً تفعّل **عزل العملاء (Client Isolation)** الذي يمنع الأجهزة من رؤية بعضها.

### الخيار 3: كابل Ethernet مباشر
اربط الجهازين بكابل، ثم أعطِ كل جهاز IP يدوياً من: Control Panel ← Network Connections ← Ethernet ← Properties ←
IPv4 (الجهاز A: `192.168.10.1`، الجهاز B: `192.168.10.2`، Subnet `255.255.255.0`).

### اختبار الوصول
من الجهاز B:

</div>

```bash
ping 192.168.1.10
```

<div dir="rtl">

إذا لم يرد: الجدار الناري يحجب ICMP (طبيعي) أو الشبكة معزولة. جرّب الاتصال من البرنامج مباشرة بعد خطوة الجدار الناري.

## 6.5 الجدار الناري (Windows Defender Firewall)

**الطريقة السهلة:** شغّل `firewall.bat` على **الجهازين** ووافق على صلاحيات المسؤول. سيضيف:

</div>

```bash
netsh advfirewall firewall add rule name="SecureVoice TCP" dir=in action=allow protocol=TCP localport=5000 profile=any
```

```bash
netsh advfirewall firewall add rule name="SecureVoice UDP" dir=in action=allow protocol=UDP localport=5001-5002 profile=any
```

<div dir="rtl">

**ملاحظة:** عند أول تشغيل قد تظهر نافذة «Windows Defender Firewall has blocked some features» ← فعّل **Private** و **Public** ← Allow access.

**لإزالة القواعد لاحقاً:**

</div>

```bash
netsh advfirewall firewall delete rule name="SecureVoice TCP"
```

```bash
netsh advfirewall firewall delete rule name="SecureVoice UDP"
```

<div dir="rtl">

## 6.6 إجراء المكالمة

| الخطوة | الجهاز A (المستقبل) | الجهاز B (المتصل) |
|---|---|---|
| 1 | الوضع: **استقبال مكالمة** | — |
| 2 | كلمة السر: مثلاً `mykey123` | — |
| 3 | اختر الميكروفون والسماعة | — |
| 4 | **📞 بدء الاستقبال** ← «بانتظار مكالمة واردة...» | — |
| 5 | — | الوضع: **إجراء مكالمة** |
| 6 | — | IP الطرف الآخر: عنوان A |
| 7 | — | نفس كلمة السر + اختر **Ascon-128** والترميز |
| 8 | — | **📞 اتصال** |
| 9 | ✅ مكالمة آمنة + رمز أمان | ✅ مكالمة آمنة + **نفس** رمز الأمان |

## 6.7 تجربة على جهاز واحد (قبل الحصول على جهاز ثانٍ)

1. شغّل البرنامج **مرتين** (`run.bat` مرتين).
2. النافذة 1: استقبال، UDP = 5001.
3. النافذة 2: اتصال إلى `127.0.0.1`، **UDP = 5002**، نفس كلمة السر.
4. في إحدى النافذتين اختر «🎵 نغمة اختبار» كميكروفون لتجنب التغذية الراجعة (صفير).

أو من سطر الأوامر:

</div>

```bash
python -m securevoice.cli listen --password test --tone
```

```bash
python -m securevoice.cli call 127.0.0.1 --password test --udp-port 5002 --tone
```

<div dir="rtl">

## 6.8 حل المشاكل

| العَرَض | السبب المحتمل | الحل |
|---|---|---|
| `'python' is not recognized` | لم يُضف إلى PATH | أعد تثبيت Python مع تفعيل Add to PATH |
| فشل `pip install` | لا يوجد إنترنت / بروكسي | اتصل بالإنترنت، أو استخدم exe الجاهز |
| `خطأ في الشبكة: [WinError 10061]` (refused) | A لم يبدأ الاستقبال أو IP/منفذ خاطئ | ابدأ A أولاً، تحقق من IP |
| `timed out` | الجدار الناري على A أو عزل الشبكة | `firewall.bat` على A، أو Hotspot |
| `فشلت المصافحة: wrong password` | كلمة سر مختلفة | وحّد كلمة السر (حساسة لحالة الأحرف) |
| متصل لكن لا صوت + تحذير UDP | الجدار الناري يحجب UDP | `firewall.bat` على **الجهازين** |
| عداد «حزم مستقبلة» يزيد لكن لا صوت | السماعة الخاطئة | اختر السماعة الصحيحة قبل البدء |
| الطرف الآخر لا يسمعني ومؤشر الميكروفون -90 dB | الميكروفون الخاطئ أو محجوب | Settings ← Privacy ← Microphone ← Allow apps |
| صفير/صدى | الميكروفون يلتقط السماعة | سماعات رأس |
| `Error opening InputStream` | الجهاز لا يدعم الإعداد | اختر جهازاً آخر من القائمة أو «الافتراضي» |
| البرنامج لا يفتح (exe) | مكافح الفيروسات | أضف المجلد للاستثناءات، أو استخدم `run_console.bat` لرؤية الخطأ |

</div>
