# Bounechada Auto — نسخة محلية (Offline Mirror)

نسخة محلية كاملة من الموقع `https://www.bounechadaauto.com/` — جميع الصفحات والصور
والخطوط والسيرفر جاهزة، بدون إنترنت (عدا خريطة Google وروابط التواصل).

---

## التشغيل

السيرفر شغّال حالياً على:

```
http://localhost:8000/
```

لإعادة تشغيله لاحقاً (إذا أُغلق):

```powershell
cd C:\Users\RDP.runnervmm7ud1\bounechada-auto
python serve.py 8000
```

ثم افتح `http://localhost:8000/` في المتصفح.
(لتغيير المنفذ: `python serve.py 8080`)

> **لا تفتح `index.html` بالنقر المزدوج** — المتصفحات تمنع تحميل الفيديو والخطوط
> عبر `file://`. استخدم دائماً السيرفر المحلي.

---

## محتوى المجلد

| المسار | الوصف |
|---|---|
| `index.html` | الصفحة الرئيسية (الواجهة، المخزون، الطلب، الماركات، الخدمات، الموقع) |
| `*.html` (19 ملف) | صفحات تفاصيل السيارات (BMW M3, Mercedes GLE, Porsche Cayenne, ...) |
| `images/` | صور السيارات بالتفصيل (11 موديل) |
| `voiture/` | صور فوتوغرافية عالية الدقة (BMW, Audi, Kia, Opel, Peugeot, Yamaha, Volkswagen, Livan) |
| `logo auto/`, `logo showroom/` | شعارات الماركات والشعار |
| `_fonts/` | خطوط Google (Bebas Neue, Barlow Condensed, Outfit, Cairo) بصيغة woff2 |
| `_media/` | فيديوهات بديلة (انظر الملاحظة أدناه) |
| `ar.css`, `ar.js` | أنماط وسكربت النسخة العربية / RTL |
| `favicon.svg`, `favicon.ico` | أيقونة الموقع |
| `_tools/` | سكربتات التنزيل والتحقق (احتفظ بها لإعادة التحديث) |
| `serve.py` | سيرفر محلي بسيط |

---

## ملاحظات مهمة

### الفيديوهات
الفيديوهات الخمسة في الموقع الأصلي كانت تشير إلى إصدارات GitHub لمستودع خاص
(`github.com/jeunenomade16-sudo/bounechada-auto/releases/...`) وهي **ترجع 404 حتى على
الموقع الأصلي** (لاحظ خطأ `ERR_BLOCKED_BY_ORB` عند فتح الموقع الحي).

لذلك وُلّدت بدائل محلية في `_media/` من صور الموقع نفسها (حركة Ken Burns بطيئة،
H.264) حتى تعمل الصفحة بدون إنترنت. لاستبدالها بفيديوهاتك الحقيقية:

```
_media/hero.mp4       ← فيديو الواجهة (hero)
_media/showroom.mp4   ← خلفية قسم "Notre showroom"
_media/video-1..3.mp4 ← فيديوهات دوّار الواجهة
```

### ما بقي خارجياً (عن قصد)
- **خريطة Google** (iframe) — تتطلب اتصالاً بالإنترنت
- **روابط التواصل**: WhatsApp, Facebook, TikTok, Ouedkniss
- **بريد وهاتف**: `bounechadaauto@gmail.com`, `+213770557221`

---

## إعادة تحديث النسخة

```powershell
cd C:\Users\RDP.runnervmm7ud1\bounechada-auto
python _tools\mirror.py .          # إعادة تنزيل الموقع
python _tools\postprocess.py       # الخطوط + الفيديوهات البديلة
python _tools\fixfonts.py          # توجيه الخطوط للنسخة المحلية
python _tools\verify.py            # فحص كل الروابط
```

---

## نتيجة الفحص

```
20 صفحة HTML          → كلها 200 OK
414 رابط محلي        → كلها موجودة (0 مفقود)
0 أخطاء شبكة          → عبر Chrome DevTools Protocol
أبعاد الصفحات        → مطابقة تماماً للموقع الأصلي
```
