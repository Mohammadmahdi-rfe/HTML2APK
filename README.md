<div align="center">

<img src="https://img.shields.io/badge/platform-Windows-blue?style=flat-square&logo=windows" alt="Platform">
<img src="https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square&logo=python" alt="Python">
<img src="https://img.shields.io/badge/gradle-8.7-02303A?style=flat-square&logo=gradle" alt="Gradle">
<img src="https://img.shields.io/badge/android-API%2034-green?style=flat-square&logo=android" alt="Android">
<img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License">

# ⚡ HTML2APK Studio

**Turn any HTML file into a real Android APK — no Android Studio, no coding required.**

</div>

---

## What is this?

HTML2APK Studio is a desktop GUI app (Windows) that compiles your HTML/CSS/JS project into a **real, signed Android APK** using Gradle under the hood — not a simple WebView wrapper, but a proper Android project with a native JavaScript Bridge.

Just pick your HTML file, fill in the app name and package, hit build — done.

---

## Features

| Feature | Details |
|---------|---------|
| **Real APK** | Full Gradle build — not a fake wrapper |
| **JS Bridge** | Native Android APIs accessible from your HTML via `H2ABridge` |
| **5 built-in plugins** | Toast · Vibration · Clipboard · Network · Device Info |
| **Custom icon** | Auto-resized to all Android densities (mdpi → xxxhdpi) |
| **Orientation** | Portrait / Landscape / Sensor (auto) |
| **Fullscreen mode** | Hide status bar with one checkbox |
| **Live build log** | See Gradle output in real time |
| **Portable EXE** | One-click build → share with anyone, zero install needed |

---

## Quick Start (Developer)

**Prerequisites:** Python 3.10+, Java 17+, Android SDK (`build-tools;34.0.0` + `platforms;android-34`)

```bash
pip install customtkinter Pillow
python app.py
```

---

## Portable Distribution (Zero Install)

Run this **once** on any machine with internet:

```bash
python setup_portable.py
```

This downloads and bundles everything:
1. Java 17 JRE (portable, no install)
2. Android SDK — build-tools + platform-34
3. Gradle 8.7 (offline zip)
4. Builds the EXE via PyInstaller

Then zip `dist/HTML2APK_Studio/` and share it. Recipients just double-click the EXE — nothing to install.

```
dist/HTML2APK_Studio/
├── HTML2APK_Studio.exe   ← just run this
├── _internal/            ← Python runtime (do not touch)
└── tools/
    ├── jre/              ← Java 17 portable
    ├── sdk/              ← Android SDK
    └── gradle-8.7-bin.zip
```

> **Zip size:** ~350–400 MB after compression

---

## JavaScript Bridge

Every APK built with HTML2APK Studio automatically injects `html2apk.js` into the WebView. Use `H2ABridge.call()` from any HTML/JS:

```javascript
// Wait for bridge to be ready
document.addEventListener('html2apkready', function () {

  // Toast notification
  H2ABridge.call('toast', { message: 'Hello from JS!' });

  // Vibrate for 300ms
  H2ABridge.call('vibration', { duration: 300 });

  // Copy text to clipboard
  H2ABridge.call('clipboard', { action: 'copy', text: 'some text' }, function(r) {
    console.log('copied:', r.success);
  });

  // Check network status
  H2ABridge.call('network', { action: 'status' }, function(r) {
    console.log('online:', r.connected, 'type:', r.type);
  });

  // Get device info
  H2ABridge.call('device', { action: 'info' }, function(r) {
    console.log(r.manufacturer, r.model, 'Android', r.version, 'SDK', r.sdk);
  });

});
```

> Works both inside the APK and gracefully degrades in the browser (`window.H2ABridge` will be `undefined`).

---

## Project Structure

```
HTML2APK_Studio/
├── app.py                        ← Main GUI + APKBuilder logic
├── setup_portable.py             ← Downloads JRE + SDK + Gradle, builds EXE
├── setup_sdk.py                  ← Dev environment checker
├── build_exe.bat                 ← Builds EXE with PyInstaller
├── android_template/             ← Android Gradle project (template)
│   ├── app/
│   │   ├── build.gradle
│   │   └── src/main/
│   │       ├── AndroidManifest.xml
│   │       ├── assets/www/
│   │       │   ├── html2apk.js   ← JS Bridge (auto-injected)
│   │       │   └── index.html    ← Default demo (replaced by user's HTML)
│   │       ├── java/.../
│   │       │   ├── MainActivity.java
│   │       │   ├── H2ABridge.java
│   │       │   ├── H2APlugin.java
│   │       │   ├── ToastPlugin.java
│   │       │   ├── VibrationPlugin.java
│   │       │   ├── ClipboardPlugin.java
│   │       │   ├── NetworkPlugin.java
│   │       │   └── DevicePlugin.java
│   │       └── res/
│   └── gradle/wrapper/
├── .gitignore
└── README.md
```

---

## How It Works

```
User picks HTML + icon
        ↓
APKBuilder copies android_template/ to a temp dir
        ↓
Placeholders replaced: {{PACKAGE_NAME}}, {{APP_NAME}}, {{VERSION}}, ...
        ↓
User's HTML + resized icons copied into assets/
        ↓
gradlew assembleDebug runs (Gradle compiles Java → DEX → APK)
        ↓
APK saved next to the original HTML file
```

---

## Build Placeholders

The Android template uses these tokens, replaced automatically at build time:

| Placeholder | Example |
|------------|---------|
| `{{PACKAGE_NAME}}` | `com.myname.myapp` |
| `{{APP_NAME}}` | `My Awesome App` |
| `{{VERSION_NAME}}` | `1.0` |
| `{{VERSION_CODE}}` | `1` |
| `{{ORIENTATION}}` | `portrait` / `landscape` / `sensor` |
| `{{JS_ENABLED}}` | `true` |
| `{{ZOOM_ENABLED}}` | `false` |
| `{{FULLSCREEN_CODE}}` | *(injected Java code)* |

---

## License

MIT — use it, fork it, ship it.
