"""Draws the Sesli logo: a blue rounded square with five voice bars; faint specks on the left fade out
(noise being removed) and clean bars remain. Outputs icon.png (512), icon.ico (multi-size), splash.png."""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BLUE = (47, 111, 228)
INK = (29, 29, 31)
S = 1024


def logo(size=S):
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, S - 1, S - 1), radius=230, fill=BLUE)
    # noise specks (left), fading
    specks = [(170, 380, 0.55), (205, 560, 0.45), (150, 470, 0.35), (230, 690, 0.3), (185, 330, 0.25), (250, 450, 0.4)]
    for x, y, a in specks:
        r = 16
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, int(255 * a)))
    # clean voice bars
    heights = [0.30, 0.56, 0.78, 0.50, 0.26]
    bw, gap = 74, 46
    x0 = 330
    for i, hgt in enumerate(heights):
        h = hgt * S
        x = x0 + i * (bw + gap)
        d.rounded_rectangle((x, S / 2 - h / 2, x + bw, S / 2 + h / 2), radius=bw / 2, fill=(255, 255, 255, 255))
    return img.resize((size, size), Image.LANCZOS) if size != S else img


def main():
    big = logo()
    big.resize((512, 512), Image.LANCZOS).save(os.path.join(HERE, 'icon.png'))
    big.save(os.path.join(HERE, 'icon.ico'), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    big.resize((64, 64), Image.LANCZOS).save(os.path.join(HERE, 'icon64.png'))
    # splash (shown while the .exe unpacks)
    w, h = 420, 150
    sp = Image.new('RGB', (w, h), (255, 255, 255))
    d = ImageDraw.Draw(sp)
    d.rectangle((0, 0, w - 1, h - 1), outline=(220, 218, 213))
    sp.paste(big.resize((86, 86), Image.LANCZOS), (32, 32), big.resize((86, 86), Image.LANCZOS))
    try:
        f1 = ImageFont.truetype('C:/Windows/Fonts/seguisb.ttf', 40)
        f2 = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 16)
    except OSError:
        f1 = f2 = ImageFont.load_default()
    d.text((140, 36), 'Sesli', font=f1, fill=INK)
    d.text((142, 92), 'Starting\u2026  \u00b7  Başlıyor\u2026', font=f2, fill=(107, 107, 112))
    sp.save(os.path.join(HERE, 'splash.png'))


if __name__ == '__main__':
    main()
