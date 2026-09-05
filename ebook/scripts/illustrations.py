# -*- coding: utf-8 -*-
"""Generación procedural de ilustraciones atmosféricas (estilo grabado/aguafuerte
vintage) para EL FARO DE LOS AHOGADOS, usando solo PIL + numpy."""

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
import math, random, os

# En el repositorio, este script vive en ebook/scripts/ y las imágenes en
# ebook/assets/ (carpeta hermana). Si se ejecuta suelto (todo en un mismo
# directorio, como en desarrollo), usa "assets" junto al propio script.
_here = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(_here) == "scripts":
    ASSETS = os.path.join(os.path.dirname(_here), "assets")
else:
    ASSETS = os.path.join(_here, "assets")
os.makedirs(ASSETS, exist_ok=True)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
FONT_ITALIC = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"

random.seed(11)
np.random.seed(11)

# ---------------------------------------------------------------- utilidades

def lerp(a, b, t):
    return a + (b - a) * t

def lerp_color(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))

def vertical_gradient(size, top_color, bottom_color, mid_color=None, mid_pos=0.5):
    w, h = size
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        if mid_color is not None:
            if t < mid_pos:
                col = lerp_color(top_color, mid_color, t / max(mid_pos, 1e-6))
            else:
                col = lerp_color(mid_color, bottom_color, (t - mid_pos) / max(1 - mid_pos, 1e-6))
        else:
            col = lerp_color(top_color, bottom_color, t)
        grad.putpixel((0, y), col)
    return grad.resize((w, h))

def add_grain(img, amount=10, seed=0):
    arr = np.array(img).astype(np.int16)
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, amount, arr.shape[:2])
    noise = np.repeat(noise[:, :, None], 3, axis=2)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGB")

def add_vignette(img, strength=0.55, feather=1.15):
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w / 2.0, h / 2.0
    d = np.sqrt(((xx - cx) / (w * 0.72)) ** 2 + ((yy - cy) / (h * 0.72)) ** 2)
    mask = np.clip(1.0 - strength * np.clip(d - (2 - feather), 0, None) ** 1.6, 0, 1)
    arr = np.array(img).astype(np.float32)
    arr *= mask[:, :, None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")

def paper_texture(size, base=(238, 229, 209), seed=0):
    """Textura de papel envejecido a partir de ruido suavizado."""
    w, h = size
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 1, (h // 3, w // 3))
    img = Image.fromarray(((noise - noise.min()) / (np.ptp(noise) + 1e-6) * 255).astype(np.uint8))
    img = img.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(2))
    arr = np.array(img).astype(np.float32) / 255.0
    canvas = np.zeros((h, w, 3), dtype=np.float32)
    for i in range(3):
        canvas[:, :, i] = base[i] + (arr - 0.5) * 22
    return Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8), "RGB")

