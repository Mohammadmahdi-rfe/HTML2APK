#!/usr/bin/env python3
"""
HTML2APK Studio v2 — Gradle-based Build
معماری درست: Android source template + Gradle → APK واقعی
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk
from PIL import Image
import os, sys, shutil, subprocess, threading, re, tempfile, json
from pathlib import Path
import io

# ── Theme ──────────────────────────────────────────────────
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

BG       = "#F5F6FA"
CARD     = "#FFFFFF"
PRIMARY  = "#2563EB"
PRIMARY_H= "#1D4ED8"
SUCCESS  = "#16A34A"
DANGER   = "#DC2626"
TEXT     = "#1E293B"
TEXT_M   = "#64748B"
BORDER   = "#E2E8F0"
ACCENT   = "#EFF6FF"

# ── Paths ──────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    BASE      = Path(sys._MEIPASS)
    # tools/ کنار EXE هست، نه داخل _internal
    TOOLS_DIR = Path(sys.executable).parent / "tools"
else:
    BASE      = Path(__file__).parent
    TOOLS_DIR = BASE / "tools"

TEMPLATE_DIR = BASE / "android_template"   # پوشه Android project


# ══════════════════════════════════════════════════════════
#  HELPER WIDGETS
# ══════════════════════════════════════════════════════════

class Card(ctk.CTkFrame):
    def __init__(self, parent, title="", **kw):
        super().__init__(parent, fg_color=CARD, corner_radius=12,
                         border_width=1, border_color=BORDER, **kw)
        if title:
            ctk.CTkLabel(self, text=title, font=("Segoe UI Semibold", 12),
                         text_color=TEXT).pack(anchor="w", padx=16, pady=(13,3))


class DropZone(ctk.CTkFrame):
    def __init__(self, parent, label, sub, filetypes, on_select, preview=False, **kw):
        super().__init__(parent, fg_color=ACCENT, corner_radius=10,
                         border_width=2, border_color="#BFDBFE", **kw)
        self._on_select = on_select
        self._filetypes = filetypes
        self._preview   = preview
        self.filepath   = None

        self._icon  = ctk.CTkLabel(self, text="📂", font=("Segoe UI", 26))
        self._icon.pack(pady=(16,2))
        self._lbl   = ctk.CTkLabel(self, text=label, font=("Segoe UI Semibold", 12),
                                    text_color=PRIMARY)
        self._lbl.pack()
        self._sub   = ctk.CTkLabel(self, text=sub, font=("Segoe UI", 10),
                                    text_color=TEXT_M)
        self._sub.pack(pady=(1,12))
        if preview:
            self._img_lbl = ctk.CTkLabel(self, text="")
            self._img_lbl.pack(pady=(0,8))

        for w in [self] + list(self.winfo_children()):
            w.bind("<Button-1>", lambda e: self._pick())

    def _pick(self):
        p = filedialog.askopenfilename(filetypes=self._filetypes)
        if p: self.set_file(p)

    def set_file(self, path):
        self.filepath = path
        name = Path(path).name
        self._lbl.configure(text=name, text_color=SUCCESS)
        self._sub.configure(text="✔ انتخاب شد")
        self._icon.configure(text="✅")
        self.configure(fg_color="#F0FDF4", border_color="#86EFAC")
        if self._preview:
            try:
                img = Image.open(path).resize((60,60))
                ci  = ctk.CTkImage(img, size=(60,60))
                self._img_lbl.configure(image=ci, text="")
                self._img_lbl.image = ci
            except: pass
        if self._on_select: self._on_select(path)


class Field(ctk.CTkFrame):
    def __init__(self, parent, label, placeholder="", **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        ctk.CTkLabel(self, text=label, font=("Segoe UI", 11),
                     text_color=TEXT_M, anchor="w").pack(anchor="w", pady=(0,3))
        self.entry = ctk.CTkEntry(self, placeholder_text=placeholder,
                                   font=("Segoe UI", 12), height=36,
                                   fg_color=CARD, border_color=BORDER, text_color=TEXT)
        self.entry.pack(fill="x")

    def get(self): return self.entry.get().strip()
    def set(self, v):
        self.entry.delete(0,"end")
        self.entry.insert(0, v)


class BuildLog(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color=CARD, corner_radius=10,
                         border_width=1, border_color=BORDER, **kw)
        ctk.CTkLabel(self, text="Build Log", font=("Segoe UI Semibold", 12),
                     text_color=TEXT).pack(anchor="w", padx=14, pady=(10,4))
        self.bar = ctk.CTkProgressBar(self, height=6, fg_color=BORDER,
                                       progress_color=PRIMARY)
        self.bar.pack(fill="x", padx=14, pady=(0,6))
        self.bar.set(0)
        self.box = ctk.CTkTextbox(self, font=("Consolas", 11), height=180,
                                   fg_color="#F8FAFC", text_color=TEXT)
        self.box.pack(fill="both", expand=True, padx=14, pady=(0,12))
        self.box.configure(state="disabled")

    def write(self, msg):
        self.box.configure(state="normal")
        self.box.insert("end", msg+"\n")
        self.box.see("end")
        self.box.configure(state="disabled")

    def progress(self, v): self.bar.set(v)
    def clear(self):
        self.box.configure(state="normal")
        self.box.delete("1.0","end")
        self.box.configure(state="disabled")
        self.bar.set(0)


# ══════════════════════════════════════════════════════════
#  BUILDER — منطق اصلی ساخت APK
# ══════════════════════════════════════════════════════════

class APKBuilder:
    """
    معماری:
      1. پیدا کردن Android SDK و Gradle
      2. کپی android_template به یه پوشه موقت
      3. جایگزینی placeholders (package, name, version, ...)
      4. کپی HTML و آیکون کاربر
      5. اجرای gradlew assembleDebug
      6. کپی APK خروجی
    """

    def __init__(self, config: dict, log_fn, prog_fn):
        self.cfg    = config
        self.log    = log_fn
        self.prog   = prog_fn

    # ── ۱. پیدا کردن SDK ────────────────────────────────

    def find_sdk(self) -> Path | None:
        candidates = []
        # اول: tools/ بسته‌شده با پروژه
        candidates.append(TOOLS_DIR / "sdk")
        # بعد: مسیرهای سیستمی
        home = Path.home()
        env = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
        if env: candidates.append(Path(env))
        candidates += [
            home / "AppData" / "Local" / "Android" / "Sdk",
            Path("C:/Android/Sdk"),
            Path("C:/Users/Public/Android/Sdk"),
        ]
        for p in candidates:
            if p.exists() and (p / "platforms").exists():
                return p
        # اگه platforms نداشت ولی وجود داشت، همون رو برگردون
        for p in candidates:
            if p.exists():
                return p
        return None

    def find_java(self) -> str:
        """java.exe رو پیدا می‌کنه — اول tools/ بسته‌شده، بعد سیستم."""
        # tools/ بسته‌شده با پروژه
        local = TOOLS_DIR / "jre" / "bin" / "java.exe"
        if local.exists(): return str(local)
        # JAVA_HOME
        java_home = os.environ.get("JAVA_HOME")
        if java_home:
            j = Path(java_home) / "bin" / "java.exe"
            if j.exists(): return str(j)
        # از PATH
        result = shutil.which("java")
        if result: return result
        return None

    def _patch_gradle_local(self, proj: Path):
        """اگه gradle zip محلی داشتیم، wrapper رو به اون هدایت می‌کنه (آفلاین)."""
        local_zip = TOOLS_DIR / "gradle-8.7-bin.zip"
        if not local_zip.exists():
            return
        wrapper_props = proj / "gradle" / "wrapper" / "gradle-wrapper.properties"
        if not wrapper_props.exists():
            return
        zip_url = "file:///" + str(local_zip).replace("\\", "/")
        content = wrapper_props.read_text(encoding="utf-8")
        content = re.sub(r"distributionUrl=.*", f"distributionUrl={zip_url}", content)
        wrapper_props.write_text(content, encoding="utf-8")
        self.log(f"  ✔ Gradle آفلاین: {local_zip.name}")

    # ── ۲. چک prerequisites ─────────────────────────────

    def check(self) -> bool:
        self.log("  [1/5] بررسی محیط...")

        self.sdk = self.find_sdk()
        if not self.sdk:
            self.log("  ✘ Android SDK پیدا نشد!")
            self.log("    → Android Studio رو نصب کن")
            self.log("    → یا ANDROID_HOME رو set کن")
            return False
        self.log(f"  ✔ SDK: {self.sdk}")

        self.java = self.find_java()
        if not self.java:
            self.log("  ✘ Java پیدا نشد!")
            self.log("    → JDK 17 رو از adoptium.net نصب کن")
            return False
        self.log(f"  ✔ Java: {self.java}")

        if not TEMPLATE_DIR.exists():
            self.log(f"  ✘ android_template پیدا نشد: {TEMPLATE_DIR}")
            return False
        self.log(f"  ✔ Android template: OK")

        return True

    # ── ۳. آماده‌سازی project ────────────────────────────

    def prepare_project(self, work: Path) -> Path:
        self.log("\n  [2/5] آماده‌سازی Android project...")

        proj = work / "app_project"

        # کپی کامل template
        shutil.copytree(TEMPLATE_DIR, proj)
        self.log("  ✔ Template کپی شد")

        cfg = self.cfg
        pkg         = cfg["package"]
        app_name    = cfg["app_name"]
        version     = cfg["version"]
        version_code= cfg.get("version_code", "1")
        orientation = cfg.get("orientation", "portrait")
        js_enabled  = "true" if cfg.get("js_enabled", True) else "false"
        zoom_enabled= "true" if cfg.get("zoom_enabled", False) else "false"
        fullscreen  = cfg.get("fullscreen", False)

        fullscreen_code = ""
        if fullscreen:
            fullscreen_code = (
                "requestWindowFeature(Window.FEATURE_NO_TITLE);\n"
                "        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN,\n"
                "            WindowManager.LayoutParams.FLAG_FULLSCREEN);"
            )

        # orientation map
        orient_map = {
            "portrait":  "portrait",
            "landscape": "landscape",
            "sensor (auto)": "sensor",
        }
        orientation = orient_map.get(orientation, "portrait")

        replacements = {
            "{{PACKAGE_NAME}}":   pkg,
            "{{APP_NAME}}":       app_name,
            "{{VERSION_NAME}}":   version,
            "{{VERSION_CODE}}":   version_code,
            "{{ORIENTATION}}":    orientation,
            "{{JS_ENABLED}}":     js_enabled,
            "{{ZOOM_ENABLED}}":   zoom_enabled,
            "{{FULLSCREEN_CODE}}": fullscreen_code,
        }

        # فایل‌هایی که باید جایگزینی بشن
        files_to_patch = [
            proj / "app" / "src" / "main" / "AndroidManifest.xml",
            proj / "app" / "src" / "main" / "res" / "values" / "strings.xml",
            proj / "app" / "build.gradle",
        ]

        for f in files_to_patch:
            if f.exists():
                txt = f.read_text(encoding="utf-8")
                for k, v in replacements.items():
                    txt = txt.replace(k, v)
                f.write_text(txt, encoding="utf-8")

        # همه Java files — باید توی پوشه‌ای با package name باشن
        pkg_path = proj / "app" / "src" / "main" / "java" / Path(*pkg.split("."))
        pkg_path.mkdir(parents=True, exist_ok=True)

        java_template_dir = proj / "app" / "src" / "main" / "java" / "com" / "html2apk" / "template"
        if java_template_dir.exists():
            for java_file in java_template_dir.rglob("*.java"):
                rel = java_file.relative_to(java_template_dir)
                txt = java_file.read_text(encoding="utf-8")
                for k, v in replacements.items():
                    txt = txt.replace(k, v)
                dst = pkg_path / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(txt, encoding="utf-8")
            # حذف پوشه template قدیمی — همیشه باید حذف بشه
            # اگه حذف نشه، Gradle فایل‌هایی با package {{PACKAGE_NAME}} پیدا می‌کنه و کامپایل شکست می‌خوره
            old_tmpl = proj / "app" / "src" / "main" / "java" / "com" / "html2apk" / "template"
            if old_tmpl.exists() and old_tmpl.resolve() != pkg_path.resolve():
                shutil.rmtree(old_tmpl, ignore_errors=True)
            # حذف پوشه‌های خالی والد از مسیر قدیمی
            for cleanup in [
                proj / "app" / "src" / "main" / "java" / "com" / "html2apk",
                proj / "app" / "src" / "main" / "java" / "com",
            ]:
                if not str(pkg_path).startswith(str(cleanup)):
                    try:
                        if cleanup.exists() and not any(cleanup.iterdir()):
                            cleanup.rmdir()
                    except Exception:
                        pass

        self.log(f"  ✔ Package: {pkg}")
        self.log(f"  ✔ App Name: {app_name}")
        self.log(f"  ✔ Version: {version}")
        self.log(f"  ✔ Orientation: {orientation}")

        return proj

    # ── ۴. کپی assets کاربر ─────────────────────────────

    def inject_assets(self, proj: Path):
        self.log("\n  [3/5] اضافه کردن فایل‌های کاربر...")

        cfg = self.cfg
        www = proj / "app" / "src" / "main" / "assets" / "www"
        www.mkdir(parents=True, exist_ok=True)

        # HTML
        html_src = Path(cfg["html_path"])
        shutil.copy(html_src, www / "index.html")
        size = html_src.stat().st_size
        self.log(f"  ✔ HTML کپی شد ({size:,} bytes)")

        # آیکون — اگه کاربر نداد، پیش‌فرض می‌سازیم
        res_dir = proj / "app" / "src" / "main" / "res"
        icon_sizes = {
            "mipmap-mdpi":    48,
            "mipmap-hdpi":    72,
            "mipmap-xhdpi":   96,
            "mipmap-xxhdpi":  144,
            "mipmap-xxxhdpi": 192,
        }
        icon_src = Path(cfg["icon_path"]) if cfg.get("icon_path") else None
        try:
            from PIL import Image, ImageDraw
            for folder, sz in icon_sizes.items():
                d = res_dir / folder
                d.mkdir(parents=True, exist_ok=True)
                dest = d / "ic_launcher.png"
                if icon_src and icon_src.exists():
                    Image.open(icon_src).resize((sz, sz), Image.LANCZOS).save(dest)
                else:
                    img = Image.new("RGBA", (sz, sz), (37, 99, 235, 255))
                    draw = ImageDraw.Draw(img)
                    m = sz // 6
                    draw.ellipse([m, m, sz-m, sz-m], fill=(255, 255, 255, 220))
                    img.save(dest)
            if icon_src:
                self.log("  ✔ آیکون کاربر در همه سایزها ذخیره شد")
            else:
                self.log("  ✔ آیکون پیش‌فرض ساخته شد")
        except Exception as e:
            self.log(f"  ⚠ آیکون: {e}")

    # ── ۵. نوشتن local.properties ────────────────────────

    def write_local_properties(self, proj: Path):
        sdk_path = str(self.sdk).replace("\\", "/")
        (proj / "local.properties").write_text(
            f"sdk.dir={sdk_path}\n"
            f"java.home={Path(self.java).parent.parent}\n",
            encoding="utf-8"
        )
        self.log(f"  ✔ local.properties نوشته شد")

    # ── ۶. اجرای Gradle ──────────────────────────────────

    def run_gradle(self, proj: Path) -> Path | None:
        self.log("\n  [4/5] ساخت APK با Gradle...")
        self.log("  (این ممکنه ۳-۵ دقیقه طول بکشه اول بار)")
        self._patch_gradle_local(proj)

        gradlew = proj / "gradlew.bat"
        if not gradlew.exists():
            # کپی gradlew از template اگه وجود نداره
            src_gw = TEMPLATE_DIR / "gradlew.bat"
            if src_gw.exists():
                shutil.copy(src_gw, gradlew)

        if not gradlew.exists():
            self.log("  ✘ gradlew.bat پیدا نشد!")
            self.log("  → run setup_sdk.py رو اجرا کن")
            return None

        env = os.environ.copy()
        env["ANDROID_HOME"]     = str(self.sdk)
        env["ANDROID_SDK_ROOT"] = str(self.sdk)
        env["JAVA_HOME"]        = str(Path(self.java).parent.parent)

        # اجرای Gradle با capture کامل خروجی
        import sys as _sys
        cmd = [str(gradlew), "assembleDebug"]
        if _sys.platform == "win32":
            cmd = ["cmd", "/c"] + cmd   # اطمینان از اجرای .bat روی Windows

        try:
            proc = subprocess.Popen(
                cmd, cwd=proj, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
            )
        except Exception as e:
            self.log(f"  ✘ خطا در اجرای Gradle: {e}")
            return None

        all_lines = []
        for raw in proc.stdout:
            line = raw.rstrip()
            all_lines.append(line)
            low = line.lower()
            # نمایش task names، خطاها، هشدارها، و وضعیت build
            if (line.startswith((">", "*", "e:")) or
                    any(k in low for k in ["error", "failed", "exception", "warning:", "build "])):
                self.log("  " + line[:200])

        proc.wait()

        if proc.returncode != 0:
            self.log("\n  ✘ Gradle build شکست خورد")
            # نمایش آخرین ۳۰ خط برای context کامل
            relevant = [l for l in all_lines if l.strip() and
                        any(k in l.lower() for k in
                            ["error", "failed", "exception", "could not", "unresolved",
                             "what went wrong", "try:", "task :", "compilation"])]
            if relevant:
                self.log("  ── جزئیات خطا ──")
                for line in relevant[-25:]:
                    self.log("  " + line[:200])
            else:
                # اگه هیچ خطای مرتبطی پیدا نشد، آخرین ۱۵ خط رو نشون بده
                self.log("  ── آخرین خروجی ──")
                for line in all_lines[-15:]:
                    if line.strip():
                        self.log("  " + line[:200])
            return None

        # پیدا کردن APK
        apk_files = list(proj.glob("**/outputs/apk/debug/*.apk"))
        if not apk_files:
            self.log("  ✘ APK پیدا نشد بعد از build")
            return None

        self.log(f"  ✔ APK ساخته شد: {apk_files[0].name}")
        return apk_files[0]

    # ── ۷. تحویل APK ─────────────────────────────────────

    def deliver(self, apk_src: Path) -> Path:
        self.log("\n  [5/5] ذخیره APK نهایی...")

        app_name = self.cfg["app_name"]
        out_name = re.sub(r"\s+", "_", app_name) + ".apk"
        html_dir = Path(self.cfg["html_path"]).parent
        out_path = html_dir / out_name
        shutil.copy(apk_src, out_path)

        size_mb = out_path.stat().st_size / 1024 / 1024
        self.log(f"  ✔ APK ذخیره شد: {out_path}")
        self.log(f"  ✔ حجم: {size_mb:.1f} MB")
        return out_path

    # ── main build ───────────────────────────────────────

    def build(self) -> Path | None:
        try:
            if not self.check():
                return None
            self.prog(0.1)

            with tempfile.TemporaryDirectory(prefix="html2apk_") as tmp:
                work = Path(tmp)

                proj = self.prepare_project(work)
                self.prog(0.25)

                self.inject_assets(proj)
                self.prog(0.35)

                self.write_local_properties(proj)

                apk = self.run_gradle(proj)
                self.prog(0.9)

                if not apk:
                    return None

                out = self.deliver(apk)
                self.prog(1.0)
                return out

        except Exception as e:
            self.log(f"  ✘ خطا: {e}")
            import traceback
            self.log(traceback.format_exc())
            return None


# ══════════════════════════════════════════════════════════
#  MAIN GUI
# ══════════════════════════════════════════════════════════

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("HTML2APK Studio")
        self.geometry("780x860")
        self.minsize(700, 720)
        self.configure(fg_color=BG)
        self._center()
        self.building = False
        self._build_ui()

    def _center(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - 780) // 2
        y = (self.winfo_screenheight() - 860) // 2
        self.geometry(f"780x860+{x}+{y}")

    def _build_ui(self):
        # Header
        hdr = ctk.CTkFrame(self, fg_color=PRIMARY, corner_radius=0, height=60)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="⚡ HTML2APK Studio",
                     font=("Segoe UI Bold", 18), text_color="white").pack(side="left", padx=22)
        ctk.CTkLabel(hdr, text="v2 — Gradle Build",
                     font=("Segoe UI", 11), text_color="#BFDBFE").pack(side="left")

        scroll = ctk.CTkScrollableFrame(self, fg_color=BG)
        scroll.pack(fill="both", expand=True)
        b = scroll

        # ── HTML File ──────────────────────────────────
        s1 = Card(b, "① فایل HTML"); s1.pack(fill="x", padx=18, pady=6)
        self.html_drop = DropZone(s1, "فایل HTML خود را انتخاب کنید",
                                   "کلیک کنید",
                                   [("HTML","*.html *.htm"),("All","*.*")],
                                   self._on_html, False)
        self.html_drop.pack(fill="x", padx=14, pady=(4,14))
        self.html_info = ctk.CTkLabel(s1, text="", font=("Segoe UI",10),
                                       text_color=TEXT_M, anchor="w", wraplength=620)
        self.html_info.pack(anchor="w", padx=14, pady=(0,8))

        # ── App Info ───────────────────────────────────
        s2 = Card(b, "② اطلاعات اپ"); s2.pack(fill="x", padx=18, pady=6)
        g = ctk.CTkFrame(s2, fg_color="transparent")
        g.pack(fill="x", padx=14, pady=(4,14))
        g.columnconfigure((0,1), weight=1)

        self.f_name = Field(g, "نام اپ",        "مثلاً: ماشین‌حساب من")
        self.f_pkg  = Field(g, "Package Name",  "مثلاً: com.myname.calc")
        self.f_ver  = Field(g, "نسخه",          "1.0")
        self.f_desc = Field(g, "توضیحات",       "توضیح کوتاه...")

        self.f_name.grid(row=0, column=0, padx=(0,6), pady=4, sticky="ew")
        self.f_pkg.grid (row=0, column=1, padx=(6,0), pady=4, sticky="ew")
        self.f_ver.grid (row=1, column=0, padx=(0,6), pady=4, sticky="ew")
        self.f_desc.grid(row=1, column=1, padx=(6,0), pady=4, sticky="ew")
        self.f_ver.set("1.0")

        row2 = ctk.CTkFrame(g, fg_color="transparent")
        row2.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6,0))

        ctk.CTkLabel(row2, text="جهت صفحه", font=("Segoe UI",11),
                     text_color=TEXT_M).pack(side="left", padx=(0,6))
        self.orient = ctk.CTkOptionMenu(row2,
            values=["portrait","landscape","sensor (auto)"],
            font=("Segoe UI",11), width=160,
            fg_color=CARD, text_color=TEXT,
            button_color=BORDER, button_hover_color=PRIMARY,
            dropdown_fg_color=CARD, dropdown_text_color=TEXT)
        self.orient.pack(side="left")

        # ── Assets ─────────────────────────────────────
        s3 = Card(b, "③ آیکون (اختیاری)"); s3.pack(fill="x", padx=18, pady=6)
        ar = ctk.CTkFrame(s3, fg_color="transparent")
        ar.pack(fill="x", padx=14, pady=(4,14))
        ar.columnconfigure((0,1), weight=1)
        self.icon_drop = DropZone(ar, "آیکون اپ", "PNG 512×512",
                                   [("Image","*.png *.jpg *.jpeg")],
                                   lambda p: None, preview=True)
        self.icon_drop.grid(row=0, column=0, padx=(0,6), sticky="ew")

        # ── Native Bridge ──────────────────────────────────
        s_bridge = Card(b, "④ Native Bridge  (Cordova-like)"); s_bridge.pack(fill="x", padx=18, pady=6)
        bridge_info = ctk.CTkFrame(s_bridge, fg_color="transparent")
        bridge_info.pack(fill="x", padx=14, pady=(4,10))

        bridge_desc = (
            "html2apk.js به‌طور خودکار به هر صفحه inject می‌شه.\n"
            "در HTML خود از این APIها استفاده کن:\n"
            "  • html2apk.device.getInfo(cb)       — اطلاعات دستگاه\n"
            "  • html2apk.vibrate(500)              — لرزش ۵۰۰ms\n"
            "  • html2apk.toast.show('پیام')       — Toast پیام\n"
            "  • html2apk.network.isOnline(cb)      — وضعیت اینترنت\n"
            "  • html2apk.clipboard.copy('متن')    — کپی در کلیپ‌بورد\n"
            "  • document.addEventListener('html2apkready', fn)  — مثل deviceready"
        )
        ctk.CTkLabel(bridge_info, text=bridge_desc,
                     font=("Consolas", 10), text_color=TEXT,
                     justify="left", anchor="w").pack(anchor="w")

        # SDK info
        s4 = Card(b, "⑤ تنظیمات Gradle"); s4.pack(fill="x", padx=18, pady=6)
        adv = ctk.CTkFrame(s4, fg_color="transparent")
        adv.pack(fill="x", padx=14, pady=(4,14))

        self.js_on   = self._cb(adv, "JavaScript فعال", True)
        self.zoom_on = self._cb(adv, "Zoom فعال", False)
        self.fs_on   = self._cb(adv, "Fullscreen", False)

        # SDK path
        sdk_row = ctk.CTkFrame(s4, fg_color="transparent")
        sdk_row.pack(fill="x", padx=14, pady=(0,14))
        ctk.CTkLabel(sdk_row, text="ANDROID_HOME (اختیاری):",
                     font=("Segoe UI",11), text_color=TEXT_M).pack(side="left", padx=(0,8))
        self.sdk_entry = ctk.CTkEntry(sdk_row, placeholder_text="خودکار پیدا می‌شه",
                                       font=("Segoe UI",11), height=32,
                                       fg_color=CARD, border_color=BORDER, text_color=TEXT)
        self.sdk_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(sdk_row, text="Browse", width=70, height=32,
                      font=("Segoe UI",11), fg_color=BORDER, text_color=TEXT,
                      hover_color="#CBD5E1",
                      command=self._pick_sdk).pack(side="left", padx=(6,0))

        # ── Build button ───────────────────────────────────
        self.btn = ctk.CTkButton(b, text="⚡  Build APK",
                                  height=50, font=("Segoe UI Bold",16),
                                  fg_color=PRIMARY, hover_color=PRIMARY_H,
                                  corner_radius=12, command=self._start)
        self.btn.pack(fill="x", padx=18, pady=(8,6))

        # Log
        self.log_widget = BuildLog(b)
        self.log_widget.pack(fill="x", padx=18, pady=(0,16))

        ctk.CTkLabel(b, text="HTML2APK Studio v2  •  Gradle + Native Bridge  •  APK واقعی",
                     font=("Segoe UI",10), text_color=TEXT_M).pack(pady=(0,14))

    def _cb(self, parent, text, default):
        var = tk.BooleanVar(value=default)
        ctk.CTkCheckBox(parent, text=text, variable=var,
                        font=("Segoe UI",11), text_color=TEXT,
                        fg_color=PRIMARY, hover_color=PRIMARY_H
                        ).pack(side="left", padx=(0,20), pady=4)
        return var

    def _pick_sdk(self):
        p = filedialog.askdirectory(title="پوشه Android SDK")
        if p:
            self.sdk_entry.delete(0,"end")
            self.sdk_entry.insert(0, p)
            os.environ["ANDROID_HOME"] = p

    def _on_html(self, path):
        stem = Path(path).stem.replace("_"," ").replace("-"," ").title()
        if not self.f_name.get(): self.f_name.set(stem)
        if not self.f_pkg.get():
            slug = re.sub(r"[^a-z0-9]","", stem.lower())
            self.f_pkg.set(f"com.myapp.{slug or 'app'}")
        try:
            txt = Path(path).read_text(encoding="utf-8",errors="replace")
            self.html_info.configure(text=f"پیش‌نمایش: {txt[:180].strip()}...")
        except: pass

    def _start(self):
        if self.building: return

        # Validate
        if not self.html_drop.filepath:
            messagebox.showerror("خطا", "لطفاً فایل HTML انتخاب کن")
            return
        if not self.f_name.get():
            messagebox.showerror("خطا", "نام اپ رو وارد کن")
            return
        if not self.f_pkg.get():
            messagebox.showerror("خطا", "Package name رو وارد کن")
            return

        sdk_manual = self.sdk_entry.get()
        if sdk_manual: os.environ["ANDROID_HOME"] = sdk_manual

        self.building = True
        self.btn.configure(text="⏳  در حال ساخت...", state="disabled", fg_color=TEXT_M)
        self.log_widget.clear()
        self.log_widget.write("═"*46)
        self.log_widget.write("  شروع ساخت APK...")

        cfg = {
            "html_path":    self.html_drop.filepath,
            "icon_path":    self.icon_drop.filepath,
            "app_name":     self.f_name.get(),
            "package":      self.f_pkg.get(),
            "version":      self.f_ver.get() or "1.0",
            "version_code": "1",
            "orientation":  self.orient.get(),
            "js_enabled":   self.js_on.get(),
            "zoom_enabled": self.zoom_on.get(),
            "fullscreen":   self.fs_on.get(),
        }

        builder = APKBuilder(
            cfg,
            log_fn  = lambda m: self.after(0, lambda msg=m: self.log_widget.write(msg)),
            prog_fn = lambda v: self.after(0, lambda val=v: self.log_widget.progress(val)),
        )

        def run():
            out = builder.build()
            self.after(0, lambda: self._finish(out))

        threading.Thread(target=run, daemon=True).start()

    def _finish(self, out_path):
        self.building = False
        if out_path:
            self.btn.configure(text="✅  ساخت موفق!", fg_color=SUCCESS, state="normal")
            self.log_widget.write("═"*46)
            if messagebox.askyesno("موفق!", f"APK ساخته شد!\n\n{out_path}\n\nپوشه رو باز کنی؟"):
                os.startfile(out_path.parent)
        else:
            self.btn.configure(text="⚡  Build APK", fg_color=PRIMARY, state="normal")
            self.log_widget.write("═"*46)
            self.log_widget.write("  ✘ ساخت ناموفق. لاگ بالا رو بررسی کن.")


if __name__ == "__main__":
    App().mainloop()
