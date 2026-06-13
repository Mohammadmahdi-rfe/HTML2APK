#!/usr/bin/env python3
"""
setup_portable.py
─────────────────
این اسکریپت رو یه‌بار روی یه کامپیوتر با اینترنت اجرا کن.

نتیجه: پوشه tools/ آماده میشه که شامل:
  ✔ tools/jre/         — Java 17 portable (نیاز به نصب نیست)
  ✔ tools/sdk/         — Android SDK (build-tools + platform-34)
  ✔ tools/gradle-8.7-bin.zip — Gradle آفلاین

بعدش با build_exe.bat یه EXE می‌سازی که بدی به دوستات.
دوستات فقط EXE + tools/ رو می‌خوان، چیزی نصب نمی‌کنن.
"""

import os, sys, shutil, subprocess, urllib.request, urllib.error, zipfile, json, ssl
from pathlib import Path

BASE  = Path(__file__).parent
TOOLS = BASE / "tools"

# ── رنگ‌بندی terminal ──────────────────────────────────────
def c(code, t): return f"\033[{code}m{t}\033[0m"
def ok(m):   print(c(92, f"  ✔  {m}"))
def info(m): print(c(96, f"  ●  {m}"))
def err(m):  print(c(91, f"  ✘  {m}"))
def warn(m): print(c(93, f"  ⚠  {m}"))
def head(m): print(c(1,  f"\n{'─'*55}\n  {m}\n{'─'*55}"))


def _urlopen(url: str, headers: dict = None):
    """urlopen با User-Agent و بدون SSL error."""
    req = urllib.request.Request(url, headers={"User-Agent": "HTML2APK-Studio/2.0"})
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    ctx = ssl.create_default_context()
    return urllib.request.urlopen(req, context=ctx, timeout=30)


def download(url: str, dest: Path, label: str) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 100_000:
        ok(f"{label} — قبلاً دانلود شده ({dest.stat().st_size // 1024 // 1024} MB)")
        return True
    info(f"دانلود {label} ...")
    try:
        tmp = dest.with_suffix(".tmp")

        def progress(b, bs, ts):
            if ts > 0:
                pct = min(int(b * bs * 40 / ts), 40)
                done  = b * bs // 1024 // 1024
                total = ts    // 1024 // 1024
                print(f"\r  [{'█'*pct}{'░'*(40-pct)}] {done}/{total} MB", end="", flush=True)

        req = urllib.request.Request(url, headers={"User-Agent": "HTML2APK-Studio/2.0"})
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp, open(tmp, "wb") as f:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            block = 65536
            while True:
                chunk = resp.read(block)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = min(int(downloaded * 40 / total), 40)
                    done = downloaded // 1024 // 1024
                    tot  = total      // 1024 // 1024
                    print(f"\r  [{'█'*pct}{'░'*(40-pct)}] {done}/{tot} MB", end="", flush=True)

        print()
        tmp.rename(dest)
        ok(f"{label} ({dest.stat().st_size // 1024 // 1024} MB)")
        return True
    except Exception as e:
        print()
        err(f"دانلود شکست خورد: {e}")
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        return False


def extract_zip_strip_root(zip_path: Path, dest: Path) -> bool:
    """zip رو extract می‌کنه و root dir داخلش رو strip می‌کنه."""
    dest.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            names = z.namelist()
            # پیدا کردن root dir مشترک
            root = Path(names[0]).parts[0] if names else ""
            for member in z.infolist():
                parts = Path(member.filename).parts
                if len(parts) <= 1:
                    continue
                rel    = Path(*parts[1:])
                target = dest / rel
                if member.filename.endswith("/"):
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(member) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
        return True
    except Exception as e:
        err(f"استخراج شکست: {e}")
        return False


