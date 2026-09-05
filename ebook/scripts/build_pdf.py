# -*- coding: utf-8 -*-
"""Maquetación editorial de EL FARO DE LOS AHOGADOS: portada ilustrada,
prefacio, introducción, índice con numeración automática, cuerpo a dos
columnas con cabecera/pie alternantes, ilustraciones y epílogo."""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, NextPageTemplate, FrameBreak,
    Paragraph, Spacer, Image, PageBreak, HRFlowable,
    KeepTogether,
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfbase.pdfmetrics import stringWidth
from PIL import Image as PILImage

import content as C

BASE = os.path.dirname(os.path.abspath(__file__))
# En el repositorio este script vive en ebook/scripts/, con assets/ y
# output/ como carpetas hermanas; si se ejecuta suelto (todo en un mismo
# directorio, como en desarrollo), usa esas carpetas junto al script.
ROOT = os.path.dirname(BASE) if os.path.basename(BASE) == "scripts" else BASE
ASSETS = os.path.join(ROOT, "assets")
OUT_DIR = os.path.join(ROOT, "output")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PDF = os.path.join(OUT_DIR, "El_Faro_de_los_Ahogados.pdf")

# ------------------------------------------------------------------ layout

PAGE_W, PAGE_H = A4
MARGIN = 21 * mm
TOP_MARGIN = 24 * mm
BOTTOM_MARGIN = 22 * mm
COL_GAP = 9 * mm

CONTENT_W = PAGE_W - 2 * MARGIN
COL_W = (CONTENT_W - COL_GAP) / 2.0
FRAME_H = PAGE_H - TOP_MARGIN - BOTTOM_MARGIN

INK = colors.HexColor("#231f1c")
INK_SOFT = colors.HexColor("#4a433c")
RULE = colors.HexColor("#b8a988")
FAINT = colors.HexColor("#8d8172")
PAPER_TINT = colors.HexColor("#fbf9f3")

CHAPTER_WORDS = ["UNO", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE", "DIEZ", "ONCE"]

CHAPTER_IMAGES = {
    1: ("ch1_barca.jpg", "Punta Escarza, vista desde la barca de Onofre."),
    3: ("ch3_campana.jpg", "La campana hallada entre las rocas del sur."),
    5: ("ch5_mano.jpg", "Algo se movía junto a la campana, bajo el agua."),
    6: ("ch6_pueblo.jpg", "Cala Yunque, al atardecer."),
    8: ("ch7_tormenta.jpg", "La noche de las doce luces."),
    10: ("ch10_visita.jpg", "Elías Roth, de pie junto al muelle."),
    11: ("ch9_escalera.jpg", "Alguien subía la escalera de caracol."),
}

# ------------------------------------------------------------------ estilos

def make_styles():
    s = {}
    s["BodyFirst"] = ParagraphStyle(
        "BodyFirst", fontName="Times-Roman", fontSize=9.6, leading=13.4,
        alignment=TA_JUSTIFY, spaceAfter=6.5, firstLineIndent=0, textColor=INK,
    )
    s["Body"] = ParagraphStyle(
        "Body", parent=s["BodyFirst"], firstLineIndent=13,
    )
    s["Epigraph"] = ParagraphStyle(
        "Epigraph", fontName="Times-Italic", fontSize=9.2, leading=13,
        alignment=TA_LEFT, textColor=INK_SOFT, spaceAfter=10, leftIndent=14,
    )
    s["ChapterLabel"] = ParagraphStyle(
        "ChapterLabel", fontName="Times-Roman", fontSize=10.2, leading=13,
        alignment=TA_CENTER, textColor=FAINT, spaceAfter=2, spaceBefore=4,
    )
    s["ChapterTitleTOC"] = ParagraphStyle(
        "ChapterTitleTOC", fontName="Times-Bold", fontSize=20, leading=24,
        alignment=TA_CENTER, textColor=INK, spaceAfter=10, spaceBefore=2,
    )
    s["Caption"] = ParagraphStyle(
        "Caption", fontName="Times-Italic", fontSize=8, leading=10.5,
        alignment=TA_CENTER, textColor=FAINT, spaceAfter=10, spaceBefore=3,
    )
    # ---- frontmatter (columna única) ----
    s["CoverTitleBig"] = ParagraphStyle(
        "CoverTitleBig", fontName="Times-Bold", fontSize=30, leading=35,
        alignment=TA_CENTER, textColor=INK, spaceAfter=6,
    )
    s["CoverSub"] = ParagraphStyle(
        "CoverSub", fontName="Times-Italic", fontSize=12.5, leading=16,
        alignment=TA_CENTER, textColor=INK_SOFT, spaceAfter=40,
    )
    s["CoverAuthor"] = ParagraphStyle(
        "CoverAuthor", fontName="Times-Bold", fontSize=15, leading=18,
        alignment=TA_CENTER, textColor=INK,
    )
    s["Legal"] = ParagraphStyle(
        "Legal", fontName="Times-Roman", fontSize=9, leading=13.5,
        alignment=TA_LEFT, textColor=INK_SOFT, spaceAfter=8,
    )
    s["Dedication"] = ParagraphStyle(
        "Dedication", fontName="Times-Italic", fontSize=13, leading=20,
        alignment=TA_CENTER, textColor=INK,
    )
    s["TOCTitle"] = ParagraphStyle(
        "TOCTitle", fontName="Times-Bold", fontSize=22, leading=26,
        alignment=TA_CENTER, textColor=INK, spaceAfter=22,
    )
    s["TOCEntry"] = ParagraphStyle(
        "TOCEntry", fontName="Times-Roman", fontSize=11.3, leading=22,
        textColor=INK,
    )
    s["AboutTitle"] = s["ChapterTitleTOC"]
    return s


STY = make_styles()


def small_caps_like(text):
    """Aproxima versalitas con mayúsculas y espaciado de letras (sin depender de fuentes OTF)."""
    return " ".join(list(text.upper()))


# --------------------------------------------------------------- documento

class BookDocTemplate(BaseDocTemplate):
    """Registra entradas de índice y el título de sección en curso
    (para las cabeceras alternantes) cada vez que se dibuja un encabezado."""

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name == "ChapterTitleTOC":
            running = getattr(flowable, "runningTitle", None) or flowable.getPlainText()
            toc_text = getattr(flowable, "tocEntryText", None) or flowable.getPlainText()
            self._curr_running_title = running
            self.notify("TOCEntry", (0, toc_text, self.page))
            key = "bm-%d" % self.page
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(toc_text, key, level=0, closed=False)


def paint_paper(canvas):
    canvas.setFillColor(PAPER_TINT)
    canvas.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)


