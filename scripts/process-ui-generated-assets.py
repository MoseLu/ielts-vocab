#!/usr/bin/env python3
"""Split generated UI contact sheets into organized project assets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageFilter


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = REPO_ROOT / "frontend" / "assets" / "ui"
SOURCE_ROOT = ASSET_ROOT / "_source"
CELL_MARGIN = 4


BACKGROUND_SIZE = (1600, 900)
ICON_SIZE = (256, 256)
HUD_ICON_SIZE = (256, 256)
BADGE_SIZE = (384, 384)
STAR_SIZE = (192, 192)
CHEST_SIZE = (384, 384)
CARD_SIZE = (512, 768)
BUTTON_SIZE = (512, 192)
PANEL_SIZE = (960, 640)
REPORT_PANEL_SIZE = (1120, 720)
PARCHMENT_SIZE = (768, 240)
MEDAL_SIZE = (384, 384)


BatchItem = dict[str, object]


BATCHES: list[tuple[str, list[BatchItem]]] = [
    (
        "batch_01_background.png",
        [
            {"path": "background/map_education.png", "cell": 0, "mode": "opaque", "size": BACKGROUND_SIZE},
            {"path": "background/map_environment.png", "cell": 1, "mode": "opaque", "size": BACKGROUND_SIZE},
            {"path": "background/classroom_blur.png", "cell": 2, "mode": "opaque", "size": BACKGROUND_SIZE},
            {"path": "background/result_dim_overlay.png", "cell": 3, "mode": "overlay", "size": BACKGROUND_SIZE},
        ],
    ),
    (
        "batch_02_hud_a.png",
        [
            {"path": "hud/avatar_frame.png", "cell": 0, "mode": "alpha", "size": (512, 512)},
            {"path": "hud/resource_pill.png", "cell": 1, "mode": "alpha", "size": (640, 180)},
            {"path": "hud/icon_energy.png", "cell": 2, "mode": "alpha", "size": HUD_ICON_SIZE},
            {"path": "hud/icon_coin.png", "cell": 3, "mode": "alpha", "size": HUD_ICON_SIZE},
        ],
    ),
    (
        "batch_03_hud_map.png",
        [
            {"path": "hud/icon_gem.png", "cell": 0, "mode": "alpha", "size": HUD_ICON_SIZE},
            {"path": "hud/icon_mail.png", "cell": 1, "mode": "alpha", "size": HUD_ICON_SIZE},
            {"path": "map/level_badge_blue.png", "cell": 2, "mode": "alpha", "size": BADGE_SIZE},
            {"path": "map/level_badge_gray.png", "cell": 3, "mode": "alpha", "size": BADGE_SIZE},
        ],
    ),
    (
        "batch_04_map_badges_stars.png",
        [
            {"path": "map/level_badge_gold.png", "cell": 0, "mode": "alpha", "size": BADGE_SIZE},
            {"path": "map/level_badge_locked.png", "cell": 1, "mode": "alpha", "size": BADGE_SIZE},
            {"path": "map/star_full.png", "cell": 2, "mode": "alpha", "size": STAR_SIZE},
            {"path": "map/star_empty.png", "cell": 3, "mode": "alpha", "size": STAR_SIZE},
        ],
    ),
    (
        "batch_05_map_treasure.png",
        [
            {"path": "map/treasure_closed.png", "cell": 0, "mode": "alpha", "size": CHEST_SIZE},
            {"path": "map/treasure_open.png", "cell": 1, "mode": "alpha", "size": CHEST_SIZE},
            {"path": "map/node_current.png", "cell": 2, "mode": "alpha", "size": BADGE_SIZE},
            {"path": "map/node_boss.png", "cell": 3, "mode": "alpha", "size": BADGE_SIZE},
        ],
    ),
    (
        "batch_06_cards_a.png",
        [
            {"path": "cards/card_language_use.png", "cell": 0, "mode": "alpha", "size": CARD_SIZE},
            {"path": "cards/card_listening.png", "cell": 1, "mode": "alpha", "size": CARD_SIZE},
            {"path": "cards/card_reading.png", "cell": 2, "mode": "alpha", "size": CARD_SIZE},
            {"path": "cards/card_speaking.png", "cell": 3, "mode": "alpha", "size": CARD_SIZE},
        ],
    ),
    (
        "batch_07_card_buttons_a.png",
        [
            {"path": "cards/card_writing.png", "cell": 0, "mode": "alpha", "size": CARD_SIZE},
            {"path": "buttons/btn_green.png", "cell": 1, "mode": "alpha", "size": BUTTON_SIZE},
            {"path": "buttons/btn_blue.png", "cell": 2, "mode": "alpha", "size": BUTTON_SIZE},
            {"path": "buttons/btn_purple.png", "cell": 3, "mode": "alpha", "size": BUTTON_SIZE},
        ],
    ),
    (
        "batch_08_buttons_b.png",
        [
            {"path": "buttons/btn_gold.png", "cell": 0, "mode": "alpha", "size": BUTTON_SIZE},
            {"path": "buttons/btn_red.png", "cell": 1, "mode": "alpha", "size": BUTTON_SIZE},
            {"path": "buttons/btn_disabled.png", "cell": 2, "mode": "alpha", "size": BUTTON_SIZE},
            {"path": "buttons/btn_focus_glow.png", "cell": 3, "mode": "alpha", "size": BUTTON_SIZE},
        ],
    ),
    (
        "batch_09_modal.png",
        [
            {"path": "modal/panel_result.png", "cell": 0, "mode": "alpha", "size": PANEL_SIZE},
            {"path": "modal/panel_report.png", "cell": 1, "mode": "alpha", "size": REPORT_PANEL_SIZE},
            {"path": "modal/parchment_title.png", "cell": 2, "mode": "alpha", "size": PARCHMENT_SIZE},
            {"path": "modal/golden_medal.png", "cell": 3, "mode": "alpha", "size": MEDAL_SIZE},
        ],
    ),
    (
        "batch_10_icons_a.png",
        [
            {"path": "icons/icon_abc.png", "cell": 0, "mode": "alpha", "size": ICON_SIZE},
            {"path": "icons/icon_sound.png", "cell": 1, "mode": "alpha", "size": ICON_SIZE},
            {"path": "icons/icon_book.png", "cell": 2, "mode": "alpha", "size": ICON_SIZE},
            {"path": "icons/icon_microphone.png", "cell": 3, "mode": "alpha", "size": ICON_SIZE},
        ],
    ),
    (
        "batch_11_icons_b.png",
        [
            {"path": "icons/icon_pen.png", "cell": 0, "mode": "alpha", "size": ICON_SIZE},
            {"path": "icons/icon_bag.png", "cell": 1, "mode": "alpha", "size": ICON_SIZE},
            {"path": "icons/icon_task.png", "cell": 2, "mode": "alpha", "size": ICON_SIZE},
            {"path": "icons/icon_achievement.png", "cell": 3, "mode": "alpha", "size": ICON_SIZE},
        ],
    ),
    (
        "batch_12_icons_c.png",
        [
            {"path": "icons/icon_shop.png", "cell": 0, "mode": "alpha", "size": ICON_SIZE},
            {"path": "icons/icon_rank.png", "cell": 1, "mode": "alpha", "size": ICON_SIZE},
            {"path": "icons/icon_setting.png", "cell": 2, "mode": "alpha", "size": ICON_SIZE},
            {"path": "icons/icon_back.png", "cell": 3, "mode": "alpha", "size": ICON_SIZE},
        ],
    ),
]


def cell_box(image: Image.Image, index: int) -> tuple[int, int, int, int]:
    width, height = image.size
    cell_width = width // 2
    cell_height = height // 2
    col = index % 2
    row = index // 2
    left = col * cell_width + CELL_MARGIN
    top = row * cell_height + CELL_MARGIN
    right = (col + 1) * cell_width - CELL_MARGIN
    bottom = (row + 1) * cell_height - CELL_MARGIN
    return left, top, right, bottom


def edge_samples(image: Image.Image) -> Iterable[tuple[int, int, int]]:
    width, height = image.size
    pixels = image.convert("RGB").load()
    band = min(12, width // 8, height // 8)
    for x in range(width):
        for y in range(band):
            yield pixels[x, y]
            yield pixels[x, height - 1 - y]
    for y in range(height):
        for x in range(band):
            yield pixels[x, y]
            yield pixels[width - 1 - x, y]


def median_key(image: Image.Image) -> tuple[int, int, int]:
    samples = list(edge_samples(image))
    channels = zip(*samples)
    return tuple(sorted(channel)[len(samples) // 2] for channel in channels)  # type: ignore[return-value]


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def key_alpha(rgb: tuple[int, int, int], key: tuple[int, int, int]) -> int:
    red, green, blue = rgb
    kr, kg, kb = key
    distance = max(abs(red - kr), abs(green - kg), abs(blue - kb))
    is_green = kg > kr + 35 and kg > kb + 35
    is_magenta = kr > kg + 35 and kb > kg + 35

    if is_green:
        dominance = green - max(red, blue)
        if distance <= 54 or (dominance > 34 and green > 100):
            return 0
        if distance <= 138 and dominance > 12:
            return int(255 * smoothstep((distance - 54) / 84))
        return 255

    if is_magenta:
        dominance = min(red, blue) - green
        if distance <= 70 or (dominance > 42 and min(red, blue) > 130):
            return 0
        if distance <= 160 and dominance > 18:
            return int(255 * smoothstep((distance - 70) / 90))
        return 255

    return 0 if distance <= 40 else 255


def remove_key(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    key = median_key(rgba)
    pixels = rgba.load()
    width, height = rgba.size
    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = pixels[x, y]
            new_alpha = min(alpha, key_alpha((red, green, blue), key))
            if new_alpha < 8:
                pixels[x, y] = (0, 0, 0, 0)
            else:
                pixels[x, y] = (red, green, blue, new_alpha)

    alpha = rgba.getchannel("A").filter(ImageFilter.GaussianBlur(0.35))
    rgba.putalpha(alpha)
    return rgba


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A")
    box = alpha.point(lambda value: 255 if value > 8 else 0).getbbox()
    if box is None:
        return (0, 0, image.width, image.height)
    left, top, right, bottom = box
    pad = 8
    return (
        max(0, left - pad),
        max(0, top - pad),
        min(image.width, right + pad),
        min(image.height, bottom + pad),
    )


def fit_transparent(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    cropped = image.crop(alpha_bbox(image))
    target_width, target_height = size
    max_width = int(target_width * 0.9)
    max_height = int(target_height * 0.9)
    scale = min(max_width / cropped.width, max_height / cropped.height)
    new_size = (max(1, round(cropped.width * scale)), max(1, round(cropped.height * scale)))
    resized = cropped.resize(new_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    offset = ((target_width - new_size[0]) // 2, (target_height - new_size[1]) // 2)
    canvas.alpha_composite(resized, offset)
    return canvas


def cover_resize(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_width, target_height = size
    scale = max(target_width / image.width, target_height / image.height)
    new_size = (round(image.width * scale), round(image.height * scale))
    resized = image.convert("RGB").resize(new_size, Image.Resampling.LANCZOS)
    left = (new_size[0] - target_width) // 2
    top = (new_size[1] - target_height) // 2
    return resized.crop((left, top, left + target_width, top + target_height))


def write_markdown(entries: list[dict[str, object]]) -> None:
    lines = [
        "# UI Asset Generation Batches",
        "",
        "Generated for the IELTS five-dimension adventure UI.",
        "",
        "Final assets live under `frontend/assets/ui/`. Source contact sheets are kept in `_source/`.",
        "",
        "| Path | Size | Mode | Source |",
        "| --- | ---: | --- | --- |",
    ]
    for entry in entries:
        lines.append(
            f"| `{entry['path']}` | {entry['width']}x{entry['height']} | "
            f"{entry['mode']} | `{entry['source']}` cell {entry['cell']} |"
        )
    (ASSET_ROOT / "docs" / "asset-batches.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    entries: list[dict[str, object]] = []
    for source_name, items in BATCHES:
        source_path = SOURCE_ROOT / source_name
        with Image.open(source_path) as sheet:
            for item in items:
                relative_path = str(item["path"])
                mode = str(item["mode"])
                size = tuple(item["size"])  # type: ignore[arg-type]
                cell = int(item["cell"])
                cell_image = sheet.crop(cell_box(sheet, cell))
                if mode == "alpha":
                    output = fit_transparent(remove_key(cell_image), size)
                elif mode == "overlay":
                    opaque = cover_resize(cell_image, size).convert("RGBA")
                    opaque.putalpha(210)
                    output = opaque
                else:
                    output = cover_resize(cell_image, size)

                out_path = ASSET_ROOT / relative_path
                out_path.parent.mkdir(parents=True, exist_ok=True)
                output.save(out_path)
                entries.append(
                    {
                        "path": relative_path,
                        "width": size[0],
                        "height": size[1],
                        "mode": mode,
                        "source": f"_source/{source_name}",
                        "cell": cell,
                    }
                )

    manifest = {
        "version": "ielts-five-dimension-ui-v1",
        "generatedFrom": "gpt-to-image contact sheets",
        "assetRoot": "frontend/assets/ui",
        "assetCount": len(entries),
        "assets": entries,
    }
    (ASSET_ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=True, separators=(",", ":")) + "\n")
    write_markdown(entries)
    print(f"processed {len(entries)} assets")


if __name__ == "__main__":
    main()