# ══════════════════════════════════════════════════════════
#  ۱. Java 17 JRE portable
# ══════════════════════════════════════════════════════════
def setup_jdk() -> bool:
    head("Java 17 JRE Portable")

    jre_bin = TOOLS / "jre" / "bin" / "java.exe"
    if jre_bin.exists():
        ok(f"JRE قبلاً موجوده: {jre_bin}")
        return True

    zip_path = TOOLS / "_downloads" / "jdk17_jre.zip"

    # از Adoptium API آدرس دقیق رو پیدا می‌کنیم
    api = "https://api.adoptium.net/v3/assets/latest/17/hotspot?architecture=x64&image_type=jre&os=windows&vendor=eclipse"
    download_url = None
    try:
        info("پیدا کردن آدرس JRE از Adoptium API ...")
        with _urlopen(api) as resp:
            data = json.loads(resp.read())
        download_url = data[0]["binary"]["package"]["link"]
        ok(f"آدرس پیدا شد: {Path(download_url).name}")
    except Exception as e:
        warn(f"API شکست خورد ({e})")
        warn("از آدرس مستقیم GitHub استفاده می‌کنم ...")
        # آدرس مستقیم fallback — نسخه پایدار شناخته‌شده
        download_url = (
            "https://github.com/adoptium/temurin17-binaries/releases/download/"
            "jdk-17.0.15%2B6/OpenJDK17U-jre_x64_windows_hotspot_17.0.15_6.zip"
        )

    if not download(download_url, zip_path, "Java 17 JRE"):
        return False

    info("استخراج JRE ...")
    jre_dir = TOOLS / "jre"
    if not extract_zip_strip_root(zip_path, jre_dir):
        return False

    if jre_bin.exists():
        ok("JRE آماده‌ست")
        return True
    else:
        err("استخراج JRE شکست خورد — java.exe پیدا نشد")
        return False


# ══════════════════════════════════════════════════════════
#  ۲. Android SDK (cmdline-tools → sdkmanager → build-tools + platform)
# ══════════════════════════════════════════════════════════
def _run_sdkmanager(sdkmanager: Path, sdk_dir: Path, args: list,
                    java_home: Path, input_text: str = None) -> subprocess.CompletedProcess:
    """
    sdkmanager.bat رو با مدیریت صحیح مسیرهای فضادار اجرا می‌کنه.
    از shell=True + quoting استفاده می‌کنه تا مشکل فضا در مسیر نداشته باشه.
    """
    env = os.environ.copy()
    env["ANDROID_SDK_ROOT"] = str(sdk_dir)
    env["ANDROID_HOME"]     = str(sdk_dir)
    if java_home.exists():
        env["JAVA_HOME"] = str(java_home)

    # ساخت command string با quote صحیح
    parts = [f'"{sdkmanager}"', f'"--sdk_root={sdk_dir}"']
    parts += [f'"{a}"' for a in args]
    cmd_str = " ".join(parts)

    return subprocess.run(
        cmd_str,
        shell=True,
        env=env,
        capture_output=True,
        text=True,
        input=input_text,
        timeout=600,
    )


def setup_android_sdk() -> bool:
    head("Android SDK (minimal)")

    sdk_dir  = TOOLS / "sdk"
    bt_dir   = sdk_dir / "build-tools" / "34.0.0"
    plat_dir = sdk_dir / "platforms"   / "android-34"

    if bt_dir.exists() and plat_dir.exists():
        ok(f"Android SDK قبلاً موجوده")
        return True

    # دانلود cmdline-tools
    cmdtools_zip = TOOLS / "_downloads" / "cmdline-tools.zip"
    url = "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"
    if not download(url, cmdtools_zip, "Android cmdline-tools"):
        return False

    # استخراج
    info("استخراج cmdline-tools ...")
    cmdtools_dir = sdk_dir / "cmdline-tools" / "latest"
    if cmdtools_dir.exists():
        shutil.rmtree(cmdtools_dir)
    if not extract_zip_strip_root(cmdtools_zip, cmdtools_dir):
        return False

    sdkmanager = cmdtools_dir / "bin" / "sdkmanager.bat"
    if not sdkmanager.exists():
        err(f"sdkmanager.bat پیدا نشد: {sdkmanager}")
        return False

    ok("cmdline-tools استخراج شد")

    java_home = TOOLS / "jre"
    packages  = ["build-tools;34.0.0", "platforms;android-34"]

    # تایید لایسنس
    info("تایید لایسنس‌های Android SDK ...")
    _run_sdkmanager(sdkmanager, sdk_dir, ["--licenses"], java_home,
                    input_text="y\n" * 20)

    # نصب پکیج‌ها
    info(f"نصب: {', '.join(packages)}")
    info("(ممکنه ۵-۱۵ دقیقه طول بکشه...)")

    r = _run_sdkmanager(sdkmanager, sdk_dir, packages, java_home)

    if bt_dir.exists() and plat_dir.exists():
        ok(f"Android SDK نصب شد")
        return True
    else:
        out = (r.stdout + r.stderr)[-800:]
        err("نصب SDK شکست خورد. آخرین خروجی:")
        for line in out.splitlines()[-15:]:
            if line.strip():
                print(f"    {line}")
        return False


