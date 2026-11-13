"""专属番茄钟应用图标绘制与加载模块。"""

import ctypes
import math
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageTk

from config import ASSETS_DIR, ICON_ICO_PATH, ICON_PNG_PATH

APP_USER_MODEL_ID = "antigravity.pomodoro.timer.app.1"
_ICO_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def _draw_pomodoro_icon(size: int = 256) -> Image.Image:
    """绘制高清番茄钟图标（深色圆角底座 + 番茄红表盘 + 翠绿蒂叶 + 刻度指针）。"""
    # 在 2 倍超采样画布上绘制后缩放到目标尺寸，边缘更平滑
    scale = 2
    canvas_size = size * scale
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. 深色圆角底座
    pad = int(canvas_size * 0.04)
    radius = int(canvas_size * 0.22)
    draw.rounded_rectangle(
        [pad, pad, canvas_size - pad, canvas_size - pad],
        radius=radius,
        fill="#18181B",
        outline="#3F3F46",
        width=max(2, int(canvas_size * 0.015)),
    )

    # 2. 番茄红圆形主体（略微下移给顶部蒂叶留空间）
    cx = canvas_size // 2
    cy = int(canvas_size * 0.55)
    body_r = int(canvas_size * 0.34)
    draw.ellipse(
        [cx - body_r, cy - body_r, cx + body_r, cy + body_r],
        fill="#EF4444",
        outline="#DC2626",
        width=max(2, int(canvas_size * 0.015)),
    )

    # 左上角柔和光泽弧点缀
    highlight_r = int(body_r * 0.22)
    hx = cx - int(body_r * 0.42)
    hy = cy - int(body_r * 0.38)
    draw.ellipse(
        [hx - highlight_r, hy - highlight_r // 2, hx + highlight_r, hy + highlight_r // 2],
        fill=(255, 255, 255, 55),
    )

    # 3. 顶部翠绿番茄蒂叶
    stem_top_y = cy - body_r - int(canvas_size * 0.06)
    stem_base_y = cy - body_r + int(canvas_size * 0.03)
    draw.rounded_rectangle(
        [
            cx - int(canvas_size * 0.025),
            stem_top_y,
            cx + int(canvas_size * 0.025),
            stem_base_y,
        ],
        radius=max(2, int(canvas_size * 0.012)),
        fill="#10B981",
    )

    leaf_left = [
        (cx, stem_base_y),
        (cx - int(canvas_size * 0.14), stem_base_y - int(canvas_size * 0.08)),
        (cx - int(canvas_size * 0.08), stem_base_y + int(canvas_size * 0.04)),
    ]
    leaf_right = [
        (cx, stem_base_y),
        (cx + int(canvas_size * 0.14), stem_base_y - int(canvas_size * 0.08)),
        (cx + int(canvas_size * 0.08), stem_base_y + int(canvas_size * 0.04)),
    ]
    leaf_mid = [
        (cx - int(canvas_size * 0.05), stem_base_y + int(canvas_size * 0.01)),
        (cx, stem_base_y + int(canvas_size * 0.07)),
        (cx + int(canvas_size * 0.05), stem_base_y + int(canvas_size * 0.01)),
    ]
    draw.polygon(leaf_left, fill="#10B981")
    draw.polygon(leaf_right, fill="#10B981")
    draw.polygon(leaf_mid, fill="#059669")

    # 4. 白色内圈表盘刻度与指针
    dial_r = int(body_r * 0.72)
    ring_width = max(2, int(canvas_size * 0.016))
    draw.ellipse(
        [cx - dial_r, cy - dial_r, cx + dial_r, cy + dial_r],
        outline=(255, 255, 255, 220),
        width=ring_width,
    )

    # 12 个小刻度线
    for i in range(12):
        angle = math.radians(i * 30 - 90)
        inner_r = dial_r * (0.76 if i % 3 == 0 else 0.84)
        outer_r = dial_r * 0.93
        x1 = cx + math.cos(angle) * inner_r
        y1 = cy + math.sin(angle) * inner_r
        x2 = cx + math.cos(angle) * outer_r
        y2 = cy + math.sin(angle) * outer_r
        tick_w = max(2, int(canvas_size * (0.014 if i % 3 == 0 else 0.009)))
        draw.line([(x1, y1), (x2, y2)], fill="#FFFFFF", width=tick_w)

    # 时针与分针（约 25 分钟刻度位置，寓意专注 25 分钟）
    hand_w = max(3, int(canvas_size * 0.022))
    # 指向 12 点方向的短指针
    draw.line(
        [(cx, cy), (cx, cy - int(dial_r * 0.48))],
        fill="#FFFFFF",
        width=hand_w,
    )
    # 指向 25 分方向（150 度，相对 12 点顺时针 150 度 => 60 度数学角）
    min_angle = math.radians(150 - 90)
    mx = cx + math.cos(min_angle) * int(dial_r * 0.65)
    my = cy + math.sin(min_angle) * int(dial_r * 0.65)
    draw.line([(cx, cy), (mx, my)], fill="#FFFFFF", width=max(2, hand_w - 2))

    # 中心圆点
    dot_r = max(3, int(canvas_size * 0.028))
    draw.ellipse(
        [cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r],
        fill="#FFFFFF",
    )

    return img.resize((size, size), Image.Resampling.LANCZOS)


def ensure_app_icons(
    png_path: Path = ICON_PNG_PATH,
    ico_path: Path = ICON_ICO_PATH,
) -> tuple[Path, Path]:
    """确保专属 PNG 与多尺寸 ICO 图标文件存在，若缺失则自动生成。"""
    png_file = Path(png_path)
    ico_file = Path(ico_path)
    png_file.parent.mkdir(parents=True, exist_ok=True)
    ico_file.parent.mkdir(parents=True, exist_ok=True)

    if not png_file.exists() or not ico_file.exists():
        base_img = _draw_pomodoro_icon(256)
        if not png_file.exists():
            base_img.save(png_file, format="PNG")
        if not ico_file.exists():
            base_img.save(ico_file, format="ICO", sizes=_ICO_SIZES)

    return png_file, ico_file


def get_tray_image() -> Image.Image:
    """获取用于系统托盘的 64x64 PIL Image 对象。"""
    png_file, _ = ensure_app_icons()
    try:
        with Image.open(png_file) as img:
            return img.convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
    except Exception:
        return _draw_pomodoro_icon(64)


def set_windows_app_id(app_id: str = APP_USER_MODEL_ID) -> None:
    """在 Windows 下声明独立 AppUserModelID，避免任务栏归组到 python.exe 图标。"""
    if not sys.platform.startswith("win"):
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass


def apply_window_icon(
    window,
    ico_path: Path = ICON_ICO_PATH,
    png_path: Path = ICON_PNG_PATH,
) -> None:
    """为 Tkinter / CustomTkinter 窗口设置标题栏与 Windows 任务栏大/小图标。"""
    try:
        if not window.winfo_exists():
            return
    except Exception:
        return

    png_file, ico_file = ensure_app_icons(png_path=png_path, ico_path=ico_path)

    try:
        window.iconbitmap(default=str(ico_file))
    except Exception:
        pass

    try:
        window.iconbitmap(str(ico_file))
    except Exception:
        pass

    try:
        with Image.open(png_file) as img:
            rgba = img.convert("RGBA")
            img_256 = rgba.resize((256, 256), Image.Resampling.LANCZOS)
            img_32 = rgba.resize((32, 32), Image.Resampling.LANCZOS)
        photo_256 = ImageTk.PhotoImage(img_256, master=window)
        photo_32 = ImageTk.PhotoImage(img_32, master=window)
        window._icon_photo_refs = (photo_256, photo_32)
        window.wm_iconphoto(True, photo_256, photo_32)
    except Exception:
        pass

    if sys.platform.startswith("win"):
        _apply_win32_taskbar_icon(window, ico_file)


def _apply_win32_taskbar_icon(window, ico_file: Path) -> None:
    """通过 Win32 WM_SETICON 为窗口及其顶层父窗口句柄显式设置任务栏大/小图标。"""
    try:
        window.update_idletasks()
        hwnd = int(window.winfo_id())
        if not hwnd:
            return

        user32 = ctypes.windll.user32
        user32.GetParent.argtypes = [ctypes.c_void_p]
        user32.GetParent.restype = ctypes.c_void_p
        user32.LoadImageW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_wchar_p,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        user32.LoadImageW.restype = ctypes.c_void_p
        user32.SendMessageW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_ssize_t,
            ctypes.c_void_p,
        ]
        user32.SendMessageW.restype = ctypes.c_ssize_t

        image_icon = 1
        lr_loadfromfile = 0x0010
        wm_seticon = 0x0080
        icon_small = 0
        icon_big = 1

        hicon_big = user32.LoadImageW(None, str(ico_file), image_icon, 48, 48, lr_loadfromfile)
        hicon_small = user32.LoadImageW(None, str(ico_file), image_icon, 16, 16, lr_loadfromfile)

        targets = [hwnd]
        parent_hwnd = user32.GetParent(hwnd)
        if parent_hwnd:
            targets.append(int(parent_hwnd))

        for target_hwnd in targets:
            if hicon_big:
                user32.SendMessageW(target_hwnd, wm_seticon, icon_big, hicon_big)
            if hicon_small:
                user32.SendMessageW(target_hwnd, wm_seticon, icon_small, hicon_small)
    except Exception:
        pass
