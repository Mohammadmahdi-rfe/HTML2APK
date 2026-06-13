#!/usr/bin/env python3
"""HTML2APK Studio v2 — Gradle-based Android APK builder"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk
from PIL import Image
import os, sys, shutil, subprocess, threading, re, tempfile
from pathlib import Path

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

BG       = "#F5F6FA"
CARD     = "#FFFFFF"
PRIMARY  = "#2563EB"
PRIMARY_H= "#1D4ED8"
SUCCESS  = "#16A34A"
TEXT     = "#1E293B"
TEXT_M   = "#64748B"
BORDER   = "#E2E8F0"
ACCENT   = "#EFF6FF"

# ── Paths ───────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    BASE      = Path(sys._MEIPASS)
    TOOLS_DIR = Path(sys.executable).parent / "tools"  # next to EXE, not inside _internal
else:
    BASE      = Path(__file__).parent
    TOOLS_DIR = BASE / "tools"

TEMPLATE_DIR = BASE / "android_template"


# ══════════════════════════════════════════════════════════
#  WIDGETS
# ══════════════════════════════════════════════════════════

class Card(ctk.CTkFrame):
    def __init__(self, parent, title="", **kw):
        super().__init__(parent, fg_color=CARD, corner_radius=12,
                         border_width=1, border_color=BORDER, **kw)
        if title:
            ctk.CTkLabel(self, text=title, font=("Segoe UI Semibold", 12),
                         text_color=TEXT).pack(anchor="w", padx=16, pady=(13, 3))


class DropZone(ctk.CTkFrame):
    def __init__(self, parent, label, sub, filetypes, on_select, preview=False, **kw):
        super().__init__(parent, fg_color=ACCENT, corner_radius=10,
                         border_width=2, border_color="#BFDBFE", **kw)
        self._on_select = on_select
        self._filetypes = filetypes
        self._preview   = preview
        self.filepath   = None

        self._icon = ctk.CTkLabel(self, text="📂", font=("Segoe UI", 26))
        self._icon.pack(pady=(16, 2))
        self._lbl = ctk.CTkLabel(self, text=label, font=("Segoe UI Semibold", 12),
                                  text_color=PRIMARY)
        self._lbl.pack()
        self._sub = ctk.CTkLabel(self, text=sub, font=("Segoe UI", 10),
                                  text_color=TEXT_M)
        self._sub.pack(pady=(1, 12))
        if preview:
            self._img_lbl = ctk.CTkLabel(self, text="")
            self._img_lbl.pack(pady=(0, 8))

        for w in [self] + list(self.winfo_children()):
            w.bind("<Button-1>", lambda e: self._pick())

    def _pick(self):
        p = filedialog.askopenfilename(filetypes=self._filetypes)
        if p:
            self.set_file(p)

    def set_file(self, path):
        self.filepath = path
        self._lbl.configure(text=Path(path).name, text_color=SUCCESS)
        self._sub.configure(text="✔ Selected")
        self._icon.configure(text="✅")
        self.configure(fg_color="#F0FDF4", border_color="#86EFAC")
        if self._preview:
            try:
                img = Image.open(path).resize((60, 60))
                ci  = ctk.CTkImage(img, size=(60, 60))
                self._img_lbl.configure(image=ci, text="")
                self._img_lbl.image = ci
            except Exception:
                pass
        if self._on_select:
            self._on_select(path)


class Field(ctk.CTkFrame):
    def __init__(self, parent, label, placeholder="", **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        ctk.CTkLabel(self, text=label, font=("Segoe UI", 11),
                     text_color=TEXT_M, anchor="w").pack(anchor="w", pady=(0, 3))
        self.entry = ctk.CTkEntry(self, placeholder_text=placeholder,
                                   font=("Segoe UI", 12), height=36,
                                   fg_color=CARD, border_color=BORDER, text_color=TEXT)
        self.entry.pack(fill="x")

    def get(self): return self.entry.get().strip()
    def set(self, v):
        self.entry.delete(0, "end")
        self.entry.insert(0, v)


class BuildLog(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color=CARD, corner_radius=10,
                         border_width=1, border_color=BORDER, **kw)
        ctk.CTkLabel(self, text="Build Log", font=("Segoe UI Semibold", 12),
                     text_color=TEXT).pack(anchor="w", padx=14, pady=(10, 4))
        self.bar = ctk.CTkProgressBar(self, height=6, fg_color=BORDER,
                                       progress_color=PRIMARY)
        self.bar.pack(fill="x", padx=14, pady=(0, 6))
        self.bar.set(0)
        self.box = ctk.CTkTextbox(self, font=("Consolas", 11), height=180,
                                   fg_color="#F8FAFC", text_color=TEXT)
        self.box.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self.box.configure(state="disabled")

    def write(self, msg):
        self.box.configure(state="normal")
        self.box.insert("end", msg + "\n")
        self.box.see("end")
        self.box.configure(state="disabled")

    def progress(self, v): self.bar.set(v)

    def clear(self):
        self.box.configure(state="normal")
        self.box.delete("1.0", "end")
        self.box.configure(state="disabled")
        self.bar.set(0)


# ══════════════════════════════════════════════════════════
#  APK BUILDER
# ══════════════════════════════════════════════════════════

class APKBuilder:
    """
    Build flow:
      1. Locate Android SDK + Java
      2. Copy android_template to a temp dir
      3. Replace placeholders (package, name, version, ...)
      4. Copy user HTML + icon
      5. Run gradlew assembleDebug
      6. Copy output APK
    """

    def __init__(self, config: dict, log_fn, prog_fn):
        self.cfg  = config
        self.log  = log_fn
        self.prog = prog_fn

    # ── SDK / Java detection ─────────────────────────────

    def find_sdk(self) -> Path | None:
        candidates = [TOOLS_DIR / "sdk"]   # bundled tools/ first
        env = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
        if env:
            candidates.append(Path(env))
        home = Path.home()
        candidates += [
            home / "AppData" / "Local" / "Android" / "Sdk",
            Path("C:/Android/Sdk"),
            Path("C:/Users/Public/Android/Sdk"),
        ]
        for p in candidates:
            if p.exists() and (p / "platforms").exists():
                return p
        for p in candidates:
            if p.exists():
                return p
        return None

    def find_java(self) -> str | None:
        local = TOOLS_DIR / "jre" / "bin" / "java.exe"
        if local.exists():
            return str(local)
        java_home = os.environ.get("JAVA_HOME")
        if java_home:
            j = Path(java_home) / "bin" / "java.exe"
            if j.exists():
                return str(j)
        return shutil.which("java")

    def _patch_gradle_local(self, proj: Path):
        """Point gradle wrapper to the bundled zip for offline builds."""
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
        self.log(f"  ✔ Gradle offline mode: {local_zip.name}")

    # ── Build steps ──────────────────────────────────────

    def check(self) -> bool:
        self.log("  [1/5] Checking environment...")

        self.sdk = self.find_sdk()
        if not self.sdk:
            self.log("  ✘ Android SDK not found!")
            self.log("    → Install Android Studio, or set ANDROID_HOME")
            self.log("    → Or run setup_portable.py to download everything automatically")
            return False
        self.log(f"  ✔ SDK: {self.sdk}")

        self.java = self.find_java()
        if not self.java:
            self.log("  ✘ Java not found!")
            self.log("    → Install JDK 17 from adoptium.net")
            self.log("    → Or run setup_portable.py to download everything automatically")
            return False
        self.log(f"  ✔ Java: {self.java}")

        if not TEMPLATE_DIR.exists():
            self.log(f"  ✘ android_template not found: {TEMPLATE_DIR}")
            return False
        self.log("  ✔ Android template: OK")
        return True

    def prepare_project(self, work: Path) -> Path:
        self.log("\n  [2/5] Preparing Android project...")

        proj = work / "app_project"
        shutil.copytree(TEMPLATE_DIR, proj)
        self.log("  ✔ Template copied")

        cfg          = self.cfg
        pkg          = cfg["package"]
        app_name     = cfg["app_name"]
        version      = cfg["version"]
        version_code = cfg.get("version_code", "1")
        orientation  = cfg.get("orientation", "portrait")
        js_enabled   = "true" if cfg.get("js_enabled", True) else "false"
        zoom_enabled = "true" if cfg.get("zoom_enabled", False) else "false"
        fullscreen   = cfg.get("fullscreen", False)

        fullscreen_code = ""
        if fullscreen:
            fullscreen_code = (
                "requestWindowFeature(Window.FEATURE_NO_TITLE);\n"
                "        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN,\n"
                "            WindowManager.LayoutParams.FLAG_FULLSCREEN);"
            )

        orient_map  = {"portrait": "portrait", "landscape": "landscape", "sensor (auto)": "sensor"}
        orientation = orient_map.get(orientation, "portrait")

        replacements = {
            "{{PACKAGE_NAME}}":    pkg,
            "{{APP_NAME}}":        app_name,
            "{{VERSION_NAME}}":    version,
            "{{VERSION_CODE}}":    version_code,
            "{{ORIENTATION}}":     orientation,
            "{{JS_ENABLED}}":      js_enabled,
            "{{ZOOM_ENABLED}}":    zoom_enabled,
            "{{FULLSCREEN_CODE}}": fullscreen_code,
        }

        for f in [
            proj / "app" / "src" / "main" / "AndroidManifest.xml",
            proj / "app" / "src" / "main" / "res" / "values" / "strings.xml",
            proj / "app" / "build.gradle",
        ]:
            if f.exists():
                txt = f.read_text(encoding="utf-8")
                for k, v in replacements.items():
                    txt = txt.replace(k, v)
                f.write_text(txt, encoding="utf-8")

        # Move Java sources into the correct package directory
        pkg_path = proj / "app" / "src" / "main" / "java" / Path(*pkg.split("."))
        pkg_path.mkdir(parents=True, exist_ok=True)

        java_tmpl = proj / "app" / "src" / "main" / "java" / "com" / "html2apk" / "template"
        if java_tmpl.exists():
            for java_file in java_tmpl.rglob("*.java"):
                rel = java_file.relative_to(java_tmpl)
                txt = java_file.read_text(encoding="utf-8")
                for k, v in replacements.items():
                    txt = txt.replace(k, v)
                dst = pkg_path / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(txt, encoding="utf-8")

            # Remove old template package dir to avoid Gradle seeing duplicate sources
            old_tmpl = proj / "app" / "src" / "main" / "java" / "com" / "html2apk" / "template"
            if old_tmpl.exists() and old_tmpl.resolve() != pkg_path.resolve():
                shutil.rmtree(old_tmpl, ignore_errors=True)
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

    def inject_assets(self, proj: Path):
        self.log("\n  [3/5] Injecting user assets...")

        cfg = self.cfg
        www = proj / "app" / "src" / "main" / "assets" / "www"
        www.mkdir(parents=True, exist_ok=True)

        html_src = Path(cfg["html_path"])
        shutil.copy(html_src, www / "index.html")
        self.log(f"  ✔ HTML copied ({html_src.stat().st_size:,} bytes)")

        res_dir    = proj / "app" / "src" / "main" / "res"
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
                    img  = Image.new("RGBA", (sz, sz), (37, 99, 235, 255))
                    draw = ImageDraw.Draw(img)
                    m    = sz // 6
                    draw.ellipse([m, m, sz - m, sz - m], fill=(255, 255, 255, 220))
                    img.save(dest)
            self.log("  ✔ Icon: custom" if icon_src else "  ✔ Icon: default generated")
        except Exception as e:
            self.log(f"  ⚠ Icon error: {e}")

    def write_local_properties(self, proj: Path):
        sdk_path = str(self.sdk).replace("\\", "/")
        (proj / "local.properties").write_text(
            f"sdk.dir={sdk_path}\n"
            f"java.home={Path(self.java).parent.parent}\n",
            encoding="utf-8",
        )
        self.log("  ✔ local.properties written")

    def run_gradle(self, proj: Path) -> Path | None:
        self.log("\n  [4/5] Running Gradle build...")
        self.log("  (First run may take 3-5 min to download Gradle)")
        self._patch_gradle_local(proj)

        gradlew = proj / "gradlew.bat"
        if not gradlew.exists():
            src_gw = TEMPLATE_DIR / "gradlew.bat"
            if src_gw.exists():
                shutil.copy(src_gw, gradlew)

        if not gradlew.exists():
            self.log("  ✘ gradlew.bat not found!")
            self.log("  → Run setup_portable.py or setup_sdk.py first")
            return None

        env = os.environ.copy()
        env["ANDROID_HOME"]     = str(self.sdk)
        env["ANDROID_SDK_ROOT"] = str(self.sdk)
        env["JAVA_HOME"]        = str(Path(self.java).parent.parent)

        cmd = [str(gradlew), "assembleDebug"]
        if sys.platform == "win32":
            cmd = ["cmd", "/c"] + cmd

        try:
            proc = subprocess.Popen(
                cmd, cwd=proj, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
            )
        except Exception as e:
            self.log(f"  ✘ Failed to start Gradle: {e}")
            return None

        all_lines = []
        for raw in proc.stdout:
            line = raw.rstrip()
            all_lines.append(line)
            low = line.lower()
            if (line.startswith((">", "*", "e:")) or
                    any(k in low for k in ["error", "failed", "exception", "warning:", "build "])):
                self.log("  " + line[:200])

        proc.wait()

        if proc.returncode != 0:
            self.log("\n  ✘ Gradle build failed")
            relevant = [l for l in all_lines if l.strip() and
                        any(k in l.lower() for k in
                            ["error", "failed", "exception", "could not", "unresolved",
                             "what went wrong", "try:", "task :", "compilation"])]
            if relevant:
                self.log("  ── Error details ──")
                for line in relevant[-25:]:
                    self.log("  " + line[:200])
            else:
                self.log("  ── Last output ──")
                for line in all_lines[-15:]:
                    if line.strip():
                        self.log("  " + line[:200])
            return None

        apk_files = list(proj.glob("**/outputs/apk/debug/*.apk"))
        if not apk_files:
            self.log("  ✘ APK not found after build")
            return None

        self.log(f"  ✔ APK built: {apk_files[0].name}")
        return apk_files[0]

    def deliver(self, apk_src: Path) -> Path:
        self.log("\n  [5/5] Saving APK...")

        out_name = re.sub(r"\s+", "_", self.cfg["app_name"]) + ".apk"
        out_path = Path(self.cfg["html_path"]).parent / out_name
        shutil.copy(apk_src, out_path)

        size_mb = out_path.stat().st_size / 1024 / 1024
        self.log(f"  ✔ Saved: {out_path}")
        self.log(f"  ✔ Size: {size_mb:.1f} MB")
        return out_path

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
            self.log(f"  ✘ Unexpected error: {e}")
            import traceback
            self.log(traceback.format_exc())
            return None


# ══════════════════════════════════════════════════════════
#  GUI
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
        hdr = ctk.CTkFrame(self, fg_color=PRIMARY, corner_radius=0, height=60)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="⚡ HTML2APK Studio",
                     font=("Segoe UI Bold", 18), text_color="white").pack(side="left", padx=22)
        ctk.CTkLabel(hdr, text="v2 — Gradle Build",
                     font=("Segoe UI", 11), text_color="#BFDBFE").pack(side="left")

        scroll = ctk.CTkScrollableFrame(self, fg_color=BG)
        scroll.pack(fill="both", expand=True)
        b = scroll

        # ① HTML File
        s1 = Card(b, "① HTML File")
        s1.pack(fill="x", padx=18, pady=6)
        self.html_drop = DropZone(
            s1, "Select your HTML file", "Click to browse",
            [("HTML", "*.html *.htm"), ("All", "*.*")],
            self._on_html, False,
        )
        self.html_drop.pack(fill="x", padx=14, pady=(4, 14))
        self.html_info = ctk.CTkLabel(s1, text="", font=("Segoe UI", 10),
                                       text_color=TEXT_M, anchor="w", wraplength=620)
        self.html_info.pack(anchor="w", padx=14, pady=(0, 8))

        # ② App Info
        s2 = Card(b, "② App Info")
        s2.pack(fill="x", padx=18, pady=6)
        g = ctk.CTkFrame(s2, fg_color="transparent")
        g.pack(fill="x", padx=14, pady=(4, 14))
        g.columnconfigure((0, 1), weight=1)

        self.f_name = Field(g, "App Name",    "e.g. My Calculator")
        self.f_pkg  = Field(g, "Package Name","e.g. com.myname.calc")
        self.f_ver  = Field(g, "Version",     "1.0")
        self.f_desc = Field(g, "Description", "Short description...")

        self.f_name.grid(row=0, column=0, padx=(0, 6), pady=4, sticky="ew")
        self.f_pkg.grid (row=0, column=1, padx=(6, 0), pady=4, sticky="ew")
        self.f_ver.grid (row=1, column=0, padx=(0, 6), pady=4, sticky="ew")
        self.f_desc.grid(row=1, column=1, padx=(6, 0), pady=4, sticky="ew")
        self.f_ver.set("1.0")

        row2 = ctk.CTkFrame(g, fg_color="transparent")
        row2.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ctk.CTkLabel(row2, text="Orientation", font=("Segoe UI", 11),
                     text_color=TEXT_M).pack(side="left", padx=(0, 6))
        self.orient = ctk.CTkOptionMenu(
            row2, values=["portrait", "landscape", "sensor (auto)"],
            font=("Segoe UI", 11), width=160,
            fg_color=CARD, text_color=TEXT,
            button_color=BORDER, button_hover_color=PRIMARY,
            dropdown_fg_color=CARD, dropdown_text_color=TEXT,
        )
        self.orient.pack(side="left")

        # ③ Icon
        s3 = Card(b, "③ Icon (optional)")
        s3.pack(fill="x", padx=18, pady=6)
        ar = ctk.CTkFrame(s3, fg_color="transparent")
        ar.pack(fill="x", padx=14, pady=(4, 14))
        ar.columnconfigure((0, 1), weight=1)
        self.icon_drop = DropZone(
            ar, "App Icon", "PNG 512×512 recommended",
            [("Image", "*.png *.jpg *.jpeg")],
            lambda p: None, preview=True,
        )
        self.icon_drop.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        # ④ Native Bridge
        s_bridge = Card(b, "④ Native JS Bridge")
        s_bridge.pack(fill="x", padx=18, pady=6)
        bridge_frame = ctk.CTkFrame(s_bridge, fg_color="transparent")
        bridge_frame.pack(fill="x", padx=14, pady=(4, 10))
        ctk.CTkLabel(
            bridge_frame,
            text=(
                "html2apk.js is auto-injected into every page.\n"
                "Use these APIs in your HTML:\n"
                "  • H2ABridge.call('device',    { action: 'info' }, cb)      — device info\n"
                "  • H2ABridge.call('vibration', { duration: 500 })           — vibrate 500ms\n"
                "  • H2ABridge.call('toast',     { message: 'Hi!' })          — show toast\n"
                "  • H2ABridge.call('network',   { action: 'status' }, cb)    — network status\n"
                "  • H2ABridge.call('clipboard', { action: 'copy', text: … }) — copy text\n"
                "  • document.addEventListener('html2apkready', fn)           — bridge ready"
            ),
            font=("Consolas", 10), text_color=TEXT,
            justify="left", anchor="w",
        ).pack(anchor="w")

        # ⑤ Gradle Settings
        s4 = Card(b, "⑤ Gradle Settings")
        s4.pack(fill="x", padx=18, pady=6)
        adv = ctk.CTkFrame(s4, fg_color="transparent")
        adv.pack(fill="x", padx=14, pady=(4, 14))

        self.js_on   = self._cb(adv, "JavaScript enabled", True)
        self.zoom_on = self._cb(adv, "Zoom enabled", False)
        self.fs_on   = self._cb(adv, "Fullscreen", False)

        sdk_row = ctk.CTkFrame(s4, fg_color="transparent")
        sdk_row.pack(fill="x", padx=14, pady=(0, 14))
        ctk.CTkLabel(sdk_row, text="ANDROID_HOME (optional):",
                     font=("Segoe UI", 11), text_color=TEXT_M).pack(side="left", padx=(0, 8))
        self.sdk_entry = ctk.CTkEntry(
            sdk_row, placeholder_text="Auto-detected",
            font=("Segoe UI", 11), height=32,
            fg_color=CARD, border_color=BORDER, text_color=TEXT,
        )
        self.sdk_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            sdk_row, text="Browse", width=70, height=32,
            font=("Segoe UI", 11), fg_color=BORDER, text_color=TEXT,
            hover_color="#CBD5E1", command=self._pick_sdk,
        ).pack(side="left", padx=(6, 0))

        # Build button
        self.btn = ctk.CTkButton(
            b, text="⚡  Build APK",
            height=50, font=("Segoe UI Bold", 16),
            fg_color=PRIMARY, hover_color=PRIMARY_H,
            corner_radius=12, command=self._start,
        )
        self.btn.pack(fill="x", padx=18, pady=(8, 6))

        self.log_widget = BuildLog(b)
        self.log_widget.pack(fill="x", padx=18, pady=(0, 16))

        ctk.CTkLabel(b, text="HTML2APK Studio v2  •  Gradle + Native Bridge",
                     font=("Segoe UI", 10), text_color=TEXT_M).pack(pady=(0, 14))

    def _cb(self, parent, text, default):
        var = tk.BooleanVar(value=default)
        ctk.CTkCheckBox(
            parent, text=text, variable=var,
            font=("Segoe UI", 11), text_color=TEXT,
            fg_color=PRIMARY, hover_color=PRIMARY_H,
        ).pack(side="left", padx=(0, 20), pady=4)
        return var

    def _pick_sdk(self):
        p = filedialog.askdirectory(title="Select Android SDK folder")
        if p:
            self.sdk_entry.delete(0, "end")
            self.sdk_entry.insert(0, p)
            os.environ["ANDROID_HOME"] = p

    def _on_html(self, path):
        stem = Path(path).stem.replace("_", " ").replace("-", " ").title()
        if not self.f_name.get():
            self.f_name.set(stem)
        if not self.f_pkg.get():
            slug = re.sub(r"[^a-z0-9]", "", stem.lower())
            self.f_pkg.set(f"com.myapp.{slug or 'app'}")
        try:
            txt = Path(path).read_text(encoding="utf-8", errors="replace")
            self.html_info.configure(text=f"Preview: {txt[:180].strip()}...")
        except Exception:
            pass

    def _start(self):
        if self.building:
            return

        if not self.html_drop.filepath:
            messagebox.showerror("Error", "Please select an HTML file.")
            return
        if not self.f_name.get():
            messagebox.showerror("Error", "Please enter an App Name.")
            return
        if not self.f_pkg.get():
            messagebox.showerror("Error", "Please enter a Package Name.")
            return

        sdk_manual = self.sdk_entry.get()
        if sdk_manual:
            os.environ["ANDROID_HOME"] = sdk_manual

        self.building = True
        self.btn.configure(text="⏳  Building...", state="disabled", fg_color=TEXT_M)
        self.log_widget.clear()
        self.log_widget.write("═" * 46)
        self.log_widget.write("  Starting APK build...")

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
            self.btn.configure(text="✅  Build Successful!", fg_color=SUCCESS, state="normal")
            self.log_widget.write("═" * 46)
            if messagebox.askyesno("Done!", f"APK built successfully!\n\n{out_path}\n\nOpen output folder?"):
                os.startfile(out_path.parent)
        else:
            self.btn.configure(text="⚡  Build APK", fg_color=PRIMARY, state="normal")
            self.log_widget.write("═" * 46)
            self.log_widget.write("  ✘ Build failed. Check the log above.")


if __name__ == "__main__":
    App().mainloop()
