# ================= DEBUG =================
DEBUG = False

def debug(*args):
    if DEBUG:
        print("[DEBUG]:", *args)