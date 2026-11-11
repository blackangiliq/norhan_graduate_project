<div dir="rtl">

# 12. هيكل تقرير التخرج المقترح والمراجع

[⬅ العودة للصفحة الرئيسية](../README.md)

> كل المخططات في `docs/images/diagrams/` والرسوم في `docs/images/charts/` والصور في `docs/images/` جاهزة للإدراج في التقرير
> بدقة عالية. كل ملف في `docs/` يقابل جزءاً من التقرير.

## الفصل الأول: المقدمة
1.1 مقدمة عامة عن الاتصالات الصوتية الرقمية (VoIP) ← [01](01_project_overview.md)
1.2 مشكلة البحث
1.3 أهداف المشروع
1.4 أهمية المشروع
1.5 نطاق المشروع وحدوده
1.6 منهجية العمل
1.7 هيكل التقرير

## الفصل الثاني: الخلفية النظرية والدراسات السابقة
2.1 أساسيات التشفير: المتماثل وغير المتماثل، الكتلي والتياري ← [03](03_cryptography.md)
2.2 التشفير الموثّق AEAD
2.3 التشفير خفيف الوزن ومسابقة NIST LWC
2.4 خوارزمية Ascon (البنية الإسفنجية، التبديل، الأمان)
2.5 خوارزميتا AES-GCM و ChaCha20-Poly1305
2.6 تبادل المفاتيح Diffie-Hellman والمنحنيات الإهليلجية X25519
2.7 دوال اشتقاق المفاتيح HKDF و PBKDF2
2.8 نقل الصوت عبر الشبكات: أخذ العينات، الترميز، RTP، SRTP، الارتعاش ← [05](05_audio_pipeline.md)
2.9 الدراسات السابقة (جدول مقارنة: الدراسة، الخوارزمية، المنصة، النتائج، الفرق عن مشروعنا)

## الفصل الثالث: تحليل وتصميم النظام
3.1 المتطلبات الوظيفية وغير الوظيفية
3.2 المعمارية العامة ← [02](02_system_architecture.md) + `01_architecture.png`
3.3 مخطط سير البرنامج ← `05_program_flowchart.png`
3.4 مخطط حالات المكالمة ← `06_state_machine.png`
3.5 تصميم البروتوكول والمصافحة ← [04](04_protocol_and_transport.md) + `02_handshake_sequence.png`
3.6 تصميم اشتقاق المفاتيح ← `07_key_derivation.png`
3.7 تصميم حزمة الصوت ← `11_packet_format.png`
3.8 مخططا الإرسال والاستقبال ← `03_sender_flowchart.png` و `04_receiver_flowchart.png`
3.9 تصميم الخيوط والتزامن ← `10_threads.png`
3.10 نموذج التهديد ← `12_attack_model.png`

## الفصل الرابع: التنفيذ
4.1 بيئة العمل والأدوات
4.2 تنفيذ Ascon-128 (مقتطفات من `ascon.py` مع الشرح) ← [11](11_code_walkthrough.md)
4.3 تنفيذ المصافحة
4.4 تنفيذ قنوات النقل
4.5 تنفيذ معالجة الصوت
4.6 الواجهة الرسومية (الصور من `docs/images`) ← [07](07_user_guide.md)
4.7 التحويل إلى برنامج Windows مستقل

## الفصل الخامس: الاختبار والنتائج
5.1 منهجية الاختبار ← [08](08_testing_and_results.md)
5.2 اختبارات الصحة (KAT)
5.3 الاختبارات الوظيفية والتكاملية
5.4 الاختبارات الأمنية (محاكاة الهجمات) ← [09](09_security_analysis.md)
5.5 قياس الأداء والمقارنة بين الخوارزميات (الرسوم 01–04)
5.6 تحليل التأخير وعرض النطاق (الرسوم 03 و 05)
5.7 مناقشة النتائج

## الفصل السادس: الخاتمة والأعمال المستقبلية
6.1 الخلاصة
6.2 القيود
6.3 الأعمال المستقبلية

## الملاحق
- أ: دليل التثبيت والتشغيل ← [06](06_installation_windows.md)
- ب: الكود المصدري الرئيسي
- ج: متجهات الاختبار ونتائج الاختبارات

---

## المراجع العلمية المقترحة

1. C. Dobraunig, M. Eichlseder, F. Mendel, M. Schläffer, "**Ascon v1.2: Lightweight Authenticated Encryption and Hashing**," *Journal of Cryptology*, vol. 34, no. 33, 2021.
2. NIST, "**SP 800-232: Ascon-Based Lightweight Cryptography Standards for Constrained Devices**," 2025.
3. NIST, "**Lightweight Cryptography Standardization Process**," <https://csrc.nist.gov/projects/lightweight-cryptography>
4. M. S. Turan et al., "**Status Report on the Final Round of the NIST Lightweight Cryptography Standardization Process**," NIST IR 8454, 2023.
5. Y. Nir, A. Langley, "**ChaCha20 and Poly1305 for IETF Protocols**," RFC 8439, 2018.
6. NIST, "**Advanced Encryption Standard (AES)**," FIPS 197, 2001 (updated 2023).
7. M. Dworkin, "**Recommendation for Block Cipher Modes of Operation: Galois/Counter Mode (GCM) and GMAC**," NIST SP 800-38D, 2007.
8. A. Langley, M. Hamburg, S. Turner, "**Elliptic Curves for Security**," RFC 7748, 2016 (X25519).
9. D. J. Bernstein, "**Curve25519: new Diffie-Hellman speed records**," PKC 2006.
10. H. Krawczyk, P. Eronen, "**HMAC-based Extract-and-Expand Key Derivation Function (HKDF)**," RFC 5869, 2010.
11. K. Moriarty et al., "**PKCS #5: Password-Based Cryptography Specification Version 2.1**," RFC 8018, 2017 (PBKDF2).
12. E. Rescorla, "**The Transport Layer Security (TLS) Protocol Version 1.3**," RFC 8446, 2018 (بناء الـ Nonce).
13. M. Baugher et al., "**The Secure Real-time Transport Protocol (SRTP)**," RFC 3711, 2004.
14. H. Schulzrinne et al., "**RTP: A Transport Protocol for Real-Time Applications**," RFC 3550, 2003 (حساب الارتعاش).
15. P. Zimmermann, A. Johnston, J. Callas, "**ZRTP: Media Path Key Agreement for Unicast Secure RTP**," RFC 6189, 2011 (رمز الأمان SAS).
16. S. Kent, "**IP Encapsulating Security Payload (ESP)**," RFC 4303, 2005 (نافذة منع التكرار).
17. ITU-T, "**G.711: Pulse code modulation (PCM) of voice frequencies**," 1988.
18. ITU-T, "**G.114: One-way transmission time**," 2003.
19. CAESAR Competition, "**Final Portfolio**," 2019, <https://competitions.cr.yp.to/caesar-submissions.html>

</div>