def moon(size, center, radius, glow_color=(250, 244, 222), core_boost=25):
    """Devuelve una capa RGBA con una luna y su halo, para pegar con alpha_composite."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = center
    for r, a in [(radius * 4.2, 14), (radius * 3.1, 22), (radius * 2.2, 40), (radius * 1.5, 90)]:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=glow_color + (a,))
    layer = layer.filter(ImageFilter.GaussianBlur(radius * 0.35))
    d2 = ImageDraw.Draw(layer)
    core = tuple(min(255, c + core_boost) for c in glow_color)
    d2.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=core + (235,))
    # sombreado sutil en un borde de la luna (terminador), para dar volumen
    # esférico sin caer en manchas que se lean como rasgos de una cara.
    shade_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade_layer)
    shade_off = radius * 0.62
    sd.ellipse([cx - radius + shade_off, cy - radius, cx + radius + shade_off, cy + radius],
               fill=(8, 8, 14, 130))
    shade_layer = shade_layer.filter(ImageFilter.GaussianBlur(radius * 0.28))
    mask = Image.new("L", size, 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=255)
    layer = Image.composite(Image.alpha_composite(layer, shade_layer), layer, mask)
    return layer

def choppy_waterline(width, base_y, amplitude, n=140, seed=0, roughness=1.0):
    rng = np.random.default_rng(seed)
    xs = np.linspace(0, width, n)
    y = np.zeros(n)
    freqs = [ (0.004, 1.0), (0.012, 0.5), (0.035, 0.25 * roughness), (0.09, 0.12 * roughness) ]
    phases = rng.uniform(0, 2 * math.pi, len(freqs))
    for (f, amp), ph in zip(freqs, phases):
        y += np.sin(xs * f * 2 * math.pi + ph) * amp
    y = base_y + y * amplitude
    return list(zip(xs.tolist(), y.tolist()))

def draw_water(draw, size, base_y, top_color, bottom_color, seed=0, roughness=1.0, rows=26):
    w, h = size
    for i in range(rows):
        t = i / (rows - 1)
        y = base_y + (h - base_y) * (t ** 1.35)
        col = lerp_color(top_color, bottom_color, t)
        amp = 3 + 22 * t * roughness
        pts = choppy_waterline(w, y, amp, n=90, seed=seed + i, roughness=roughness)
        pts = [(0, h)] + pts + [(w, h)]
        draw.polygon(pts, fill=col)

def add_fog_layers(img, bands, seed=0):
    """Superpone bandas de niebla horizontales, translúcidas y difuminadas,
    a distintas alturas, para dar profundidad atmosférica a una escena.
    `bands` es una lista de (y_frac, thickness_frac, alpha)."""
    W, H = img.size
    rng = np.random.default_rng(seed)
    fog = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fog)
    for y_frac, th_frac, alpha in bands:
        cy = H * y_frac
        th = H * th_frac
        n = 6
        for i in range(n):
            cx = W * (i + 0.5) / n + rng.uniform(-W * 0.04, W * 0.04)
            rw = W / n * rng.uniform(0.9, 1.5)
            rh = th * rng.uniform(0.7, 1.3)
            fd.ellipse([cx - rw, cy - rh / 2, cx + rw, cy + rh / 2], fill=(225, 225, 230, alpha))
    fog = fog.filter(ImageFilter.GaussianBlur(min(W, H) * 0.02))
    img_rgba = img.convert("RGBA")
    img_rgba.alpha_composite(fog)
    return img_rgba.convert("RGB")


def add_water_glints(img, waterline, moon_center, count=10, seed=0):
    """Pequeños destellos especulares horizontales bajo la luna, sobre el agua."""
    W, H = img.size
    rng = np.random.default_rng(seed)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    mx, my = moon_center
    for i in range(count):
        t = i / max(1, count - 1)
        y = waterline + t * (H - waterline) * 0.85
        spread = 20 + t * 90
        x = mx + rng.uniform(-spread, spread)
        w = rng.uniform(14, 60) * (1 - t * 0.4)
        alpha = int(lerp(120, 25, t))
        ld.ellipse([x - w, y - 2, x + w, y + 2], fill=(235, 232, 214, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(2))
    img_rgba = img.convert("RGBA")
    img_rgba.alpha_composite(layer)
    return img_rgba.convert("RGB")


def hatched_silhouette(img, polygon_or_draw_fn, bbox, density=0.35, angle=35, color=(20, 16, 14), seed=0):
    """Rellena una máscara con trama de líneas finas (efecto grabado) en vez de negro sólido."""
    pass  # (no usado directamente; el detalle de trama se aplica con líneas explícitas donde hace falta)

def wrap_text_letterspaced(text, spacing=" "):
    return spacing.join(list(text))

def draw_lighthouse(draw, base_x, base_y, height, band=True, color=(15, 13, 14), light_on=True, beam_dir=1):
    """Dibuja un faro estilizado (torre + linterna + base) en silueta, con una
    franja de luz lateral que sugiere volumen cilíndrico en vez de un plano liso."""
    tower_top_w = height * 0.11
    tower_bot_w = height * 0.19
    top_y = base_y - height
    lantern_h = height * 0.14
    body_top = top_y + lantern_h
    # cuerpo de la torre (trapecio)
    draw.polygon([
        (base_x - tower_bot_w, base_y),
        (base_x + tower_bot_w, base_y),
        (base_x + tower_top_w, body_top),
        (base_x - tower_top_w, body_top),
    ], fill=color)
    # franja de luz rasante en el borde derecho (sugiere volumen cilíndrico)
    rim = tuple(min(255, c + 34) for c in color)
    draw.polygon([
        (base_x + tower_bot_w * 0.62, base_y),
        (base_x + tower_bot_w * 0.86, base_y),
        (base_x + tower_top_w * 0.86, body_top),
        (base_x + tower_top_w * 0.62, body_top),
    ], fill=rim)
    # sombra leve en el borde izquierdo, para reforzar el contraste de volumen
    shade = tuple(max(0, c - 6) for c in color)
    draw.polygon([
        (base_x - tower_bot_w, base_y),
        (base_x - tower_bot_w * 0.78, base_y),
        (base_x - tower_top_w * 0.78, body_top),
        (base_x - tower_top_w, body_top),
    ], fill=shade)
    # linterna (cabina)
    lant_w = tower_top_w * 1.35
    draw.rectangle([base_x - lant_w, body_top - lantern_h, base_x + lant_w, body_top], fill=color)
    # techo cónico
    draw.polygon([
        (base_x - lant_w * 1.15, body_top - lantern_h),
        (base_x + lant_w * 1.15, body_top - lantern_h),
        (base_x, body_top - lantern_h - height * 0.09),
    ], fill=color)
    # base ensanchada
    draw.polygon([
        (base_x - tower_bot_w * 1.5, base_y + height * 0.05),
        (base_x + tower_bot_w * 1.5, base_y + height * 0.05),
        (base_x + tower_bot_w * 1.05, base_y),
        (base_x - tower_bot_w * 1.05, base_y),
    ], fill=color)
    return (base_x, body_top - lantern_h / 2)


def add_light_beam(layer, origin, angle_deg, length, spread_deg, color=(255, 248, 214), alpha=95):
    draw = ImageDraw.Draw(layer, "RGBA")
    ox, oy = origin
    a0 = math.radians(angle_deg - spread_deg / 2)
    a1 = math.radians(angle_deg + spread_deg / 2)
    p1 = (ox + math.cos(a0) * length, oy + math.sin(a0) * length)
    p2 = (ox + math.cos(a1) * length, oy + math.sin(a1) * length)
    draw.polygon([origin, p1, p2], fill=color + (alpha,))
    return layer


def crosshatch(draw, bbox, spacing=6, angle=45, color=(20, 16, 14, 60), width=1):
    x0, y0, x1, y1 = bbox
    diag = int(math.hypot(x1 - x0, y1 - y0)) + spacing * 2
    rad = math.radians(angle)
    dx, dy = math.cos(rad), math.sin(rad)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    n = int(diag / spacing)
    for i in range(-n, n):
        offset = i * spacing
        px, py = cx - dy * offset, cy + dx * offset
        x_a = px - dx * diag / 2
        y_a = py - dy * diag / 2
        x_b = px + dx * diag / 2
        y_b = py + dy * diag / 2
        draw.line([(x_a, y_a), (x_b, y_b)], fill=color, width=width)


def bird(draw, x, y, s, color=(15, 13, 14)):
    draw.arc([x - s, y - s * 0.6, x, y + s * 0.6], start=200, end=340, fill=color, width=max(1, int(s * 0.12)))
    draw.arc([x, y - s * 0.6, x + s, y + s * 0.6], start=200, end=340, fill=color, width=max(1, int(s * 0.12)))


def figure_silhouette(draw, x, y, h, pose="standing", color=(12, 10, 10)):
    """Silueta humana simple, de pie, para escenas atmosféricas."""
    head_r = h * 0.075
    neck_y = y - h + head_r * 2.1
    draw.ellipse([x - head_r, y - h, x + head_r, y - h + head_r * 2], fill=color)
    shoulder_w = head_r * 1.55
    hip_w = head_r * 1.05
    torso_bottom = y - h * (0.42 if pose == "kneeling" else 0.5)
    # torso (ligeramente cónico, mas natural que un trapecio ancho)
    draw.polygon([
        (x - shoulder_w, neck_y),
        (x + shoulder_w, neck_y),
        (x + hip_w, torso_bottom),
        (x - hip_w, torso_bottom),
    ], fill=color)
    leg_w = max(2, int(hip_w * 0.42))
    if pose == "kneeling":
        # piernas dobladas: muslo hacia atrás, espinilla hacia el suelo
        draw.polygon([(x - hip_w, torso_bottom), (x, torso_bottom), (x + hip_w * 0.3, y), (x - hip_w * 1.1, y)], fill=color)
    else:
        stride = h * 0.02 if pose == "standing" else h * 0.05
        draw.line([(x - hip_w * 0.55, torso_bottom), (x - hip_w * 0.55 - stride, y)], fill=color, width=leg_w)
        draw.line([(x + hip_w * 0.55, torso_bottom), (x + hip_w * 0.55 + stride, y)], fill=color, width=leg_w)
    arm_w = max(2, int(leg_w * 0.85))
    if pose == "reaching":
        draw.line([(x + shoulder_w * 0.8, neck_y + head_r), (x + h * 0.30, neck_y - h * 0.10)], fill=color, width=arm_w)
        draw.line([(x - shoulder_w * 0.8, neck_y + head_r), (x - hip_w, torso_bottom)], fill=color, width=arm_w)
    else:
        draw.line([(x - shoulder_w * 0.8, neck_y + head_r), (x - shoulder_w * 0.55, torso_bottom)], fill=color, width=arm_w)
        draw.line([(x + shoulder_w * 0.8, neck_y + head_r), (x + shoulder_w * 0.55, torso_bottom)], fill=color, width=arm_w)


def save(img, name):
    path = os.path.join(ASSETS, name)
    img.convert("RGB").save(path, quality=95)
    print("guardado:", path)
    return path


# ------------------------------------------------------------- ilustraciones

def gen_cover():
    W, H = 1700, 2404  # proporción A4 (210x297mm) para portada a sangre completa sin deformar
    sky_top = (18, 22, 42)
    sky_mid = (52, 46, 66)
    sky_bottom = (120, 92, 84)
    img = vertical_gradient((W, H), sky_top, sky_bottom, mid_color=sky_mid, mid_pos=0.55)

    moon_layer = moon((W, H), (W * 0.66, H * 0.40), 130, glow_color=(247, 231, 196))
    img = img.convert("RGBA")
    img.alpha_composite(moon_layer)
    img = img.convert("RGB")

    draw = ImageDraw.Draw(img, "RGBA")
    # nubes lejanas
    for _ in range(9):
        cx = random.uniform(0, W)
        cy = random.uniform(H * 0.08, H * 0.42)
        rw = random.uniform(180, 420)
        rh = rw * random.uniform(0.12, 0.22)
        draw.ellipse([cx - rw, cy - rh, cx + rw, cy + rh], fill=(20, 18, 30, 60))

    horizon = H * 0.62
    draw_water(draw, (W, H), horizon, (58, 62, 78), (10, 9, 14), seed=3, roughness=1.6, rows=30)

    # acantilado
    cliff_pts = [(0, horizon + H * 0.05)]
    for x in np.linspace(0, W * 0.62, 30):
        cliff_pts.append((x, horizon - (x / (W * 0.62)) ** 1.4 * H * 0.16))
    cliff_pts += [(W * 0.62, horizon + H * 0.3), (0, H)]
    draw.polygon(cliff_pts, fill=(8, 7, 10))

    fx, fy = W * 0.40, horizon - H * 0.155
    lh_h = H * 0.30
    origin = draw_lighthouse(draw, fx, fy, lh_h, color=(6, 5, 7))

    beam_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    add_light_beam(beam_layer, origin, angle_deg=200, length=W * 0.9, spread_deg=13, alpha=70)
    add_light_beam(beam_layer, origin, angle_deg=15, length=W * 0.75, spread_deg=11, alpha=55)
    beam_layer = beam_layer.filter(ImageFilter.GaussianBlur(6))
    img = img.convert("RGBA")
    img.alpha_composite(beam_layer)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")

    for _ in range(6):
        bird(draw, random.uniform(W * 0.05, W * 0.9), random.uniform(H * 0.12, H * 0.3), random.uniform(14, 24))

    # textura de grabado + grano + viñeta
    tex = paper_texture((W, H), base=(0, 0, 0), seed=5)
    tex_arr = (np.array(tex).astype(np.float32) - 0) / 255.0 * 10
    img_arr = np.array(img).astype(np.float32)
    img_arr = np.clip(img_arr + (tex_arr - 5), 0, 255).astype(np.uint8)
    img = Image.fromarray(img_arr, "RGB")
    img = add_vignette(img, strength=0.75, feather=1.05)
    img = add_grain(img, amount=6, seed=7)

    # ---- panel oscuro suave tras el bloque de título, para legibilidad ----
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    pd.rectangle([0, 0, W, H * 0.40], fill=(8, 7, 12, 130))
    panel = panel.filter(ImageFilter.GaussianBlur(60))
    img = img.convert("RGBA"); img.alpha_composite(panel); img = img.convert("RGB")

    # ---- tipografía de portada (con autoajuste de ancho) ----
    draw = ImageDraw.Draw(img, "RGBA")
    title_lines = ["EL FARO", "DE LOS", "AHOGADOS"]
    max_w = W * 0.88

    def fit_font(text, start_size, spacing, max_width, min_size=60):
        size = start_size
        while size > min_size:
            f = ImageFont.truetype(FONT_BOLD, size)
            spaced = wrap_text_letterspaced(text, spacing)
            bbox = draw.textbbox((0, 0), spaced, font=f)
            if bbox[2] - bbox[0] <= max_width:
                return f, spaced, bbox
            size -= 4
        f = ImageFont.truetype(FONT_BOLD, min_size)
        spaced = wrap_text_letterspaced(text, spacing)
        return f, spaced, draw.textbbox((0, 0), spaced, font=f)

    y = H * 0.075
    line_h_total = 0
    line_data = []
    for line in title_lines:
        f, spaced, bbox = fit_font(line, 150, "  ", max_w)
        line_data.append((f, spaced, bbox))
    for f, spaced, bbox in line_data:
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (W - tw) / 2
        for dx, dy_, col in [(5, 5, (0, 0, 0, 200)), (0, 0, (247, 240, 222, 255))]:
            draw.text((tx + dx, y + dy_ - bbox[1]), spaced, font=f, fill=col)
        y += th + 30

    y += 8
    rule_w = W * 0.20
    draw.line([(W / 2 - rule_w / 2, y), (W / 2 + rule_w / 2, y)], fill=(210, 190, 150, 230), width=3)
    y += 30
    f_sub2, spaced_sub, bbox = fit_font("UNA NOVELA DE TERROR Y SUSPENSO", 34, " ", max_w, min_size=20)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) / 2, y - bbox[1]), spaced_sub, font=f_sub2, fill=(226, 214, 190, 235))

    author = "TITO"
    f_author = ImageFont.truetype(FONT_BOLD, 58)
    spaced_a = wrap_text_letterspaced(author, "   ")
    bbox = draw.textbbox((0, 0), spaced_a, font=f_author)
    tw = bbox[2] - bbox[0]
    ay = H * 0.90
    draw.line([(W / 2 - 60, ay - 18), (W / 2 + 60, ay - 18)], fill=(210, 190, 150, 200), width=2)
    draw.text(((W - tw) / 2, ay), spaced_a, font=f_author, fill=(247, 240, 222, 255))

    return save(img, "cover.jpg")


def gen_ch1_boat():
    """La barca acercándose al faro, al atardecer."""
    W, H = 1800, 1150
    img = vertical_gradient((W, H), (30, 27, 46), (168, 108, 78), mid_color=(96, 63, 70), mid_pos=0.5)
    draw = ImageDraw.Draw(img, "RGBA")
    sun_layer = moon((W, H), (W * 0.72, H * 0.38), 95, glow_color=(255, 214, 160))
    img = img.convert("RGBA"); img.alpha_composite(sun_layer); img = img.convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")
    horizon = H * 0.55
    draw_water(draw, (W, H), horizon, (110, 70, 66), (18, 15, 22), seed=9, roughness=1.1, rows=24)

    islet_x = W * 0.68
    draw.polygon([(islet_x - 140, horizon + 40), (islet_x + 40, horizon - 90), (islet_x + 210, horizon + 55)], fill=(10, 8, 10))
    draw_lighthouse(draw, islet_x, horizon - 85, H * 0.22, color=(8, 7, 8))

    # barca en primer plano
    bx, by = W * 0.28, H * 0.86
    draw.polygon([(bx - 130, by), (bx + 140, by), (bx + 95, by + 34), (bx - 90, by + 34)], fill=(6, 5, 7))
    draw.line([(bx - 10, by), (bx - 10, by - 90)], fill=(6, 5, 7), width=6)
    draw.polygon([(bx - 6, by - 88), (bx - 6, by - 30), (bx + 70, by - 20)], fill=(15, 13, 16, 210))
    figure_silhouette(draw, bx + 30, by - 2, 78, color=(4, 3, 4))

    for _ in range(4):
        bird(draw, random.uniform(W * 0.1, W * 0.5), random.uniform(H * 0.15, H * 0.35), random.uniform(16, 26))

    img = add_water_glints(img, horizon, (W * 0.72, H * 0.38), count=9, seed=12)
    img = add_fog_layers(img, [(0.5, 0.10, 26), (0.62, 0.08, 20)], seed=4)
    img = add_vignette(img, strength=0.5)
    img = add_grain(img, amount=7, seed=2)
    return save(img, "ch1_barca.jpg")


def gen_ch3_bell():
    """La campana de bronce entre las rocas."""
    W, H = 1800, 1150
    img = vertical_gradient((W, H), (10, 12, 22), (34, 38, 46), mid_color=(18, 20, 30), mid_pos=0.4)
    draw = ImageDraw.Draw(img, "RGBA")
    m = moon((W, H), (W * 0.22, H * 0.18), 80, glow_color=(230, 232, 224))
    img = img.convert("RGBA"); img.alpha_composite(m); img = img.convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")

    waterline = H * 0.62
    draw_water(draw, (W, H), waterline, (40, 46, 52), (8, 9, 13), seed=15, roughness=0.6, rows=20)

    for i in range(7):
        rx = W * (0.15 + i * 0.11) + random.uniform(-30, 30)
        ry = waterline + random.uniform(-10, 60)
        rs = random.uniform(60, 140)
        draw.ellipse([rx - rs, ry - rs * 0.5, rx + rs, ry + rs * 0.5], fill=(6, 6, 8))

    # campana de bronce: perfil curvo (hombro redondeado + falda acampanada), no un cono recto
    cx, cy = W * 0.52, waterline - 30
    bw, bh = 190, 220
    bronze = (58, 78, 66)
    bronze_dark = (32, 46, 40)
    top_y = cy - bh * 0.60
    profile_r = [0.10, 0.16, 0.24, 0.34, 0.46, 0.60, 0.78, 0.98]
    n = len(profile_r)
    left_pts, right_pts = [], []
    for i, r in enumerate(profile_r):
        t = i / (n - 1)
        y = top_y + t * bh * 0.78
        x = bw * 0.5 * r
        left_pts.append((cx - x, y))
        right_pts.append((cx + x, y))
    draw.polygon(left_pts + right_pts[::-1], fill=bronze)
    # falda inferior (elipse) y boca de la campana
    skirt_y = top_y + bh * 0.78
    draw.ellipse([cx - bw * 0.5, skirt_y - bh * 0.05, cx + bw * 0.5, skirt_y + bh * 0.09], fill=bronze_dark)
    draw.ellipse([cx - bw * 0.5, skirt_y - bh * 0.09, cx + bw * 0.5, skirt_y + bh * 0.05], fill=bronze)
    # asa superior
    draw.rectangle([cx - bw * 0.05, top_y - bh * 0.12, cx + bw * 0.05, top_y + bh * 0.02], fill=bronze_dark)
    draw.ellipse([cx - bw * 0.08, top_y - bh * 0.18, cx + bw * 0.08, top_y - bh * 0.02], outline=bronze_dark, width=8)
    # badajo colgando dentro
    draw.line([(cx, top_y + bh * 0.1), (cx, skirt_y - 6)], fill=bronze_dark, width=5)
    draw.ellipse([cx - 13, skirt_y - 20, cx + 13, skirt_y + 6], fill=bronze_dark)
    # brillo sutil (una franja vertical más clara) para sugerir volumen curvo
    highlight = tuple(min(255, c + 26) for c in bronze)
    draw.line([(cx - bw * 0.22, top_y + bh * 0.05), (cx - bw * 0.30, skirt_y - bh * 0.08)], fill=highlight, width=6)

    reflect = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(reflect)
    rd.ellipse([cx - bw * 0.4, waterline, cx + bw * 0.4, waterline + 120], fill=(60, 80, 70, 70))
    reflect = reflect.filter(ImageFilter.GaussianBlur(14))
    img = img.convert("RGBA"); img.alpha_composite(reflect); img = img.convert("RGB")

    img = add_fog_layers(img, [(0.58, 0.09, 22)], seed=17)
    img = add_vignette(img, strength=0.6)
    img = add_grain(img, amount=8, seed=21)
    return save(img, "ch3_campana.jpg")


def gen_ch5_hand():
    """Una mano emergiendo del agua junto a las rocas, bajo la luna."""
    W, H = 1800, 1150
    img = vertical_gradient((W, H), (6, 8, 18), (20, 24, 34))
    draw = ImageDraw.Draw(img, "RGBA")
    m = moon((W, H), (W * 0.78, H * 0.2), 100, glow_color=(232, 236, 226))
    img = img.convert("RGBA"); img.alpha_composite(m); img = img.convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")

    waterline = H * 0.45
    draw_water(draw, (W, H), waterline, (26, 32, 38), (5, 6, 10), seed=44, roughness=1.8, rows=30)

    # mano emergiendo
    hx, hy = W * 0.46, H * 0.72
    wrist_w = 46
    draw.polygon([(hx - wrist_w, hy + 160), (hx + wrist_w, hy + 160), (hx + wrist_w * 0.7, hy), (hx - wrist_w * 0.7, hy)], fill=(4, 4, 6))
    finger_specs = [(-34, -170, 16), (-10, -205, 15), (14, -200, 15), (36, -165, 14), (-52, -120, 15)]
    for fx, fy, fw in finger_specs:
        x0, y0 = hx + fx, hy + fy
        draw.line([(hx + fx * 0.4, hy - 10), (x0, y0)], fill=(4, 4, 6), width=fw)
        draw.ellipse([x0 - fw / 2, y0 - fw / 2, x0 + fw / 2, y0 + fw / 2], fill=(4, 4, 6))
    draw.ellipse([hx - wrist_w * 0.8, hy - 40, hx + wrist_w * 0.8, hy + 40], fill=(4, 4, 6))

    ripple = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ripple)
    for i, r in enumerate([40, 80, 130, 190]):
        rd.ellipse([hx - r, hy + 150 - r * 0.3, hx + r, hy + 150 + r * 0.3], outline=(180, 190, 200, 90 - i * 18), width=3)
    img = img.convert("RGBA"); img.alpha_composite(ripple); img = img.convert("RGB")

    for i in range(5):
        rx = W * (0.05 + i * 0.05)
        ry = waterline + random.uniform(10, 40)
        rs = random.uniform(40, 90)
        d2 = ImageDraw.Draw(img)
        d2.ellipse([rx - rs, ry - rs * 0.4, rx + rs, ry + rs * 0.4], fill=(4, 4, 6))

    img = add_water_glints(img, waterline, (W * 0.78, H * 0.2), count=8, seed=34)
    img = add_vignette(img, strength=0.68)
    img = add_grain(img, amount=9, seed=33)
    return save(img, "ch5_mano.jpg")


def gen_ch7_storm():
    """Tormenta imposible: siluetas entre las olas, bajo el haz del faro."""
    W, H = 1800, 1150
    img = vertical_gradient((W, H), (5, 6, 14), (26, 22, 30), mid_color=(12, 12, 20), mid_pos=0.45)
    draw = ImageDraw.Draw(img, "RGBA")

    horizon = H * 0.5
    draw_water(draw, (W, H), horizon, (30, 34, 42), (4, 4, 8), seed=71, roughness=2.6, rows=34)

    lx, ly = W * 0.14, horizon - 60
    origin = draw_lighthouse(draw, lx, ly, H * 0.42, color=(5, 4, 6))
    beam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    add_light_beam(beam, origin, angle_deg=18, length=W * 1.1, spread_deg=20, alpha=60)
    beam = beam.filter(ImageFilter.GaussianBlur(10))
    img = img.convert("RGBA"); img.alpha_composite(beam); img = img.convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")

    silhouettes = [(0.32, "standing"), (0.42, "reaching"), (0.55, "standing"), (0.66, "kneeling"), (0.78, "reaching"), (0.88, "standing")]
    for fx, pose in silhouettes:
        x = W * fx + random.uniform(-20, 20)
        y = horizon + random.uniform(30, 90)
        h = random.uniform(190, 260)
        rim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        rd = ImageDraw.Draw(rim)
        figure_silhouette(rd, x + 4, y + 2, h, pose=pose, color=(210, 220, 235, 110))
        rim = rim.filter(ImageFilter.GaussianBlur(4))
        img_rgba = img.convert("RGBA"); img_rgba.alpha_composite(rim); img = img_rgba.convert("RGB")
        draw = ImageDraw.Draw(img, "RGBA")
        figure_silhouette(draw, x, y, h, pose=pose, color=(2, 2, 4))

    for _ in range(60):
        x0 = random.uniform(0, W)
        y0 = random.uniform(0, horizon)
        ln = random.uniform(30, 90)
        ang = random.uniform(1.3, 1.7)
        x1 = x0 + math.cos(ang) * ln
        y1 = y0 + math.sin(ang) * ln
        draw.line([(x0, y0), (x1, y1)], fill=(180, 185, 200, 30), width=2)

    img = add_fog_layers(img, [(0.48, 0.12, 24), (0.6, 0.08, 18)], seed=62)
    img = add_vignette(img, strength=0.7)
    img = add_grain(img, amount=11, seed=61)
    return save(img, "ch7_tormenta.jpg")


def gen_ch9_stairs():
    """Escalera de caracol de piedra vista de perfil, con luz cayendo desde la trampilla."""
    W, H = 1150, 1500
    img = vertical_gradient((W, H), (10, 9, 14), (26, 21, 24))
    draw = ImageDraw.Draw(img, "RGBA")

    # muro curvo de la torre a la izquierda, para dar sensación de encierro
    draw.polygon([(0, 0), (W * 0.30, 0), (W * 0.12, H), (0, H)], fill=(5, 4, 6))

    axis_x = W * 0.66  # eje vertical de la escalera (columna central)
    top_y = H * 0.10
    bottom_y = H * 1.02
    n_steps = 16
    step_reach = W * 0.40

    # columna central de piedra
    draw.polygon([(axis_x - 16, top_y - 10), (axis_x + 16, top_y - 10), (axis_x + 10, bottom_y), (axis_x - 10, bottom_y)], fill=(24, 20, 20))

    peldanos = []
    for i in range(n_steps):
        t = i / (n_steps - 1)
        y = lerp(bottom_y, top_y, t)
        reach = lerp(step_reach, step_reach * 0.22, t)
        side = 1 if i % 2 == 0 else -1
        depth_shade = int(lerp(96, 34, t))
        col = (depth_shade + 10, depth_shade, depth_shade - 4)
        thickness = lerp(30, 10, t)
        x_far = axis_x + side * reach
        peldanos.append((axis_x, y, x_far, side))
        # cada peldaño: un trapecio de piedra que sale de la columna
        draw.polygon([
            (axis_x, y - thickness * 0.5),
            (x_far, y - thickness * 0.32),
            (x_far, y + thickness * 0.32),
            (axis_x, y + thickness * 0.5),
        ], fill=col)
        # borde superior más claro (arista iluminada desde arriba)
        edge_light = tuple(min(255, c + 30) for c in col)
        draw.line([(axis_x, y - thickness * 0.5), (x_far, y - thickness * 0.32)], fill=edge_light, width=2)
        # baranda de hierro
        rail_top = y - lerp(64, 18, t)
        draw.line([(x_far, y), (x_far, rail_top)], fill=(8, 7, 8), width=max(2, int(lerp(7, 2, t))))
        if i > 0:
            px, py, pfar, pside = peldanos[i - 1]
            prail_top = py - lerp(64, 18, (i - 1) / (n_steps - 1))
            draw.line([(pfar, prail_top), (x_far, rail_top)], fill=(8, 7, 8), width=2)

    # haz de luz cayendo desde la trampilla abierta arriba
    light = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(light)
    ld.polygon([(axis_x - 210, top_y - 60), (axis_x + 210, top_y - 60), (axis_x + 55, H * 0.62), (axis_x - 55, H * 0.62)], fill=(255, 238, 196, 75))
    light = light.filter(ImageFilter.GaussianBlur(34))
    img = img.convert("RGBA"); img.alpha_composite(light); img = img.convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")
    draw.ellipse([axis_x - 42, top_y - 46, axis_x + 42, top_y + 38], fill=(255, 246, 214, 240))
    draw.rectangle([axis_x - 70, top_y - 50, axis_x + 70, top_y - 12], outline=(20, 17, 16, 220), width=6)

    # silueta subiendo, a contraluz, con un leve borde iluminado (rim light)
    fx, fy, fh = axis_x - W * 0.12, H * 0.62, H * 0.22
    rim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rim)
    figure_silhouette(rd, fx + 6, fy + 3, fh, pose="standing", color=(255, 240, 205, 130))
    rim = rim.filter(ImageFilter.GaussianBlur(5))
    img = img.convert("RGBA"); img.alpha_composite(rim); img = img.convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")
    figure_silhouette(draw, fx, fy, fh, pose="standing", color=(3, 3, 4))

    img = add_vignette(img, strength=0.6)
    img = add_grain(img, amount=9, seed=91)
    return save(img, "ch9_escalera.jpg")


def gen_epilogue_footprints():
    """Huellas en la orilla, alejándose hacia el agua, al amanecer."""
    W, H = 1800, 1000
    img = vertical_gradient((W, H), (60, 52, 66), (214, 172, 132), mid_color=(150, 108, 96), mid_pos=0.55)
    draw = ImageDraw.Draw(img, "RGBA")
    horizon = H * 0.42
    draw_water(draw, (W, H), horizon, (150, 118, 104), (30, 26, 34), seed=101, roughness=0.9, rows=16)

    # playa
    draw.rectangle([0, horizon + H * 0.02, W, H], fill=(70, 56, 52))
    sand = paper_texture((W, int(H * 0.6)), base=(70, 56, 52), seed=8)
    img.paste(sand, (0, int(horizon + H * 0.02)))
    draw = ImageDraw.Draw(img, "RGBA")

    lx, ly = W * 0.14, horizon - 30
    draw_lighthouse(draw, lx, ly, H * 0.34, color=(20, 15, 16))

    start = (W * 0.62, H * 0.94)
    end = (W * 0.5, horizon + 10)
    n = 9
    for i in range(n):
        t = i / (n - 1)
        px = lerp(start[0], end[0], t) + (10 if i % 2 == 0 else -10)
        py = lerp(start[1], end[1], t)
        s = lerp(26, 10, t)
        draw.ellipse([px - s * 0.4, py - s, px + s * 0.4, py + s], fill=(35, 27, 25, 200))

    for _ in range(4):
        bird(draw, random.uniform(W * 0.5, W * 0.95), random.uniform(H * 0.1, H * 0.3), random.uniform(14, 22), color=(30, 24, 22))

    img = add_fog_layers(img, [(0.44, 0.08, 20)], seed=45)
    img = add_vignette(img, strength=0.5)
    img = add_grain(img, amount=7, seed=44)
    return save(img, "epilogo_huellas.jpg")


def gen_ch6_pueblo():
    """Cala Yunque al atardecer: la iglesia en la ladera, ventanas encendidas."""
    W, H = 1800, 1150
    img = vertical_gradient((W, H), (24, 20, 38), (150, 96, 84), mid_color=(88, 58, 66), mid_pos=0.55)
    draw = ImageDraw.Draw(img, "RGBA")
    m = moon((W, H), (W * 0.16, H * 0.2), 78, glow_color=(247, 231, 196))
    img = img.convert("RGBA"); img.alpha_composite(m); img = img.convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")

    horizon = H * 0.62
    draw_water(draw, (W, H), horizon, (120, 92, 84), (18, 15, 20), seed=53, roughness=0.5, rows=14)

    # ladera con el pueblo escalonado
    hill_pts = [(0, H)]
    for x in np.linspace(0, W, 40):
        hill_pts.append((x, horizon - (x / W) * H * 0.30 + math.sin(x * 0.01) * 10))
    hill_pts += [(W, H)]
    draw.polygon(hill_pts, fill=(14, 11, 14))

    # casas: bloques pequeños escalonados con ventanas encendidas
    rng = random.Random(77)
    for i in range(22):
        t = rng.uniform(0.05, 0.95)
        hx = t * W
        hy = horizon - t * H * 0.30 + math.sin(hx * 0.01) * 10 + rng.uniform(2, 14)
        hw = rng.uniform(28, 60)
        hh = rng.uniform(26, 50)
        draw.rectangle([hx - hw / 2, hy - hh, hx + hw / 2, hy], fill=(10, 9, 11))
        if rng.random() < 0.7:
            draw.rectangle([hx - hw * 0.18, hy - hh * 0.62, hx + hw * 0.05, hy - hh * 0.30],
                            fill=(255, 200, 120, 230))

    # iglesia en lo alto
    cx = W * 0.30
    cy = horizon - (cx / W) * H * 0.30 + math.sin(cx * 0.01) * 10 + 6
    draw.polygon([(cx - 46, cy + 90), (cx + 46, cy + 90), (cx + 46, cy - 10), (cx, cy - 70), (cx - 46, cy - 10)],
                 fill=(8, 7, 9))
    draw.rectangle([cx - 12, cy - 130, cx + 12, cy - 70], fill=(8, 7, 9))
    draw.polygon([(cx - 18, cy - 130), (cx + 18, cy - 130), (cx, cy - 156)], fill=(8, 7, 9))
    draw.rectangle([cx - 4, cy - 158, cx + 4, cy - 150], fill=(8, 7, 9))
    draw.rectangle([cx - 12, cy - 100, cx + 12, cy - 80], fill=(255, 210, 140, 200))

    for _ in range(5):
        bird(draw, random.uniform(W * 0.5, W * 0.95), random.uniform(H * 0.1, H * 0.3), random.uniform(14, 24))

    img = add_fog_layers(img, [(0.63, 0.07, 22)], seed=54)
    img = add_vignette(img, strength=0.55)
    img = add_grain(img, amount=8, seed=55)
    return save(img, "ch6_pueblo.jpg")


def gen_ch10_visita():
    """La silueta espectral de Elías Roth, de pie junto al muelle, al atardecer."""
    W, H = 1800, 1150
    img = vertical_gradient((W, H), (26, 22, 34), (140, 96, 78), mid_color=(84, 58, 60), mid_pos=0.5)
    draw = ImageDraw.Draw(img, "RGBA")
    m = moon((W, H), (W * 0.82, H * 0.22), 70, glow_color=(240, 226, 196))
    img = img.convert("RGBA"); img.alpha_composite(m); img = img.convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")

    horizon = H * 0.56
    draw_water(draw, (W, H), horizon, (96, 78, 70), (14, 12, 16), seed=81, roughness=0.7, rows=20)

    lx, ly = W * 0.16, horizon - 70
    draw_lighthouse(draw, lx, ly, H * 0.28, color=(10, 8, 10))

    # muelle de piedra en primer plano
    draw.polygon([(W * 0.30, horizon + 10), (W * 0.62, horizon + 10), (W * 0.58, H), (W * 0.20, H)], fill=(12, 10, 12))

    # figura espectral de Roth: silueta translúcida con halo, no sólida
    fx, fy, fh = W * 0.44, horizon + H * 0.20, H * 0.30
    spectre = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(spectre)
    figure_silhouette(sd, fx, fy, fh, pose="standing", color=(20, 22, 24, 235))
    spectre = spectre.filter(ImageFilter.GaussianBlur(1.5))
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    figure_silhouette(hd, fx, fy, fh, pose="standing", color=(210, 225, 220, 90))
    halo = halo.filter(ImageFilter.GaussianBlur(14))
    img = img.convert("RGBA")
    img.alpha_composite(halo)
    img.alpha_composite(spectre)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")

    ripple = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ripple)
    for i, r in enumerate([30, 60, 95]):
        rd.ellipse([fx - r, fy + fh * 0.02 - r * 0.25, fx + r, fy + fh * 0.02 + r * 0.25],
                   outline=(200, 205, 210, 70 - i * 18), width=2)
    img = img.convert("RGBA"); img.alpha_composite(ripple); img = img.convert("RGB")

    img = add_fog_layers(img, [(0.56, 0.09, 26), (0.7, 0.07, 18)], seed=82)
    img = add_vignette(img, strength=0.6)
    img = add_grain(img, amount=9, seed=83)
    return save(img, "ch10_visita.jpg")


if __name__ == "__main__":
    gen_cover()
    gen_ch1_boat()
    gen_ch3_bell()
    gen_ch5_hand()
    gen_ch6_pueblo()
    gen_ch7_storm()
    gen_ch9_stairs()
    gen_ch10_visita()
    gen_epilogue_footprints()
