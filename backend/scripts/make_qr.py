"""Render a scannable QR card for a URL.

    python backend/scripts/make_qr.py https://example.trycloudflare.com [out.png]

Generated locally on purpose: the demo URL is a temporary door into this
machine, and sending it to an online QR service would hand it to a third
party. Defaults to ~/Documents/pomidorai-qr/pomidorai-qr.png.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont
from qrcode.constants import ERROR_CORRECT_H

DEFAULT_OUT = Path.home() / "Documents" / "pomidorai-qr" / "pomidorai-qr.png"


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    suffix = "-Bold" if bold else ""
    for path in (
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{suffix}.ttf",
        f"/usr/share/fonts/TTF/DejaVuSans{suffix}.ttf",
    ):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render(url: str, out: Path) -> Path:
    # Highest error correction: survives a phone held at an angle, poor
    # lighting, or a printout with a crease through it.
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=14, border=3)
    qr.add_data(url)
    qr.make(fit=True)
    code = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    width = code.width
    card = Image.new("RGB", (width, code.height + 170), "white")
    card.paste(code, (0, 0))
    draw = ImageDraw.Draw(card)

    def centre(text: str, y: int, font: ImageFont.ImageFont, fill: str = "black") -> None:
        text_width = draw.textbbox((0, 0), text, font=font)[2]
        draw.text(((width - text_width) / 2, y), text, font=font, fill=fill)

    centre("PomidorAI", code.height + 8, _font(46, bold=True))
    centre("Telefon kamerasi bilan skanerlang", code.height + 66, _font(22), "#444444")
    centre(url.replace("https://", ""), code.height + 104, _font(17), "#777777")

    out.parent.mkdir(parents=True, exist_ok=True)
    card.save(out)
    (out.parent / "URL.txt").write_text(url + "\n")
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    url = sys.argv[1].strip()
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    print(f"QR saved to {render(url, out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
