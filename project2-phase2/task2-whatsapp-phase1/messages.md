# Bot Messages

## Bright Smile Dental Clinic

**Niche:** Dental Clinic

**Languages Supported:**
- English
- Arabic

These message scripts are designed for the WhatsApp Lead-to-Booking Automation (Phase 1).

---

## State 1 — Greeting + Intent
**EN:**
```
Welcome to Bright Smile Dental Clinic 🦷
Would you like to book an appointment, or do you have a question?
1. Book an appointment
2. Ask a question
```
**AR:**
```
مرحباً بكم في عيادة برايت سمايل لطب الأسنان 🦷
هل تودون حجز موعد أم لديكم سؤال؟
1. حجز موعد
2. طرح سؤال
```

---

## FAQ Answer (loops back to State 1)
**EN:**
```
Thanks for your question! Our clinic is open Saturday–Thursday, 10 AM to 8 PM.
Would you like to book an appointment now, or ask something else?
1. Book an appointment
2. Ask another question
```
**AR:**
```
شكراً لسؤالكم! عيادتنا مفتوحة من السبت إلى الخميس، من 10 صباحاً حتى 8 مساءً.
هل تودون حجز موعد الآن، أم لديكم سؤال آخر؟
1. حجز موعد
2. سؤال آخر
```

---

## State 2 — Select Service
**EN:**
```
Great! Which service are you interested in?
1. Check-up & Cleaning
2. Teeth Whitening
3. Braces Consultation
4. Other
```
**AR:**
```
رائع! ما هي الخدمة التي تهتمون بها؟
1. فحص وتنظيف
2. تبييض الأسنان
3. استشارة تقويم الأسنان
4. أخرى
```

---

## State 3 — Choose Preferred Date & Time
**EN:**
```
Perfect. When would you like to come in?
Just tell me a day and time that works for you (e.g. "Tuesday afternoon").
```
**AR:**
```
ممتاز. متى تودون الحضور؟
أخبرونا باليوم والوقت المناسبين لكم (مثلاً: "الثلاثاء بعد الظهر").
```

---

## State 4 — Offer Available Time Slots
**EN:**
```
Here are the available slots close to your preferred time:
1. Tuesday, 3:00 PM
2. Tuesday, 5:00 PM
3. Wednesday, 11:00 AM
Which one works for you?
```
**AR:**
```
إليكم المواعيد المتاحة القريبة من وقتكم المفضل:
1. الثلاثاء، 3:00 مساءً
2. الثلاثاء، 5:00 مساءً
3. الأربعاء، 11:00 صباحاً
أي موعد يناسبكم؟
```

---

## State 5 — Booking Summary & Confirmation
**EN:**
```
Here's your booking summary:
Service: {service}
Date: {date}
Time: {time}
Shall I confirm this appointment for you?
1. Yes, confirm
2. No, change the time
```
**AR:**
```
إليكم ملخص حجزكم:
الخدمة: {service}
التاريخ: {date}
الوقت: {time}
هل نؤكد لكم هذا الموعد؟
1. نعم، تأكيد
2. لا، تغيير الوقت
```

**Confirmation success message:**
**EN:**
```
You're all set! ✅
We look forward to seeing you at Bright Smile Dental Clinic.
Reply STOP if you ever need to cancel.
```
**AR:**
```
تم تأكيد موعدكم! ✅
نتطلع لرؤيتكم في عيادة برايت سمايل لطب الأسنان.
للإلغاء في أي وقت، أرسلوا كلمة STOP.
```

---

## Nudge +1h (free-form message)
**EN:**
```
Hi again! Just checking in — are you still looking to book your dental appointment?
I'm here whenever you're ready 🙂
```
**AR:**
```
مرحباً مجدداً! أردنا الاطمئنان — هل ما زلتم ترغبون بحجز موعدكم؟
نحن هنا عندما تكونون جاهزين 🙂
```

---

## Nudge +24h (template message — needs Meta approval in real deployment)
**EN:**
```
Hi {name}, we noticed you started booking with Bright Smile Dental Clinic but didn't finish.
Reply YES to continue where you left off.
```
**AR:**
```
مرحباً {name}، لاحظنا أنكم بدأتم بحجز موعد ولم تكملوا العملية.
أرسلوا "نعم" للمتابعة من حيث توقفتم.
```

---

## Nudge +72h (template message — needs Meta approval in real deployment)
**EN:**
```
Hi {name}, final reminder from Bright Smile Dental Clinic — your slot request is still open.
Reply YES to keep it, or we'll close this request.
```
**AR:**
```
مرحباً {name}، تذكير أخير من عيادة برايت سمايل — طلب حجزكم ما زال مفتوحاً.
أرسلوا "نعم" للاحتفاظ به، وإلا سنغلق الطلب.
```

---

## Human Handoff
**EN:**
```
Thanks for reaching out — this needs a bit more personal attention,
so I'm connecting you with one of our team members. They'll be with you shortly!
```
**AR:**
```
شكراً لتواصلكم — هذا الأمر يحتاج اهتماماً شخصياً أكثر،
لذلك سأقوم بتوصيلكم بأحد أعضاء فريقنا. سيكونون معكم قريباً!
```
