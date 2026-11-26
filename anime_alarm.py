"""ল্যাপটপ গার্ড: কেউ ল্যাপটপে হাত দিলে ছবি দেখায় আর মানা করে।

ইনস্টল:  pip install pynput pillow psutil gTTS pygame-ce
চালানো:  python laptop_guard.py   (পাশে girl.jpg রাখুন)
বন্ধ:     কিবোর্ডে পাসওয়ার্ড টাইপ করুন (English লেআউটে)
"""
import sys
import tkinter as tk
from pathlib import Path

import psutil
from PIL import Image, ImageTk
from pynput import keyboard, mouse

# ---------- নিজের মতো বদলান ----------
PASSWORD = "1234"
MESSAGE = "এই! দয়া করে আমার ল্যাপটপ ধরবে না!"
ARM_SECONDS = 5      # চালু করার পর সরে যাওয়ার সময়
MOVE_LIMIT = 15      # মাউস কত পিক্সেল নড়লে ধরা পড়বে
# -------------------------------------

FOLDER = Path(__file__).resolve().parent
IMAGE_FILE = FOLDER / "my_girl.png"
SOUND_FILE = FOLDER / "warn.mp3"   # নিজের রেকর্ড করা ভয়েসও রাখতে পারেন

armed = False
triggered = False
quit_now = False
typed = ""
start_pos = None


def prepare_sound():
    """ভয়েস ফাইল না থাকলে বানায় (প্রথমবার ইন্টারনেট লাগে)।"""
    try:
        import pygame
        if not SOUND_FILE.exists():
            from gtts import gTTS
            gTTS(MESSAGE, lang="bn").save(str(SOUND_FILE))
        pygame.mixer.init()
        pygame.mixer.music.load(str(SOUND_FILE))
        return pygame.mixer.music
    except Exception as error:
        print("সাউন্ড চালু হয়নি:", error)
        SOUND_FILE.exists() and SOUND_FILE.stat().st_size == 0 and SOUND_FILE.unlink()
        return None


def on_key(key):
    global typed, triggered, quit_now
    if armed:
        triggered = True
    char = getattr(key, "char", None)
    if char:
        typed = (typed + char)[-len(PASSWORD):]
        if typed == PASSWORD:
            quit_now = True


def on_move(x, y):
    global start_pos, triggered
    if not armed:
        return
    if start_pos is None:
        start_pos = (x, y)
    elif abs(x - start_pos[0]) + abs(y - start_pos[1]) > MOVE_LIMIT:
        triggered = True


def on_click_or_scroll(*_):
    global triggered
    if armed:
        triggered = True


def main():
    if not IMAGE_FILE.exists():
        sys.exit(f"ছবি পাওয়া যায়নি। ছবিটা এখানে রাখুন: {IMAGE_FILE}")

    sound = prepare_sound()
    root = tk.Tk()
    root.withdraw()

    screen = tk.Toplevel(root)
    screen.withdraw()
    screen.configure(bg="black")
    screen.protocol("WM_DELETE_WINDOW", lambda: None)

    width, height = root.winfo_screenwidth(), root.winfo_screenheight()
    picture = Image.open(IMAGE_FILE).convert("RGB")
    picture.thumbnail((width, int(height * 0.85)))
    photo = ImageTk.PhotoImage(picture)
    tk.Label(screen, image=photo, bg="black").pack(expand=True)
    tk.Label(screen, text=MESSAGE, fg="#c77dff", bg="black",
             font=("Nirmala UI", 32, "bold")).pack(pady=20)

    keyboard.Listener(on_press=on_key).start()
    mouse.Listener(on_move=on_move, on_click=on_click_or_scroll,
                   on_scroll=on_click_or_scroll).start()

    battery = psutil.sensors_battery()
    was_plugged = bool(battery and battery.power_plugged)
    showing = False

    def arm():
        global armed, typed, triggered
        nonlocal was_plugged
        typed, triggered, armed = "", False, True
        now = psutil.sensors_battery()
        was_plugged = bool(now and now.power_plugged)
        print("পাহারা চালু!")

    def check():
        nonlocal showing
        if quit_now:
            root.destroy()
            return
        now = psutil.sensors_battery()
        unplugged = armed and was_plugged and now and now.power_plugged is False
        if (triggered or unplugged) and not showing:
            showing = True
            screen.deiconify()
            screen.attributes("-fullscreen", True)
            screen.attributes("-topmost", True)
            screen.focus_force()
        if showing:
            screen.lift()
            if sound and not sound.get_busy():
                sound.play()
        root.after(200, check)

    print(f"{ARM_SECONDS} সেকেন্ড পর পাহারা শুরু হবে...")
    root.after(ARM_SECONDS * 1000, arm)
    check()
    root.mainloop()


if __name__ == "__main__":
    main()