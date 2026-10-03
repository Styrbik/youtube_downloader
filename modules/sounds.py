import os
import sys
import wave
import struct
import math
import tempfile

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# Куда сохраняем сгенерированные звуки
if getattr(sys, 'frozen', False):
    SOUNDS_DIR = os.path.join(tempfile.gettempdir(), "ytdl_sounds")
else:
    SOUNDS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sounds_cache")
os.makedirs(SOUNDS_DIR, exist_ok=True)

SAMPLE_RATE = 44100

# Глобальный флаг — выключатель звуков
SOUNDS_ENABLED = True


def _generate_slide(filename, f1, f2, duration_ms=200, volume=0.3):
    """Генерирует .wav с плавным перетеканием от f1 до f2."""
    path = os.path.join(SOUNDS_DIR, filename)
    if os.path.exists(path):
        return path

    n_samples = int(SAMPLE_RATE * duration_ms / 1000)
    with wave.open(path, 'w') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        frames = bytearray()
        phase = 0.0
        for i in range(n_samples):
            t = i / (n_samples - 1) if n_samples > 1 else 0
            # Линейная интерполяция частоты
            freq = f1 + (f2 - f1) * t
            # Фаза накапливается для непрерывности
            phase += 2 * math.pi * freq / SAMPLE_RATE
            # Плавное появление и затухание (envelope)
            env = math.sin(math.pi * t)
            sample = int(volume * env * 32767 * math.sin(phase))
            frames += struct.pack('<h', sample)
        wav.writeframes(bytes(frames))
    return path


def _play(path, async_=False):
    if not SOUNDS_ENABLED:
        return
    if HAS_WINSOUND and os.path.exists(path):
        flags = winsound.SND_FILENAME
        if async_:
            flags |= winsound.SND_ASYNC
        winsound.PlaySound(path, flags)


# ===== Звуки =====

def click():
    _play(_generate_slide("click.wav", 1400, 900, 80, 0.25), async_=True)
    
def ice_crack():
    """Хруст льда — из файла."""
    try:
        from config import BASE_DIR
        path = os.path.join(BASE_DIR, "admin_assets", "sounds", "ice_crack.wav")
        if os.path.exists(path):
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            return
    except Exception as e:
        print(f"⚠️ ice_crack: {e}")

    # fallback — сгенерированный
    _play(_generate_slide("ice_crack1.wav", 3000, 800, 60, 0.5), async_=False)
    _play(_generate_slide("ice_crack2.wav", 2500, 400, 80, 0.4), async_=True)

def radio():
    _play(_generate_slide("radio.wav", 800, 1300, 60, 0.2), async_=True)

def fetch():
    _play(_generate_slide("fetch.wav", 600, 1200, 250, 0.25), async_=True)

def download_start():
    _play(_generate_slide("start.wav", 500, 900, 300, 0.25), async_=True)

def done():
    # Два звука подряд: вверх и вниз
    _play(_generate_slide("done_up.wav", 600, 1400, 200, 0.3))
    _play(_generate_slide("done_down.wav", 1400, 700, 300, 0.3))

def error():
    _play(_generate_slide("error.wav", 700, 200, 350, 0.3), async_=True)

def warning():
    _play(_generate_slide("warn1.wav", 1000, 1200, 100, 0.25))
    _play(_generate_slide("warn2.wav", 1000, 1200, 100, 0.25))

def folder_pick():
    _play(_generate_slide("folder.wav", 800, 1300, 150, 0.25), async_=True)

def file_saved():
    _play(_generate_slide("saved.wav", 1200, 1800, 200, 0.3), async_=True)

def startup():
    _play(_generate_slide("startup1.wav", 400, 800, 200, 0.25))
    _play(_generate_slide("startup2.wav", 800, 1200, 200, 0.25))

def shutdown():
    _play(_generate_slide("shutdown1.wav", 1200, 600, 250, 0.25))
    _play(_generate_slide("shutdown2.wav", 600, 300, 250, 0.25))
    
def list_click():
    """Звук при выборе строки в списке форматов."""
    _play(_generate_slide("list_click.wav", 1000, 1400, 70, 0.2), async_=True)
  
def play_admin_mp3(filename):
    """Играет mp3 из admin_assets/sounds/."""
    try:
        from config import BASE_DIR
        path = os.path.join(BASE_DIR, "admin_assets", "sounds", filename)

        if not os.path.exists(path):
            print(f"⚠️ Файл не найден: {path}")
            return False

        # mp3 — через pygame
        if filename.lower().endswith(".mp3"):
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            print(f"🔊 Играю: {filename}")
            return True

        # wav — через winsound
        if filename.lower().endswith(".wav"):
            _play(path, async_=False)
            print(f"🔊 Играю: {filename}")
            return True

        return False
    except Exception as e:
        print(f"⚠️ Ошибка воспроизведения: {e}")
        return False