def draw_display_furniture(canvas, doc):
    canvas.saveState()
    paint_paper(canvas)
    page_num = canvas.getPageNumber()
    footer_y = BOTTOM_MARGIN - 15
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.6)
    canvas.line(MARGIN, footer_y + 12, PAGE_W - MARGIN, footer_y + 12)
    canvas.setFont("Times-Roman", 9)
    canvas.setFillColor(INK_SOFT)
    canvas.drawCentredString(PAGE_W / 2, footer_y, str(page_num))
    canvas.restoreState()


def _twocol_furniture(canvas, doc, show_header):
    canvas.saveState()
    paint_paper(canvas)
    page_num = canvas.getPageNumber()
    is_even = (page_num % 2 == 0)
    if show_header:
        header_y = PAGE_H - TOP_MARGIN + 10
        running = getattr(doc, "_curr_running_title", C.TITULO)
        canvas.setFont("Times-Italic", 8.3)
        canvas.setFillColor(FAINT)
        if is_even:
            canvas.drawString(MARGIN, header_y, small_caps_like(C.TITULO))
        else:
            text = small_caps_like(running)
            canvas.drawRightString(PAGE_W - MARGIN, header_y, text)
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.6)
        canvas.line(MARGIN, header_y - 6, PAGE_W - MARGIN, header_y - 6)

    footer_y = BOTTOM_MARGIN - 15
    canvas.line(MARGIN, footer_y + 12, PAGE_W - MARGIN, footer_y + 12)
    canvas.setFont("Times-Roman", 9)
    canvas.setFillColor(INK_SOFT)
    canvas.drawCentredString(PAGE_W / 2, footer_y, str(page_num))
    canvas.setFont("Times-Italic", 7.3)
    canvas.setFillColor(FAINT)
    if is_even:
        canvas.drawString(MARGIN, footer_y, "Tito")
    else:
        canvas.drawRightString(PAGE_W - MARGIN, footer_y, "El faro de los ahogados")
    canvas.restoreState()


def draw_twocol_furniture(canvas, doc):
    _twocol_furniture(canvas, doc, show_header=True)


def draw_twocol_opener_furniture(canvas, doc):
    # Página de apertura de capítulo/sección: sin cabecera (el propio título
    # ya cumple esa función), siguiendo la convención editorial clásica.
    _twocol_furniture(canvas, doc, show_header=False)


def draw_cover_furniture(canvas, doc):
    pass


