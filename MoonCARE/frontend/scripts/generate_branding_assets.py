from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
ANDROID_RES = ROOT / "android" / "app" / "src" / "main" / "res"
WEB_ASSETS = ROOT / "src" / "assets"

BG = "#FFF6F4"
CARD = "#FFFDFC"
ROSE = "#F48AA8"
ROSE_DARK = "#D75A7D"
CORAL = "#F7B29E"
PLUM = "#7F5A7A"
GRID = "#F1DDE5"


def rounded_shadow(base_size: int):
    shadow = Image.new("RGBA", (base_size, base_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)
    margin = int(base_size * 0.1)
    draw.rounded_rectangle(
        (margin, margin + int(base_size * 0.03), base_size - margin, base_size - margin + int(base_size * 0.03)),
        radius=int(base_size * 0.22),
        fill=(199, 126, 151, 70),
    )
    return shadow.filter(ImageFilter.GaussianBlur(radius=max(4, base_size // 80)))


def build_icon(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), BG)
    image.alpha_composite(rounded_shadow(size))

    draw = ImageDraw.Draw(image)
    margin = int(size * 0.08)
    draw.rounded_rectangle(
        (margin, margin, size - margin, size - margin),
        radius=int(size * 0.22),
        fill=CARD,
        outline="#EBCAD4",
        width=max(2, size // 110),
    )

    grid_step = max(22, size // 7)
    for offset in range(-size, size * 2, grid_step):
        draw.line((offset, margin, offset + size, size - margin), fill=GRID, width=max(1, size // 180))

    crescent_bounds = (
        int(size * 0.24),
        int(size * 0.22),
        int(size * 0.70),
        int(size * 0.68),
    )
    cutout_bounds = (
        int(size * 0.37),
        int(size * 0.18),
        int(size * 0.82),
        int(size * 0.67),
    )
    draw.ellipse(crescent_bounds, fill=ROSE)
    draw.ellipse(cutout_bounds, fill=CARD)

    petal_one = [
        (int(size * 0.63), int(size * 0.40)),
        (int(size * 0.70), int(size * 0.29)),
        (int(size * 0.77), int(size * 0.40)),
        (int(size * 0.70), int(size * 0.53)),
    ]
    petal_two = [
        (int(size * 0.60), int(size * 0.55)),
        (int(size * 0.70), int(size * 0.47)),
        (int(size * 0.79), int(size * 0.58)),
        (int(size * 0.69), int(size * 0.69)),
    ]
    draw.polygon(petal_one, fill=CORAL)
    draw.polygon(petal_two, fill=ROSE_DARK)
    draw.ellipse(
        (
            int(size * 0.64),
            int(size * 0.47),
            int(size * 0.73),
            int(size * 0.56),
        ),
        fill=PLUM,
    )

    for dot_center in ((0.30, 0.72), (0.39, 0.76), (0.49, 0.71)):
        cx = int(size * dot_center[0])
        cy = int(size * dot_center[1])
        radius = max(4, size // 45)
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill="#E7A0B4")

    return image


def build_splash(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), BG)
    draw = ImageDraw.Draw(image)
    draw.ellipse(
        (
            int(size * -0.18),
            int(size * -0.08),
            int(size * 0.55),
            int(size * 0.62),
        ),
        fill="#FFE8E6",
    )
    draw.ellipse(
        (
            int(size * 0.50),
            int(size * 0.42),
            int(size * 1.08),
            int(size * 1.04),
        ),
        fill="#FFF0E7",
    )
    icon = build_icon(int(size * 0.28))
    shadow = Image.new("RGBA", (icon.width + 80, icon.height + 80), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        (40, 56, shadow.width - 40, shadow.height - 24),
        radius=int(icon.width * 0.22),
        fill=(202, 122, 154, 55),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=max(8, size // 160)))
    center = ((size - shadow.width) // 2, (size - shadow.height) // 2)
    image.alpha_composite(shadow, center)
    image.alpha_composite(icon, ((size - icon.width) // 2, (size - icon.height) // 2))
    return image


def save(image: Image.Image, target: Path):
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target)


def main():
    icon_1024 = build_icon(1024)
    splash_2732 = build_splash(2732)

    save(icon_1024, WEB_ASSETS / "mooncare-logo.png")
    save(splash_2732, ANDROID_RES / "drawable" / "splash.png")

    launcher_sizes = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }
    splash_sizes = {
        "drawable-port-mdpi": (320, 480),
        "drawable-port-hdpi": (480, 800),
        "drawable-port-xhdpi": (720, 1280),
        "drawable-port-xxhdpi": (960, 1600),
        "drawable-port-xxxhdpi": (1280, 1920),
        "drawable-land-mdpi": (480, 320),
        "drawable-land-hdpi": (800, 480),
        "drawable-land-xhdpi": (1280, 720),
        "drawable-land-xxhdpi": (1600, 960),
        "drawable-land-xxxhdpi": (1920, 1280),
    }

    for folder, size in launcher_sizes.items():
        icon = icon_1024.resize((size, size), Image.LANCZOS)
        save(icon, ANDROID_RES / folder / "ic_launcher.png")
        save(icon, ANDROID_RES / folder / "ic_launcher_round.png")
        save(icon, ANDROID_RES / folder / "ic_launcher_foreground.png")

    for folder, (width, height) in splash_sizes.items():
        splash = splash_2732.resize((width, height), Image.LANCZOS)
        save(splash, ANDROID_RES / folder / "splash.png")


if __name__ == "__main__":
    main()
