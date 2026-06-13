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

HTML2APK Studio is a Windows desktop GUI that compiles your HTML/CSS/JS project into a **real Android APK** using Gradle — not a simple wrapper, but a full Android project with a native JavaScript Bridge.

Pick your HTML → fill in the app name → hit Build. Done.

---

## Features

| | |
|---|---|
| **Real APK** | Full Gradle build pipeline — not a fake wrapper |
| **JS Bridge** | 5 native plugins accessible from JavaScript |
| **Custom icon** | Auto-resized to all Android densities |
| **Orientation** | Portrait / Landscape / Sensor (auto) |
| **Fullscreen** | Hide status bar with one checkbox |
| **Live build log** | See Gradle output in real time |

---

## Two Ways to Use

### Option A — Run from Source (Developer)

Best if you already have Java + Android SDK installed, or want to contribute.

**Requirements:**
- Python 3.10+
- Java 17+ (or Android Studio's bundled JDK)
- Android SDK with `build-tools;34.0.0` + `platforms;android-34`

**Steps:**
```bash
# 1. Clone the repo
git clone https://github.com/Mohammadmahdi-rfe/HTML2APK.git
cd HTML2APK

# 2. Install Python dependencies
pip install customtkinter Pillow

# 3. Verify your environment (optional but recommended)
python setup_sdk.py

# 4. Launch the app
python app.py
```

---

### Option B — Portable EXE (Zero Install)

Best for sharing with others. Run once on any machine with internet, get a folder you can zip and share — recipients need nothing installed.

**Steps:**
```bash
# 1. Clone and enter the project
git clone https://github.com/Mohammadmahdi-rfe/HTML2APK.git
cd HTML2APK

# 2. Install Python (only needed for this step)
pip install customtkinter Pillow pyinstaller

# 3. Run the portable setup — downloads Java, Android SDK, Gradle automatically
python setup_portable.py
# → Prompts you to build the EXE at the end (press y)
```

This creates `dist/HTML2APK_Studio/` — zip it and share it.

**What's inside the zip:**
```
HTML2APK_Studio/
├── HTML2APK_Studio.exe   ← just double-click this
├── _internal/            ← Python runtime (do not touch)
└── tools/
    ├── jre/              ← Java 17 portable (no install needed)
    ← sdk/              ← Android SDK (build-tools + platform-34)
    └── gradle-8.7-bin.zip ← Gradle offline
```

> **Zip size:** ~350–400 MB after compression

---

## JavaScript Bridge

`html2apk.js` is automatically injected into every page your app loads.

```javascript
document.addEventListener('html2apkready', function () {

  // Show a toast notification
  H2ABridge.call('toast', { message: 'Hello!' });

  // Vibrate for 300ms
  H2ABridge.call('vibration', { duration: 300 });

  // Copy text to clipboard
  H2ABridge.call('clipboard', { action: 'copy', text: 'some text' }, function(r) {
    console.log('copied:', r.success);
  });

  // Check network status
  H2ABridge.call('network', { action: 'status' }, function(r) {
    console.log('online:', r.connected, '| type:', r.type);
  });

  // Get device info
  H2ABridge.call('device', { action: 'info' }, function(r) {
    console.log(r.manufacturer, r.model, 'Android', r.version);
  });

});
```

> If running in a browser (not inside the APK), `window.H2ABridge` is `undefined` — handle gracefully with a simple `if (window.H2ABridge)` check.

---

## Project Structure

```
HTML2APK/
├── app.py                        ← Main GUI + build logic
├── setup_sdk.py                  ← Dev environment checker (Option A)
├── setup_portable.py             ← Downloads everything + builds EXE (Option B)
├── build_exe.bat                 ← Builds EXE only (if tools/ already exists)
├── android_template/             ← Android Gradle project used as build template
│   ├── app/
│   │   ├── build.gradle
│   │   └── src/main/
│   │       ├── AndroidManifest.xml
│   │       ├── assets/www/
│   │       │   └── html2apk.js   ← JS Bridge (auto-injected)
│   │       ├── java/.../
│   │       │   ├── MainActivity.java
│   │       │   ├── H2ABridge.java
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
User selects HTML file + icon
          ↓
APKBuilder copies android_template/ → temp dir
          ↓
Placeholders replaced: {{PACKAGE_NAME}}, {{APP_NAME}}, {{VERSION}}, ...
          ↓
User's HTML copied into assets/www/index.html
Icons resized to all densities
          ↓
gradlew assembleDebug (Gradle compiles Java → DEX → APK)
          ↓
APK saved next to the original HTML file
```

---

## Build Placeholders

| Placeholder | Example |
|---|---|
| `{{PACKAGE_NAME}}` | `com.myname.myapp` |
| `{{APP_NAME}}` | `My App` |
| `{{VERSION_NAME}}` | `1.0` |
| `{{VERSION_CODE}}` | `1` |
| `{{ORIENTATION}}` | `portrait` / `landscape` / `sensor` |
| `{{JS_ENABLED}}` | `true` |
| `{{ZOOM_ENABLED}}` | `false` |
| `{{FULLSCREEN_CODE}}` | *(injected Java)* |

---

## License

MIT