def build_templates(doc):
    cover_frame = Frame(0, 0, PAGE_W, PAGE_H, id="coverF",
                         leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    display_frame = Frame(MARGIN, BOTTOM_MARGIN, CONTENT_W, FRAME_H, id="dispF",
                           leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    colA = Frame(MARGIN, BOTTOM_MARGIN, COL_W, FRAME_H, id="colA",
                 leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    colB = Frame(MARGIN + COL_W + COL_GAP, BOTTOM_MARGIN, COL_W, FRAME_H, id="colB",
                 leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    colA2 = Frame(MARGIN, BOTTOM_MARGIN, COL_W, FRAME_H, id="colA2",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    colB2 = Frame(MARGIN + COL_W + COL_GAP, BOTTOM_MARGIN, COL_W, FRAME_H, id="colB2",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[cover_frame], onPage=draw_cover_furniture),
        PageTemplate(id="display", frames=[display_frame], onPage=draw_display_furniture),
        PageTemplate(id="twocol", frames=[colA, colB], onPage=draw_twocol_furniture),
        PageTemplate(id="twocolOpen", frames=[colA2, colB2], onPage=draw_twocol_opener_furniture),
    ])


# ------------------------------------------------------------- ayudantes

OPT_DIR = os.path.join(ASSETS, "_optimized")
os.makedirs(OPT_DIR, exist_ok=True)
TARGET_DPI = 220


def _optimized_path(filename, target_w_px):
    src = os.path.join(ASSETS, filename)
    dst = os.path.join(OPT_DIR, filename)
    if os.path.exists(dst):
        with PILImage.open(dst) as existing:
            if abs(existing.size[0] - target_w_px) <= 4:
                return dst
    with PILImage.open(src) as im:
        im = im.convert("RGB")
        if im.size[0] > target_w_px:
            ratio = target_w_px / im.size[0]
            im = im.resize((target_w_px, max(1, int(im.size[1] * ratio))), PILImage.LANCZOS)
        im.save(dst, "JPEG", quality=82, optimize=True)
    return dst


def img_flowable(filename, max_width, max_height=None, hAlign="CENTER"):
    src = os.path.join(ASSETS, filename)
    with PILImage.open(src) as im:
        iw, ih = im.size
    ratio = ih / iw
    w = max_width
    h = w * ratio
    if max_height and h > max_height:
        h = max_height
        w = h / ratio
    target_w_px = max(300, int(w / 72.0 * TARGET_DPI))
    path = _optimized_path(filename, target_w_px)
    im = Image(path, width=w, height=h)
    im.hAlign = hAlign
    return im


def paragraphs_from_text(text, first_style, rest_style):
    flowables = []
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    for i, p in enumerate(parts):
        style = first_style if i == 0 else rest_style
        p_escaped = p.replace("&", "&amp;")
        flowables.append(Paragraph(p_escaped, style))
    return flowables


def section_heading(display_text, running_title, toc_text, label=None):
    """Bloque de apertura de una sección/capítulo. Se asume que la página que lo
    recibe ya usa la plantilla 'twocolOpen' (sin cabecera); al final se
    reprograma la plantilla 'twocol' normal para las páginas siguientes,
    si el contenido de la sección se extiende más de una página."""
    flow = []
    if label:
        flow.append(Paragraph(label.upper(), STY["ChapterLabel"]))
    p = Paragraph(display_text, STY["ChapterTitleTOC"])
    p.runningTitle = running_title
    p.tocEntryText = toc_text
    flow.append(p)
    flow.append(HRFlowable(width="18%", thickness=0.8, color=RULE, spaceAfter=14,
                            hAlign="CENTER", lineCap="round"))
    flow.append(NextPageTemplate("twocol"))
    return flow


# ------------------------------------------------------------------ build

def build_story():
    story = []

    # ---------------------------------------------------------- portada
    cover_w_px = int(PAGE_W / 72.0 * TARGET_DPI)
    cover_path = _optimized_path("cover.jpg", cover_w_px)
    story.append(Image(cover_path, width=PAGE_W, height=PAGE_H))
    story.append(NextPageTemplate("display"))
    story.append(PageBreak())

    # ------------------------------------------------------- portadilla
    story.append(Spacer(1, FRAME_H * 0.30))
    story.append(Paragraph(C.TITULO, STY["CoverTitleBig"]))
    story.append(Paragraph(C.SUBTITULO, STY["CoverSub"]))
    story.append(Paragraph(C.AUTOR, STY["CoverAuthor"]))
    story.append(PageBreak())

    # ------------------------------------------------------------ legal
    story.append(Spacer(1, FRAME_H * 0.62))
    legal_lines = [
        "<b>EL FARO DE LOS AHOGADOS</b>",
        f"© Edición digital — {C.AUTOR}",
        "Primera edición",
        "",
        "Esta es una obra de ficción. Los nombres, personajes, instituciones, lugares "
        "y hechos son producto de la imaginación del autor o se usan de forma ficticia. "
        "Cualquier parecido con hechos, lugares o personas reales, vivas o muertas, es "
        "pura coincidencia.",
        "",
        "Maquetación, ilustraciones de cubierta e interior y diseño editorial: Tito.",
        "",
        "Queda prohibida la reproducción total o parcial de esta obra por cualquier "
        "medio sin autorización expresa del autor, salvo citas breves con fines de "
        "crítica o reseña.",
    ]
    for line in legal_lines:
        story.append(Paragraph(line, STY["Legal"]))
    story.append(PageBreak())

    # ------------------------------------------------------- dedicatoria
    story.append(Spacer(1, FRAME_H * 0.40))
    story.append(Paragraph(C.DEDICATORIA, STY["Dedication"]))
    story.append(PageBreak())

    # ---------------------------------------------------------- índice
    story.append(Paragraph("Índice", STY["TOCTitle"]))
    toc = TableOfContents()
    toc.levelStyles = [STY["TOCEntry"]]
    toc.dotsMinLevel = 0
    story.append(toc)

    story.append(NextPageTemplate("twocolOpen"))
    story.append(PageBreak())

    # --------------------------------------------------------- prefacio
    story.extend(section_heading("Prefacio", "Prefacio", "Prefacio"))
    story.extend(paragraphs_from_text(C.PREFACIO.split("\n\n", 1)[1], STY["BodyFirst"], STY["Body"]))
    story.append(NextPageTemplate("twocolOpen"))
    story.append(PageBreak())

    # ------------------------------------------------------ introducción
    story.extend(section_heading("Introducción", "Introducción", "Introducción"))
    story.extend(paragraphs_from_text(C.INTRODUCCION.split("\n\n", 1)[1], STY["BodyFirst"], STY["Body"]))
    story.append(NextPageTemplate("twocolOpen"))
    story.append(PageBreak())

    # ----------------------------------------------------------- capítulos
    for num, title, text in C.CAPITULOS:
        label = f"Capítulo {CHAPTER_WORDS[num-1].capitalize()}"
        toc_text = f"Capítulo {num} — {title}"
        story.extend(section_heading(title, title, toc_text, label=label))

        body_text = text
        epigraph = None
        if "\n\n" in text:
            first_line, rest = text.split("\n\n", 1)
            if len(first_line) < 60 and ("—" in first_line or first_line[0].isdigit()):
                epigraph = first_line
                body_text = rest

        if epigraph:
            story.append(Paragraph(epigraph, STY["Epigraph"]))

        if num in CHAPTER_IMAGES:
            fname, caption = CHAPTER_IMAGES[num]
            story.append(img_flowable(fname, COL_W, max_height=68 * mm))
            story.append(Paragraph(caption, STY["Caption"]))

        story.extend(paragraphs_from_text(body_text, STY["BodyFirst"], STY["Body"]))
        story.append(NextPageTemplate("twocolOpen"))
        story.append(PageBreak())

    # ----------------------------------------------------------- epílogo
    story.extend(section_heading("Epílogo", "Epílogo", "Epílogo"))
    story.append(img_flowable("epilogo_huellas.jpg", COL_W, max_height=60 * mm))
    story.append(Paragraph("El único rastro de pisadas que no volvía a salir del agua.", STY["Caption"]))
    story.extend(paragraphs_from_text(C.EPILOGO.split("\n\n", 1)[1], STY["BodyFirst"], STY["Body"]))
    story.append(NextPageTemplate("twocolOpen"))
    story.append(PageBreak())

    # ------------------------------------------------------- sobre el autor
    story.extend(section_heading("Sobre el autor", "Sobre el autor", "Sobre el autor"))
    story.extend(paragraphs_from_text(C.SOBRE_AUTOR.split("\n\n", 1)[1], STY["BodyFirst"], STY["Body"]))

    return story


def main():
    doc = BookDocTemplate(
        OUT_PDF, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN, topMargin=TOP_MARGIN, bottomMargin=BOTTOM_MARGIN,
        title=C.TITULO, author=C.AUTOR, subject=C.SUBTITULO,
    )
    build_templates(doc)
    doc._curr_running_title = C.TITULO
    story = build_story()
    doc.multiBuild(story)
    print("PDF generado en:", OUT_PDF)


if __name__ == "__main__":
    main()
