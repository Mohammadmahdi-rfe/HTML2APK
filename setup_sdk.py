#!/usr/bin/env python3
"""
setup_sdk.py
────────────
این اسکریپت رو یه بار اجرا کن تا:
  ✔ محیط (SDK, Java) رو بررسی کنه
  ✔ gradle-wrapper.jar رو دانلود کنه
  ✔ همه چیز رو برای اجرای app.py آماده کنه

اجرا: python setup_sdk.py
"""

import os, sys, shutil, subprocess, urllib.request, hashlib
from pathlib import Path

BASE = Path(__file__).parent
TEMPLATE = BASE / "android_template"
WRAPPER_DIR = TEMPLATE / "gradle" / "wrapper"
WRAPPER_JAR = WRAPPER_DIR / "gradle-wrapper.jar"

def c(code, t): return f"\033[{code}m{t}\033[0m"
def ok(m):   print(c(92, f"  ✔  {m}"))
def info(m): print(c(96, f"  ●  {m}"))
def err(m):  print(c(91, f"  ✘  {m}"))
def warn(m): print(c(93, f"  ⚠  {m}"))
def head(m): print(c(1,  f"\n{'─'*50}\n  {m}\n{'─'*50}"))


# ─────────────────────────────────────────
# ۱. بررسی Java
# ─────────────────────────────────────────
def find_java_exe():
    """همه جا دنبال java.exe می‌گرده."""
    candidates = []

    # ۱. از JAVA_HOME
    jh = os.environ.get("JAVA_HOME")
    if jh:
        candidates.append(Path(jh) / "bin" / "java.exe")

    # ۲. از PATH
    w = shutil.which("java")
    if w:
        candidates.append(Path(w))

    # ۳. JDK بسته‌شده با Android Studio
    home = Path.home()
    as_jdk_roots = [
        Path("C:/Program Files/Android/Android Studio/jbr"),
        Path("C:/Program Files/Android/Android Studio/jre"),
        home / "AppData/Local/Android/Sdk/../studio" ,
    ]
    for root in as_jdk_roots:
        j = root / "bin" / "java.exe"
        if j.exists():
            candidates.append(j)

    # ۴. Program Files — همه نسخه‌های JDK/JRE
    for pf in [Path("C:/Program Files/Java"),
               Path("C:/Program Files/Eclipse Adoptium"),
               Path("C:/Program Files/Microsoft"),
               Path("C:/Program Files/OpenJDK"),
               Path("C:/Program Files/Zulu"),
               Path("C:/Program Files/BellSoft")]:
        if pf.exists():
            for sub in sorted(pf.iterdir(), reverse=True):
                j = sub / "bin" / "java.exe"
                if j.exists():
                    candidates.append(j)

    # ۵. Android Studio bundled JDK (مسیر دقیق‌تر)
    as_path = Path("C:/Program Files/Android/Android Studio")
    for jdk_folder in ["jbr", "jre", "jdk"]:
        j = as_path / jdk_folder / "bin" / "java.exe"
        if j.exists():
            candidates.append(j)

    for c in candidates:
        if Path(c).exists():
            return str(c)
    return None


def check_java():
    head("Java JDK")
    java = find_java_exe()

    if java:
        r = subprocess.run([java, "-version"], capture_output=True, text=True)
        ver = (r.stderr or r.stdout).split("\n")[0]
        ok(f"Java پیدا شد: {ver}")
        ok(f"Path: {java}")
        # set برای بقیه مراحل
        os.environ["JAVA_HOME"] = str(Path(java).parent.parent)
        return True
    else:
        err("Java پیدا نشد!")
        print()
        info("راه‌حل ۱ — اگه Android Studio نصبه:")
        info("  Android Studio معمولاً JDK داره. مسیرش رو پیدا کن:")
        info("  C:\\Program Files\\Android\\Android Studio\\jbr\\bin\\java.exe")
        info("  بعد این دستور رو توی CMD اجرا کن:")
        info('  set JAVA_HOME=C:\\Program Files\\Android\\Android Studio\\jbr')
        info('  بعد دوباره python setup_sdk.py رو اجرا کن')
        print()
        info("راه‌حل ۲ — نصب JDK 17:")
        info("  https://adoptium.net  →  دانلود Windows x64 JDK 17")
        info("  بعد از نصب، دوباره این اسکریپت رو اجرا کن")
        print()
        # تلاش برای پیدا کردن مسیر Android Studio JDK
        as_jbr = Path("C:/Program Files/Android/Android Studio/jbr")
        if as_jbr.exists():
            warn(f"Android Studio JBR پیدا شد ولی set نیست:")
            warn(f"  {as_jbr}")
            warn(f"  این دستور رو توی CMD اجرا کن (به عنوان Admin):")
            warn(f'  setx JAVA_HOME "{as_jbr}" /M')
            warn(f'  بعد CMD رو ببند و دوباره باز کن و setup_sdk.py رو اجرا کن')
        return False


