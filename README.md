# HTML2APK Studio

تبدیل فایل HTML به APK واقعی Android — بدون Android Studio، بدون کدنویسی.

---

## ویژگی‌ها

- ساخت APK واقعی با Gradle (نه WebView ساده)
- پشتیبانی از JavaScript Bridge — دسترسی به Camera، Vibration، Clipboard، Network، Toast
- تنظیم Package Name، نسخه، جهت صفحه، Fullscreen
- آیکون سفارشی با تبدیل خودکار به همه سایزها
- Build Log زنده در GUI
- قابل توزیع به صورت Portable EXE (بدون نیاز به نصب چیزی)

---

## نصب سریع (برای توسعه‌دهنده)

**پیش‌نیازها:**
- Python 3.10+
- Java 17+ (یا Android Studio)
- Android SDK با `build-tools;34.0.0` و `platforms;android-34`

```bash
pip install customtkinter Pillow
python app.py
```

---

## ساخت نسخه Portable (EXE بدون نیاز به نصب)

یه‌بار روی یه کامپیوتر با اینترنت اجرا کن:

```bash
python setup_portable.py
```

این اسکریپت:
1. Java 17 JRE portable رو دانلود می‌کنه
2. Android SDK (build-tools + platform-34) رو دانلود می‌کنه
3. Gradle 8.7 رو برای استفاده آفلاین دانلود می‌کنه
4. EXE می‌سازه

نتیجه: پوشه `dist/HTML2APK_Studio/` که می‌تونی zip کنی و به دوستات بدی.

---

## ساختار پروژه

```
HTML2APK_Studio/
├── app.py                  ← برنامه اصلی (GUI + Build Logic)
├── setup_portable.py       ← ساخت نسخه portable آفلاین
├── setup_sdk.py            ← بررسی و راه‌اندازی محیط توسعه
├── build_exe.bat           ← ساخت EXE با PyInstaller
├── android_template/       ← پروژه Android (template برای Gradle)
│   ├── app/src/main/
│   │   ├── java/           ← MainActivity + JS Bridge plugins
│   │   └── assets/www/     ← html2apk.js + index.html پیش‌فرض
│   └── gradle/wrapper/
└── .gitignore
```

---

## JS Bridge (html2apk.js)

وقتی APK رو می‌سازی، `html2apk.js` به صورت خودکار داخل WebView تزریق میشه:

```javascript
// Toast
H2ABridge.call('toast', { message: 'سلام!' });

// Vibration
H2ABridge.call('vibration', { duration: 500 });

// Clipboard
H2ABridge.call('clipboard', { action: 'copy', text: 'متن' });

// Network status
H2ABridge.call('network', { action: 'status' }, (result) => {
    console.log(result.connected);
});

// Device info
H2ABridge.call('device', { action: 'info' }, (result) => {
    console.log(result.model, result.sdk);
});
```

---

## توزیع برای دوستان

بعد از اجرای `setup_portable.py`:

```
dist\HTML2APK_Studio\   ← این پوشه رو zip کن
├── HTML2APK_Studio.exe ← دوستات فقط اینو اجرا می‌کنن
├── _internal\
└── tools\              ← Java + SDK + Gradle (آفلاین)
```

حجم zip نهایی: ~350-400 MB

---

## لایسنس

MIT
