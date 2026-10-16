import os, shutil, subprocess
def _have(c): return shutil.which(c) is not None
def is_termux(): return "com.termux" in os.environ.get("PREFIX","")
def wake_lock():
    if not _have("termux-wake-lock"): return False
    try:
        subprocess.run(["termux-wake-lock"],check=False,
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        return True
    except Exception: return False
def wake_unlock():
    if not _have("termux-wake-unlock"): return
    try:
        subprocess.run(["termux-wake-unlock"],check=False,
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except Exception: pass
def notify(t,b):
    if not _have("termux-notification"): return
    try:
        subprocess.run(["termux-notification","--title",t,"--content",b,
                        "--priority","high"],check=False,
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except Exception: pass
