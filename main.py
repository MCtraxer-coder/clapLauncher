import webview
import sounddevice as sd
import numpy as np
import subprocess
import webbrowser
import time
import yaml
import os
import sys
import threading
from pathlib import Path
import sys, io
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def resource_path(rel):
    base = getattr(sys, "_MEIPASS", Path(__file__).parent)
    return str(Path(base) / rel)


def user_path(name):
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent
    return str(base / name)


CONFIG_FILE = user_path("clap_config.yaml")
DEFAULT_CONFIG = {
    "threshold": 0.3,
    "claps_required": 2,
    "clap_window": 1.5,
    "cooldown": 2.0,
    "action_type": "app",
    "action_target": "notepad.exe",
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return {**DEFAULT_CONFIG, **cfg}
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True)

class Api:
    def __init__(self):
        self.cfg = load_config()
        self.detector = None
        self.window = None
        self.running = False

    def set_window(self, w):
        self.window = w

    def get_config(self):
        return self.cfg

    def save_settings(self, data):
        self.cfg.update({
            "threshold": float(data["threshold"]),
            "claps_required": int(data["claps_required"]),
            "clap_window": float(data["clap_window"]),
            "cooldown": float(data["cooldown"]),
            "action_type": data["action_type"],
            "action_target": data["action_target"],
        })
        save_config(self.cfg)
        return {"ok": True}

    def calibrate(self):
        threading.Thread(target=self._calibrate_worker, daemon=True).start()
        return {"ok": True}

    def _calibrate_worker(self):
        sr = 44100

        self._log("🎤 Слушаю тишину 3 сек...")
        rec = sd.rec(int(3 * sr), samplerate=sr, channels=1)
        sd.wait()
        noise = float(np.sqrt(np.mean(rec ** 2)))

        self._log("👏 Хлопни один раз (2 сек)...")
        rec = sd.rec(int(2 * sr), samplerate=sr, channels=1)
        sd.wait()
        peak = float(np.max(np.abs(rec)))

        suggested = round(max(0.05, noise * 5), 3)
        self._log(f"Фон: {noise:.4f} | Пик: {peak:.4f} | Порог: {suggested}")

        self._eval(f"window.onCalibrated && window.onCalibrated({suggested})")

    def start(self):
        if self.running:
            return {"ok": False, "msg": "Уже запущено"}
        self.running = True
        self.detector = ClapDetector(self.cfg, self._on_clap, self._log)
        threading.Thread(target=self.detector.run, daemon=True).start()
        self._log("▶️ Слушаю хлопки...")
        return {"ok": True}

    def stop(self):
        if self.detector:
            self.detector.stop()
        self.running = False
        self._log("⏹️ Остановлено")
        return {"ok": True}

    def test_action(self):
        self._trigger(self.cfg["action_type"], self.cfg["action_target"])
        return {"ok": True}

    def _on_clap(self, count):
        self._eval(f"window.onClap && window.onClap({count})")

    def _log(self, msg):
        safe = msg.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
        self._eval(f"window.onLog && window.onLog('{safe}')")

    def _eval(self, js):
        if self.window:
            try:
                self.window.evaluate_js(js)
            except Exception:
                pass

    def _trigger(self, action, target):
        try:
            if action == "url":
                webbrowser.open(target)
            else:
                if sys.platform.startswith("win"):
                    os.startfile(target)
                else:
                    subprocess.Popen(target, shell=True)
            self._log(f"🚀 Запущено: {target}")
        except Exception as e:
            self._log(f"❌ Ошибка: {e}")
class ClapDetector:
    def __init__(self, cfg, on_clap, log):
        self.cfg = cfg
        self.on_clap = on_clap
        self.log = log
        self.clap_times = []
        self.last_trigger = 0
        self._stop = False

    def audio_callback(self, indata, frames, t, status):
        if status:
            return
        rms = float(np.sqrt(np.mean(indata ** 2)))
        if rms > self.cfg["threshold"]:
            now = time.time()
            if self.clap_times and (now - self.clap_times[-1]) < 0.15:
                return
            if (now - self.last_trigger) < self.cfg["cooldown"]:
                return

            self.clap_times.append(now)
            self.log(f"👏 Хлопок #{len(self.clap_times)} ({rms:.3f})")

            self.clap_times = [x for x in self.clap_times
                               if now - x <= self.cfg["clap_window"]]

            if len(self.clap_times) >= self.cfg["claps_required"]:
                self.log("✅ Срабатывание!")
                self.on_clap(0)
                self.clap_times.clear()
                self.last_trigger = now
                api._trigger(self.cfg["action_type"], self.cfg["action_target"])

    def run(self):
        with sd.InputStream(callback=self.audio_callback, channels=1,
                            samplerate=44100, blocksize=1024):
            while not self._stop:
                time.sleep(0.1)

    def stop(self):
        self._stop = True

api = Api()

if __name__ == "__main__":
    window = webview.create_window(
        "Clap Launcher",
        url=resource_path("ui/index.html"),
        js_api=api,
        width=520,
        height=720,
        min_size=(480, 600),
        background_color="#0f1115",
        text_select=False,
        easy_drag=False,
        frameless=False,
    )
    api.set_window(window)
    webview.start(debug=False)