# ─────────────────────────────────────────
# ۲. بررسی Android SDK
# ─────────────────────────────────────────
def check_sdk():
    head("Android SDK")
    candidates = []
    home = Path.home()
    candidates += [
        home / "AppData" / "Local" / "Android" / "Sdk",
        Path("C:/Android/Sdk"),
        Path(os.environ.get("ANDROID_HOME","_none_")),
        Path(os.environ.get("ANDROID_SDK_ROOT","_none_")),
    ]

    sdk = None
    for p in candidates:
        if p.exists() and (p / "platforms").exists():
            sdk = p
            break

    if sdk:
        ok(f"Android SDK: {sdk}")
        # بررسی build-tools
        bt = sdk / "build-tools"
        if bt.exists():
            versions = list(bt.iterdir())
            ok(f"Build tools: {[v.name for v in versions]}")
        else:
            warn("Build tools پیدا نشد — Android Studio رو باز کن و SDK Manager رو اجرا کن")

        # بررسی platforms
        pl = sdk / "platforms"
        if pl.exists():
            platforms = list(pl.iterdir())
            ok(f"Platforms: {[p.name for p in platforms]}")
        else:
            warn("هیچ platform ای نصب نیست — android-34 رو از SDK Manager نصب کن")

        os.environ["ANDROID_HOME"] = str(sdk)
        return True
    else:
        err("Android SDK پیدا نشد!")
        err("Android Studio رو نصب کن: https://developer.android.com/studio")
        err("بعد SDK Manager رو باز کن و این رو نصب کن:")
        err("  - Android SDK Platform 34")
        err("  - Android SDK Build-Tools 34")
        err("  - Android SDK Platform-Tools")
        err("")
        err("سپس ANDROID_HOME رو set کن:")
        err("  set ANDROID_HOME=%LOCALAPPDATA%\\Android\\Sdk")
        return False


# ─────────────────────────────────────────
# ۳. دانلود gradle-wrapper.jar
# ─────────────────────────────────────────
def download_gradle_wrapper():
    head("Gradle Wrapper JAR")
    WRAPPER_DIR.mkdir(parents=True, exist_ok=True)

    if WRAPPER_JAR.exists():
        ok(f"gradle-wrapper.jar موجوده ({WRAPPER_JAR.stat().st_size // 1024} KB)")
        return True

    # gradle-wrapper.jar از releases رسمی Gradle
    url = (
        "https://github.com/gradle/gradle/raw/v8.1.1/"
        "gradle/wrapper/gradle-wrapper.jar"
    )

    # backup URL
    url2 = (
        "https://raw.githubusercontent.com/gradle/gradle/"
        "v8.4.0/gradle/wrapper/gradle-wrapper.jar"
    )

    for u in [url, url2]:
        info(f"دانلود gradle-wrapper.jar ...")
        try:
            def progress(b, bs, ts):
                if ts > 0:
                    pct = min(int(b*bs*40/ts), 40)
                    print(f"\r  [{'█'*pct}{'░'*(40-pct)}] {b*bs//1024}/{ts//1024} KB", end="")
            urllib.request.urlretrieve(u, WRAPPER_JAR, reporthook=progress)
            print()
            if WRAPPER_JAR.exists() and WRAPPER_JAR.stat().st_size > 10000:
                ok(f"gradle-wrapper.jar ({WRAPPER_JAR.stat().st_size // 1024} KB)")
                return True
            else:
                WRAPPER_JAR.unlink(missing_ok=True)
        except Exception as e:
            print()
            warn(f"نشد از {u}: {e}")

    # اگه دانلود نشد، از یه پروژه Android Studio موجود روی سیستم بگیر
    info("دنبال gradle-wrapper.jar روی سیستم می‌گردم...")
    search_paths = list(Path.home().glob("**/gradle-wrapper.jar"))
    if search_paths:
        src = search_paths[0]
        shutil.copy(src, WRAPPER_JAR)
        ok(f"از {src} کپی شد")
        return True

    err("gradle-wrapper.jar رو نتونستم دانلود کنم")
    err("دستی این کار رو بکن:")
    err("  ۱. هر پروژه Android که قبلاً ساختی رو باز کن")
    err(f"  ۲. فایل gradle/wrapper/gradle-wrapper.jar رو کپی کن")
    err(f"  ۳. بریزش توی: {WRAPPER_JAR}")
    return False


# ─────────────────────────────────────────
# ۴. تست Gradle
# ─────────────────────────────────────────
def test_gradle():
    head("تست Gradle")
    gradlew = TEMPLATE / "gradlew.bat"
    if not gradlew.exists():
        err("gradlew.bat پیدا نشد!")
        return False

    info("تست: gradlew --version ...")
    env = os.environ.copy()
    sdk = env.get("ANDROID_HOME","")
    java_home = env.get("JAVA_HOME","")

    result = subprocess.run(
        [str(gradlew), "--version"],
        cwd=TEMPLATE,
        env=env,
        capture_output=True,
        text=True,
        timeout=120
    )

    if result.returncode == 0:
        for line in result.stdout.split("\n"):
            if "Gradle" in line:
                ok(line.strip())
        return True
    else:
        warn("Gradle اولین بار ممکنه کمی طول بکشه برای دانلود...")
        info("خروجی: " + (result.stderr or result.stdout)[:200])
        return False


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    print(c(1, c(96, """
  ╔══════════════════════════════════════════╗
  ║   HTML2APK Studio — Environment Setup  ║
  ╚══════════════════════════════════════════╝
""")))

    java_ok = check_java()
    sdk_ok  = check_sdk()
    jar_ok  = download_gradle_wrapper()

    if java_ok and sdk_ok and jar_ok:
        gradle_ok = test_gradle()
    else:
        gradle_ok = False

    print(f"\n{c(1, '  ── نتیجه نهایی ──')}\n")
    for label, status in [
        ("Java JDK",           java_ok),
        ("Android SDK",        sdk_ok),
        ("gradle-wrapper.jar", jar_ok),
        ("Gradle test",        gradle_ok),
    ]:
        icon = c(92,"✔") if status else c(91,"✘")
        print(f"  {icon}  {label}")

    print()
    if java_ok and sdk_ok and jar_ok:
        print(c(92, c(1, "  ✅ محیط آماده‌ست! الان python app.py رو اجرا کن.")))
    else:
        print(c(91, "  ⚠ مشکلات بالا رو برطرف کن، بعد دوباره اجرا کن."))

    print()
    input("  Enter بزن...")

if __name__ == "__main__":
    main()