# ══════════════════════════════════════════════════════════
#  ۳. Gradle zip (آفلاین)
# ══════════════════════════════════════════════════════════
def setup_gradle() -> bool:
    head("Gradle 8.7 (آفلاین)")

    gradle_zip = TOOLS / "gradle-8.7-bin.zip"
    if gradle_zip.exists() and gradle_zip.stat().st_size > 1_000_000:
        ok(f"Gradle zip قبلاً موجوده ({gradle_zip.stat().st_size // 1024 // 1024} MB)")
        return True

    url = "https://services.gradle.org/distributions/gradle-8.7-bin.zip"
    return download(url, gradle_zip, "Gradle 8.7")


# ══════════════════════════════════════════════════════════
#  ۴. ساخت EXE (اختیاری)
# ══════════════════════════════════════════════════════════
def build_exe() -> bool:
    head("ساخت EXE با PyInstaller")

    if not shutil.which("pyinstaller"):
        info("PyInstaller پیدا نشد — نصب می‌کنم ...")
        r = subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            err("نصب PyInstaller شکست: " + r.stderr[-200:])
            return False

    app_py = BASE / "app.py"
    if not app_py.exists():
        err("app.py پیدا نشد!")
        return False

    info("ساخت EXE (onedir mode) ...")
    r = subprocess.run(
        [
            sys.executable, "-m", "PyInstaller",
            "--onedir",
            "--windowed",
            "--name", "HTML2APK_Studio",
            "--add-data", f"{BASE / 'android_template'};android_template",
            "--clean",
            str(app_py),
        ],
        cwd=BASE,
    )
    dist_exe = BASE / "dist" / "HTML2APK_Studio" / "HTML2APK_Studio.exe"
    if dist_exe.exists():
        ok(f"EXE ساخته شد: {dist_exe}")
        return True
    else:
        err("ساخت EXE شکست خورد")
        return False


# ══════════════════════════════════════════════════════════
#  ۵. کپی tools/ کنار EXE
# ══════════════════════════════════════════════════════════
def copy_tools_to_dist() -> bool:
    head("کپی tools/ کنار EXE")

    dist_dir  = BASE / "dist" / "HTML2APK_Studio"
    tools_dst = dist_dir / "tools"

    if not dist_dir.exists():
        warn("پوشه dist/ پیدا نشد — شاید EXE ساخته نشده")
        return False

    if tools_dst.exists():
        shutil.rmtree(tools_dst)

    shutil.copytree(TOOLS, tools_dst,
                    ignore=shutil.ignore_patterns("_downloads"))
    size_mb = sum(
        f.stat().st_size for f in tools_dst.rglob("*") if f.is_file()
    ) // 1024 // 1024
    ok(f"tools/ کپی شد ({size_mb} MB)")
    return True


# ══════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════
def main():
    print(c(1, c(96, """
  ╔═══════════════════════════════════════════════╗
  ║   HTML2APK Studio — Portable Setup           ║
  ║   یه‌بار اجرا کن، برای همیشه آفلاین باش     ║
  ╚═══════════════════════════════════════════════╝
""")))

    jdk_ok    = setup_jdk()
    sdk_ok    = setup_android_sdk()
    gradle_ok = setup_gradle()

    print(f"\n{c(1, '  ── نتیجه ──')}\n")
    for label, status in [
        ("Java 17 JRE portable",     jdk_ok),
        ("Android SDK (build+plat)",  sdk_ok),
        ("Gradle 8.7 zip",            gradle_ok),
    ]:
        icon = c(92, "✔") if status else c(91, "✘")
        print(f"  {icon}  {label}")

    if not (jdk_ok and sdk_ok and gradle_ok):
        print(c(91, "\n  ⚠ بعضی مراحل شکست خوردن. لاگ بالا رو بررسی کن."))
        print()
        input("  Enter بزن...")
        return

    print()
    ans = input(c(96, "  الان EXE بسازم؟ (y/n): ")).strip().lower()
    if ans == "y":
        exe_ok = build_exe()
        if exe_ok:
            copy_tools_to_dist()
            dist = BASE / "dist" / "HTML2APK_Studio"
            print(c(92, c(1, f"""
  ✅ آماده‌ست!

  این پوشه رو zip کن و به دوستات بده:
  {dist}

  دوستات فقط HTML2APK_Studio.exe رو اجرا می‌کنن.
  هیچ‌چیزی نصب نمی‌کنن.
""")))
    else:
        print(c(92, c(1, """
  ✅ tools/ آماده‌ست!

  برای ساخت EXE بعداً:
    build_exe.bat  رو اجرا کن
""")))

    print()
    input("  Enter بزن...")


if __name__ == "__main__":
    main()
