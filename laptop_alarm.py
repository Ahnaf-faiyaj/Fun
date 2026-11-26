"""
ল্যাপটপ অ্যালার্ম
ইনস্টল:  pip install pynput psutil opencv-python
চালানো:  python laptop_alarm.py
"""
import getpass
import math
import os
import platform
import shutil
import struct
import subprocess
import tempfile
import threading
import time
import wave

import psutil
from pynput import keyboard, mouse

try:
    import cv2  # ক্যামেরা (না থাকলেও বাকি সব চলবে)
except ImportError:
    cv2 = None

PASSWORD = "1234"      # নিজের পাসওয়ার্ড দিন
ARM_DELAY = 10         # চালু হওয়ার আগে সময় (সেকেন্ড)
MOUSE_LIMIT = 15       # মাউস কত পিক্সেল নড়লে অ্যালার্ম
CAMERA_LIMIT = 0.30    # ছবির কত অংশ বদলালে অ্যালার্ম (0 থেকে 1)
USE_CAMERA = True

armed = threading.Event()
alarm_on = threading.Event()
stopped = threading.Event()


def make_siren():
    """সাইরেনের শব্দ একটি wav ফাইলে তৈরি করে"""
    path = os.path.join(tempfile.gettempdir(), "siren.wav")
    rate = 44100
    frames = bytearray()
    phase = 0.0
    for i in range(rate * 2):
        t = i / rate
        freq = 1200 + 600 * math.sin(2 * math.pi * 2 * t)
        phase += 2 * math.pi * freq / rate
        frames += struct.pack("<h", int(32000 * math.sin(phase)))
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(bytes(frames))
    return path


def play_siren(path):
    system = platform.system()
    if system == "Windows":
        import winsound
        winsound.PlaySound(
            path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP
        )
        stopped.wait()
        winsound.PlaySound(None, 0)
        return

    if system == "Darwin":
        player = "afplay"
    else:
        player = shutil.which("paplay") or shutil.which("aplay")

    while not stopped.is_set():
        if player:
            proc = subprocess.Popen([player, path])
            while proc.poll() is None:
                if stopped.is_set():
                    proc.terminate()
                    break
                time.sleep(0.1)
        else:
            print("\a", end="", flush=True)
            time.sleep(0.5)


def trigger(reason):
    if armed.is_set() and not alarm_on.is_set():
        alarm_on.set()
        print(f"\n!!! অ্যালার্ম: {reason} !!!")
        threading.Thread(target=play_siren, args=(SIREN,), daemon=True).start()


# ---------- মাউস / টাচপ্যাড ----------
start_pos = None


def on_move(x, y):
    global start_pos
    if not armed.is_set():
        return
    if start_pos is None:
        start_pos = (x, y)
    elif math.dist(start_pos, (x, y)) > MOUSE_LIMIT:
        trigger("মাউস/টাচপ্যাড ধরা হয়েছে")


def on_click(x, y, button, pressed):
    trigger("ক্লিক করা হয়েছে")


def on_scroll(x, y, dx, dy):
    trigger("স্ক্রল করা হয়েছে")


# ---------- কিবোর্ড ----------
def on_press(key):
    trigger("কিবোর্ড চাপা হয়েছে")


# ---------- চার্জার ----------
def watch_charger():
    battery = psutil.sensors_battery()
    if battery is None:
        return
    was_plugged = battery.power_plugged
    while not stopped.is_set():
        battery = psutil.sensors_battery()
        if battery is not None:
            if was_plugged and battery.power_plugged is False:
                trigger("চার্জার খোলা হয়েছে")
            was_plugged = battery.power_plugged
        time.sleep(0.5)


# ---------- ক্যামেরা (ল্যাপটপ তুললে বা নাড়ালে) ----------
def watch_camera():
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("\nক্যামেরা পাওয়া যায়নি, বাকি সেন্সর চলছে।")
        return
    previous = None
    while not stopped.is_set():
        ok, frame = cam.read()
        if not ok:
            time.sleep(0.2)
            continue
        gray = cv2.cvtColor(cv2.resize(frame, (320, 240)), cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        if previous is not None:
            diff = cv2.absdiff(previous, gray)
            changed = (diff > 25).mean()
            if changed > CAMERA_LIMIT:
                trigger("ল্যাপটপ নাড়ানো হয়েছে")
        previous = gray
        time.sleep(0.2)
    cam.release()


SIREN = make_siren()


def main():
    mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll).start()
    keyboard.Listener(on_press=on_press).start()
    threading.Thread(target=watch_charger, daemon=True).start()
    if USE_CAMERA and cv2 is not None:
        threading.Thread(target=watch_camera, daemon=True).start()

    print(f"{ARM_DELAY} সেকেন্ড পর অ্যালার্ম চালু হবে। হাত সরিয়ে নিন।")
    for i in range(ARM_DELAY, 0, -1):
        print(i, end=" ", flush=True)
        time.sleep(1)
    armed.set()
    print("\nঅ্যালার্ম চালু আছে। বন্ধ করতে পাসওয়ার্ড লিখে Enter দিন।")

    while True:
        try:
            if getpass.getpass("পাসওয়ার্ড: ") == PASSWORD:
                break
            print("ভুল পাসওয়ার্ড!")
        except (KeyboardInterrupt, EOFError):
            print("\nপাসওয়ার্ড ছাড়া বন্ধ হবে না।")
            time.sleep(0.5)

    armed.clear()
    stopped.set()
    time.sleep(0.5)
    print("অ্যালার্ম বন্ধ হয়েছে।")


if __name__ == "__main__":
    main()