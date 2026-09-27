import os
import sys


def clear_vlc_cache():
    """
    Удаляет кэш обложек VLC (%APPDATA%/vlc/art).
    Explorer не трогает.
    """
    import shutil
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return 0

    vlc_art = os.path.join(appdata, "vlc", "art")
    if not os.path.isdir(vlc_art):
        return 0

    try:
        shutil.rmtree(vlc_art, ignore_errors=True)
        print(f"🧹 Кэш VLC удалён: {vlc_art}")
        return 1
    except Exception as e:
        print(f"⚠️ Не удалось удалить кэш VLC: {e}")
        return 0


def clear_thumbnail_cache(file_path=None):
    """
    Просит Windows сбросить кэш эскизов.
    - file_path указан → только для этого файла (SHCNE_UPDATEITEM).
    - file_path=None → весь кэш (SHCNE_ASSOCCHANGED).
    Explorer НЕ перезапускается.
    """
    if sys.platform != "win32":
        return 0

    try:
        import ctypes

        if file_path and os.path.exists(file_path):
            SHCNE_UPDATEITEM = 0x00002000
            SHCNF_PATHW = 0x0005
            ctypes.windll.shell32.SHChangeNotify(
                SHCNE_UPDATEITEM, SHCNF_PATHW,
                str(file_path), None
            )
            print(f"🔄 Кэш обновлён для: {os.path.basename(file_path)}")
            return 1
        else:
            SHCNE_ASSOCCHANGED = 0x08000000
            SHCNF_IDLIST = 0x0000
            ctypes.windll.shell32.SHChangeNotify(
                SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None
            )
            print("🔄 Кэш эскизов сброшен (весь)")
            return 1
    except Exception as e:
        print(f"⚠️ Не удалось сбросить кэш: {e}")
        return 0