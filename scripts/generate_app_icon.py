from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = ROOT / "resources" / "branding"
PNG_PATH = RESOURCE_DIR / "tax_converter_l1.png"
ICO_PATH = RESOURCE_DIR / "tax_converter_l1.ico"


def generate() -> tuple[Path, Path]:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError(
            "Pillow diperlukan untuk membuat icon aplikasi. "
            "Install dengan: python -m pip install pillow"
        ) from exc

    RESOURCE_DIR.mkdir(parents=True, exist_ok=True)

    size = 512
    image = Image.new("RGBA", (size, size), (15, 48, 76, 255))
    draw = ImageDraw.Draw(image)

    # Border dan panel mengikuti identitas visual sidebar aplikasi.
    margin = 34
    draw.rounded_rectangle(
        (margin, margin, size - margin, size - margin),
        radius=88,
        fill=(18, 57, 89, 255),
        outline=(47, 107, 236, 255),
        width=18,
    )

    # Simbol dokumen/lembar kerja.
    paper = (122, 108, 390, 410)
    draw.rounded_rectangle(
        paper,
        radius=28,
        fill=(247, 250, 252, 255),
    )
    draw.polygon(
        [(322, 108), (390, 176), (322, 176)],
        fill=(207, 222, 240, 255),
    )

    # Garis tabel sederhana.
    for y in (220, 260, 300):
        draw.rounded_rectangle(
            (160, y, 352, y + 14),
            radius=7,
            fill=(47, 107, 236, 255),
        )

    # Badge L-1.
    badge = (205, 326, 430, 448)
    draw.rounded_rectangle(
        badge,
        radius=34,
        fill=(20, 184, 84, 255),
        outline=(15, 48, 76, 255),
        width=10,
    )

    try:
        font = ImageFont.truetype("arialbd.ttf", 74)
    except OSError:
        font = ImageFont.load_default()

    text = "L-1"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    cx = (badge[0] + badge[2]) / 2
    cy = (badge[1] + badge[3]) / 2
    draw.text(
        (cx - tw / 2, cy - th / 2 - bbox[1]),
        text,
        font=font,
        fill=(255, 255, 255, 255),
    )

    image.save(PNG_PATH, format="PNG")
    image.save(
        ICO_PATH,
        format="ICO",
        sizes=[
            (16, 16),
            (24, 24),
            (32, 32),
            (48, 48),
            (64, 64),
            (128, 128),
            (256, 256),
        ],
    )
    return PNG_PATH, ICO_PATH


if __name__ == "__main__":
    png, ico = generate()
    print(f"PNG: {png}")
    print(f"ICO: {ico}")
