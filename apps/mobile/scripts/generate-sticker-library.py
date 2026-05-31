#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / 'src' / 'assets' / 'stickers'
HF_DIR = ROOT / 'hyperframes' / 'sticker-library'
HF_ASSET_DIR = HF_DIR / 'assets'
BASE_CAT_SOURCE = ROOT / 'src' / 'assets' / 'agreement-cat-sticker.png'

INK = '#5A3A26'
PAPER = '#FFF8ED'
CREAM = '#FFFDFC'
GREEN = '#8BBE52'
GREEN_SOFT = '#DDF2AE'
PINK = '#F7CAD6'
PINK_SOFT = '#FFE8EF'
ORANGE = '#FF9F43'
ORANGE_SOFT = '#FFE5C4'
BLUE_SOFT = '#D9F1EA'
BLUE = '#4F9FB1'
RED = '#F36B6B'
PURPLE = '#8D7BF2'


def canvas(size: int) -> Image.Image:
    return Image.new('RGBA', (size, size), (0, 0, 0, 0))


def draw_line(draw: ImageDraw.ImageDraw, points, fill=INK, width=9):
    draw.line(points, fill=fill, width=width, joint='curve')


def ellipse(draw, box, fill, outline=INK, width=8):
    draw.ellipse(box, fill=fill, outline=outline, width=width)


def rounded(draw, box, radius, fill, outline=INK, width=8):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def polygon(draw, points, fill, outline=INK, width=8):
    draw.polygon(points, fill=fill)
    draw.line(points + [points[0]], fill=outline, width=width, joint='curve')


def shadow(img: Image.Image, offset=(0, 16), blur=18, alpha=46) -> Image.Image:
    source = img.split()[-1]
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
    layer = Image.new('RGBA', img.size, (90, 58, 38, alpha))
    sh.alpha_composite(layer, offset)
    sh.putalpha(source.filter(ImageFilter.GaussianBlur(blur)))
    out = Image.new('RGBA', img.size, (0, 0, 0, 0))
    out.alpha_composite(sh)
    out.alpha_composite(img)
    return out


def save(name: str, img: Image.Image, size: int = 360):
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    HF_ASSET_DIR.mkdir(parents=True, exist_ok=True)
    art = img.copy()
    art.thumbnail((size, size), Image.Resampling.LANCZOS)
    framed = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    framed.alpha_composite(art, ((size - art.width) // 2, (size - art.height) // 2))
    framed.save(ASSET_DIR / name)
    framed.save(HF_ASSET_DIR / name)


def trim_alpha(img: Image.Image, padding: int = 24) -> Image.Image:
    box = img.getchannel('A').getbbox()
    if not box:
        return img
    x0, y0, x1, y1 = box
    x0 = max(0, x0 - padding)
    y0 = max(0, y0 - padding)
    x1 = min(img.width, x1 + padding)
    y1 = min(img.height, y1 + padding)
    return img.crop((x0, y0, x1, y1))


def clean_tutor_cat_source() -> Image.Image:
    cat = Image.open(BASE_CAT_SOURCE).convert('RGBA')
    mask = Image.new('L', cat.size, 0)
    md = ImageDraw.Draw(mask)
    md.polygon([(316, 78), (424, 120), (316, 166)], fill=255)
    md.line([(317, 78), (300, 304)], fill=255, width=18)
    md.ellipse((306, 68, 330, 92), fill=255)
    md.ellipse((286, 212, 340, 274), fill=255)
    md.polygon([(292, 250), (326, 252), (316, 316), (278, 306)], fill=255)
    softened = mask.filter(ImageFilter.GaussianBlur(1.5))
    alpha = cat.getchannel('A')
    alpha = Image.composite(Image.new('L', cat.size, 0), alpha, softened)
    cat.putalpha(alpha)
    return trim_alpha(cat, padding=16)


def wobble_points(box, count=80, wobble=7):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
    points = []
    for i in range(count):
        t = math.tau * i / count
        jitter = math.sin(t * 3.1) * wobble + math.sin(t * 7.3) * wobble * 0.45
        points.append((cx + math.cos(t) * (rx + jitter), cy + math.sin(t) * (ry + jitter)))
    return points


def soft_blob(draw: ImageDraw.ImageDraw, box, fill, outline=INK, width=10, wobble=7):
    points = wobble_points(box, wobble=wobble)
    draw.polygon(points, fill=fill)
    draw.line(points + [points[0]], fill=outline, width=width, joint='curve')


def soft_poly(draw: ImageDraw.ImageDraw, points, fill, outline=INK, width=10):
    draw.polygon(points, fill=fill)
    draw.line(points + [points[0]], fill=outline, width=width, joint='curve')


def cat_stroke(draw: ImageDraw.ImageDraw, points, fill=INK, width=8):
    draw.line(points, fill=fill, width=width, joint='curve')
    if width >= 7:
        draw.line([(x + 1, y - 1) for x, y in points], fill=(255, 255, 255, 58), width=max(1, width // 5))


def paper_grain(img: Image.Image, alpha=20):
    noise = Image.effect_noise(img.size, 42).convert('L')
    noise = noise.point(lambda value: 0 if value < 120 else min(alpha, (value - 118) // 4))
    layer = Image.new('RGBA', img.size, (255, 255, 255, 0))
    layer.putalpha(noise)
    layer.putalpha(Image.composite(layer.getchannel('A'), Image.new('L', img.size, 0), img.getchannel('A')))
    img.alpha_composite(layer)


def cat_book(draw: ImageDraw.ImageDraw, x0=242, y0=505, x1=478, y1=630):
    rounded(draw, (x0, y0, x1, y1), 24, '#FFFDF8', outline=INK, width=8)
    draw.polygon([(x0 + 12, y0 + 12), ((x0 + x1) // 2, y0 + 36), ((x0 + x1) // 2, y1 - 12), (x0 + 14, y1 - 28)], fill='#FFF7E7')
    draw.polygon([(x1 - 12, y0 + 12), ((x0 + x1) // 2, y0 + 36), ((x0 + x1) // 2, y1 - 12), (x1 - 14, y1 - 28)], fill='#FFFFFF')
    cat_stroke(draw, [((x0 + x1) // 2, y0 + 34), ((x0 + x1) // 2, y1 - 16)], fill='#D79D55', width=5)
    for y in [y0 + 48, y0 + 76]:
        cat_stroke(draw, [(x0 + 36, y), (x0 + 95, y - 6)], fill='#CDB389', width=4)
        cat_stroke(draw, [(x1 - 98, y - 4), (x1 - 34, y + 4)], fill='#CDB389', width=4)


def cat_pose(name: str, mood='idle', prop='book'):
    img = canvas(720)
    cat = clean_tutor_cat_source()
    cat.thumbnail((560, 535), Image.Resampling.LANCZOS)
    img.alpha_composite(cat, ((720 - cat.width) // 2, 82))
    d = ImageDraw.Draw(img, 'RGBA')
    if prop == 'book':
        cat_book(d, 205, 422, 500, 558)
    if prop == 'headset':
        d.arc((168, 88, 552, 390), 205, 335, fill='#64B6C8', width=18)
        rounded(d, (122, 250, 202, 378), 26, '#E0F6FF', outline='#64B6C8', width=8)
        rounded(d, (518, 250, 598, 378), 26, '#E0F6FF', outline='#64B6C8', width=8)
        cat_stroke(d, [(560, 360), (596, 420), (632, 412)], fill='#64B6C8', width=8)
    if prop == 'mic':
        rounded(d, (455, 405, 528, 528), 34, PINK_SOFT, outline='#C96A86', width=8)
        for x in [478, 492, 506]:
            cat_stroke(d, [(x, 430), (x, 500)], fill='#ECA2B6', width=4)
        cat_stroke(d, [(491, 528), (491, 625)], width=8)
        cat_stroke(d, [(440, 628), (542, 628)], width=8)
    if mood == 'worried':
        d.arc((492, 122, 580, 210), 180, 330, fill='#57A7C2', width=9)
        d.line((568, 205, 582, 232), fill='#57A7C2', width=9)
        rounded(d, (104, 426, 244, 540), 26, '#FFF2A8', outline='#D9A84E', width=7)
        cat_stroke(d, [(132, 466), (212, 466)], fill='#C6943E', width=6)
        d.arc((150, 492, 206, 535), 190, 350, fill=RED, width=6)
    if mood == 'celebrate':
        for x, y, color in [(112, 120, ORANGE), (586, 150, GREEN), (128, 508, PINK), (584, 482, BLUE)]:
            soft_poly(d, [(x, y), (x + 34, y + 12), (x + 8, y + 42)], color, outline=(255, 255, 255, 180), width=4)
        d.arc((96, 96, 198, 196), 205, 345, fill=ORANGE, width=8)
    paper_grain(img, alpha=8)
    save(name, trim_alpha(shadow(img, offset=(0, 8), blur=10, alpha=18), padding=26))


def card_stack(name: str):
    img = canvas(720); d = ImageDraw.Draw(img)
    for i, color in enumerate([PINK_SOFT, BLUE_SOFT, PAPER]):
        x, y = 170 + i * 38, 170 + i * 44
        rounded(d, (x, y, x + 310, y + 210), 34, color, width=9)
        draw_line(d, [(x + 48, y + 70), (x + 242, y + 70)], fill='#C9B087', width=7)
        draw_line(d, [(x + 48, y + 118), (x + 214, y + 118)], fill='#C9B087', width=7)
    save(name, shadow(img))


def ielts_paper(name: str):
    img = canvas(720); d = ImageDraw.Draw(img)
    rounded(d, (170, 105, 530, 615), 30, '#FFFFFF', width=9)
    rounded(d, (215, 155, 505, 218), 20, BLUE_SOFT, outline=BLUE, width=6)
    for y in [278, 340, 402, 464]:
        draw_line(d, [(225, y), (470, y)], fill='#C9B087', width=8)
        d.ellipse((188, y - 10, 210, y + 12), fill=ORANGE)
    draw_line(d, [(400, 540), (475, 580)], fill=GREEN, width=16)
    draw_line(d, [(466, 580), (510, 500)], fill=GREEN, width=16)
    save(name, shadow(img))


def simple_object(name: str, kind: str):
    img = canvas(720); d = ImageDraw.Draw(img)
    if kind == 'headset':
        d.arc((155, 140, 565, 590), 195, 345, fill=INK, width=24)
        rounded(d, (130, 340, 235, 535), 38, BLUE_SOFT, outline=BLUE, width=10)
        rounded(d, (485, 340, 590, 535), 38, BLUE_SOFT, outline=BLUE, width=10)
        draw_line(d, [(520, 520), (565, 575), (610, 565)], fill=BLUE, width=12)
    elif kind == 'mic':
        rounded(d, (275, 120, 445, 400), 84, PINK_SOFT, width=12)
        for x in [315, 360, 405]:
            draw_line(d, [(x, 170), (x, 350)], fill='#F58CAC', width=6)
        d.arc((210, 280, 510, 520), 20, 160, fill=INK, width=14)
        draw_line(d, [(360, 520), (360, 620)], width=14)
        draw_line(d, [(270, 625), (450, 625)], width=14)
    elif kind == 'sticky':
        rounded(d, (165, 150, 535, 535), 36, '#FFF2A8', width=10)
        polygon(d, [(418, 150), (535, 150), (535, 270)], '#FFE07A', width=8)
        for y in [260, 330, 400]:
            draw_line(d, [(230, y), (450, y)], fill='#C9A75F', width=8)
        d.arc((285, 455, 435, 535), 190, 350, fill=RED, width=12)
    elif kind == 'clock':
        ellipse(d, (170, 150, 550, 530), PAPER, width=12)
        draw_line(d, [(360, 340), (360, 235)], width=12)
        draw_line(d, [(360, 340), (440, 390)], width=12)
        polygon(d, [(210, 118), (260, 64), (310, 135)], PINK_SOFT, width=8)
        polygon(d, [(410, 135), (460, 64), (510, 118)], PINK_SOFT, width=8)
    elif kind == 'letter':
        rounded(d, (135, 210, 585, 505), 42, PINK_SOFT, width=12)
        draw_line(d, [(150, 245), (360, 382), (570, 245)], width=10)
        polygon(d, [(360, 305), (405, 250), (465, 285), (360, 390), (255, 285), (315, 250)], RED, outline=RED, width=1)
    elif kind == 'chest':
        rounded(d, (155, 275, 565, 555), 40, ORANGE_SOFT, width=12)
        rounded(d, (185, 170, 535, 345), 42, '#FFD66E', width=12)
        rounded(d, (315, 310, 405, 420), 18, '#FFFFFF', width=8)
        draw_line(d, [(360, 352), (360, 392)], fill=ORANGE, width=10)
    elif kind == 'leaf':
        for angle, color in [(-25, GREEN_SOFT), (0, '#CDEB90'), (24, '#BCE36B')]:
            leaf = canvas(720); ld = ImageDraw.Draw(leaf)
            polygon(ld, [(360, 150), (470, 315), (360, 570), (245, 315)], color, outline='#5F793A', width=9)
            draw_line(ld, [(360, 170), (360, 555)], fill='#5F793A', width=7)
            img.alpha_composite(leaf.rotate(angle, center=(360, 360), resample=Image.Resampling.BICUBIC))
    elif kind == 'flower':
        for a in range(0, 360, 60):
            cx = 360 + math.cos(math.radians(a)) * 88
            cy = 340 + math.sin(math.radians(a)) * 88
            ellipse(d, (cx - 62, cy - 52, cx + 62, cy + 52), PINK_SOFT, width=8)
        ellipse(d, (308, 288, 412, 392), '#FFD89E', width=8)
    elif kind == 'citrus':
        ellipse(d, (160, 160, 560, 560), '#FFF2A8', width=12)
        ellipse(d, (205, 205, 515, 515), '#FFE07A', outline=ORANGE, width=8)
        for a in range(0, 360, 45):
            draw_line(d, [(360, 360), (360 + math.cos(math.radians(a)) * 145, 360 + math.sin(math.radians(a)) * 145)], fill=ORANGE, width=5)
        polygon(d, [(410, 160), (520, 90), (565, 185)], GREEN_SOFT, outline='#5F793A', width=8)
    elif kind == 'pin':
        rounded(d, (250, 165, 470, 360), 32, PINK_SOFT, width=10)
        d.ellipse((315, 95, 405, 185), fill=RED, outline=INK, width=8)
        draw_line(d, [(360, 360), (360, 610)], width=10)
        polygon(d, [(332, 610), (388, 610), (360, 660)], INK, outline=INK, width=1)
    save(name, shadow(img))


def study_window(name: str):
    img = canvas(720); d = ImageDraw.Draw(img)
    rounded(d, (105, 150, 615, 500), 52, '#FFFFFF', width=12)
    rounded(d, (145, 195, 345, 455), 34, BLUE_SOFT, outline='#A5C9BE', width=7)
    rounded(d, (375, 195, 575, 455), 34, BLUE_SOFT, outline='#A5C9BE', width=7)
    draw_line(d, [(360, 180), (360, 485)], width=10)
    ellipse(d, (252, 445, 468, 600), PINK_SOFT, outline=None, width=0)
    save(name, shadow(img))


def desk_mat(name: str):
    img = Image.new('RGBA', (960, 540), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    rounded(d, (40, 110, 920, 430), 80, PINK, outline='#E8B3C3', width=10)
    for y in [185, 265, 345]:
        draw_line(d, [(125, y), (835, y)], fill=(255, 255, 255, 160), width=5)
    img.save(ASSET_DIR / name)
    img.save(HF_ASSET_DIR / name)


def scroll_note(name: str):
    img = canvas(720); d = ImageDraw.Draw(img)
    rounded(d, (120, 215, 600, 505), 28, PAPER, outline='#E8B45F', width=9)
    rounded(d, (85, 190, 150, 530), 30, '#FFD89E', outline='#E8B45F', width=8)
    rounded(d, (570, 190, 635, 530), 30, '#FFD89E', outline='#E8B45F', width=8)
    for y in [285, 350, 415]:
        draw_line(d, [(195, y), (520, y)], fill='#C9B087', width=8)
    save(name, shadow(img))


def make_contact_sheet():
    files = sorted([p for p in ASSET_DIR.glob('*.png') if p.name in TARGETS])
    cell = 220
    cols = 5
    rows = math.ceil(len(files) / cols)
    sheet = Image.new('RGBA', (cols * cell, rows * cell), '#FFFDFC')
    d = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for i, path in enumerate(files):
        x, y = (i % cols) * cell, (i // cols) * cell
        d.rounded_rectangle((x + 10, y + 10, x + cell - 10, y + cell - 10), 18, fill='#FFFFFF', outline='#E3EED5', width=2)
        art = Image.open(path).convert('RGBA')
        art.thumbnail((154, 154), Image.Resampling.LANCZOS)
        sheet.alpha_composite(art, (x + (cell - art.width) // 2, y + 22))
        d.text((x + 18, y + 184), path.stem, fill=INK, font=font)
    sheet.save(HF_DIR / 'contact-sheet.png')


def paste_fit(dst: Image.Image, src_path: Path, box: tuple[int, int, int, int]):
    src = Image.open(src_path).convert('RGBA')
    src.thumbnail((box[2] - box[0], box[3] - box[1]), Image.Resampling.LANCZOS)
    x = box[0] + (box[2] - box[0] - src.width) // 2
    y = box[1] + (box[3] - box[1] - src.height) // 2
    dst.alpha_composite(src, (x, y))


def make_login_preview():
    img = Image.new('RGBA', (1080, 1440), '#F5F9E2')
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((70, 555, 1010, 1220), 56, fill='#FFFFFF', outline='#DCEBCF', width=4)
    paste_fit(img, ASSET_DIR / 'leaf-sprig.png', (105, 415, 285, 615))
    paste_fit(img, ASSET_DIR / 'cat-agreement.png', (665, 325, 900, 585))
    paste_fit(img, ASSET_DIR / 'tape-pin.png', (865, 540, 990, 675))
    d.text((210, 710), 'Agreement Sheet Preview', fill=INK, font=ImageFont.load_default())
    d.rounded_rectangle((150, 930, 930, 1105), 88, fill='#D8ED9E', outline='#A9C86E', width=6)
    d.text((470, 1000), 'Continue', fill=INK, font=ImageFont.load_default())
    paste_fit(img, ASSET_DIR / 'citrus-corner.png', (755, 850, 925, 1015))
    img.save(HF_DIR / 'login-agreement-preview.png')


TARGETS = {
    'cat-tutor-idle.png', 'cat-tutor-reading.png', 'cat-tutor-listening.png',
    'cat-tutor-speaking.png', 'cat-tutor-worried.png', 'cat-tutor-celebrate.png',
    'cat-agreement.png', 'cat-companion.png', 'vocab-card-stack.png', 'ielts-paper.png', 'headset.png',
    'recording-mic.png', 'wrong-word-sticky.png', 'review-clock.png',
    'ai-letter.png', 'treasure-chest.png', 'study-window.png', 'desk-mat.png',
    'scroll-note.png', 'leaf-sprig.png', 'flower-small.png', 'citrus-corner.png',
    'tape-pin.png',
}


def main():
    cat_pose('cat-tutor-idle.png', 'idle', 'none')
    cat_pose('cat-tutor-reading.png', 'idle', 'book')
    cat_pose('cat-tutor-listening.png', 'idle', 'headset')
    cat_pose('cat-tutor-speaking.png', 'idle', 'mic')
    cat_pose('cat-tutor-worried.png', 'worried', 'none')
    cat_pose('cat-tutor-celebrate.png', 'celebrate', 'none')
    cat_pose('cat-agreement.png', 'idle', 'none')
    cat_pose('cat-companion.png', 'idle', 'none')
    card_stack('vocab-card-stack.png')
    ielts_paper('ielts-paper.png')
    simple_object('headset.png', 'headset')
    simple_object('recording-mic.png', 'mic')
    simple_object('wrong-word-sticky.png', 'sticky')
    simple_object('review-clock.png', 'clock')
    simple_object('ai-letter.png', 'letter')
    simple_object('treasure-chest.png', 'chest')
    study_window('study-window.png')
    desk_mat('desk-mat.png')
    scroll_note('scroll-note.png')
    simple_object('leaf-sprig.png', 'leaf')
    simple_object('flower-small.png', 'flower')
    simple_object('citrus-corner.png', 'citrus')
    simple_object('tape-pin.png', 'pin')
    make_contact_sheet()
    make_login_preview()


if __name__ == '__main__':
    main()
