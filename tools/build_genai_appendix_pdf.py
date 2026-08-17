from pathlib import Path

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "drafts" / "ISR_genai_use_appendix_2026-08-17.md"
OUTPUT_DIR = ROOT / "output" / "pdf"
OUTPUT = OUTPUT_DIR / "ISR_genai_use_appendix_2026-08-17.pdf"


def body_text(text: str) -> str:
    replacements = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.replace("**", "")


def build() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="TitleCentered", parent=styles["Title"], alignment=TA_CENTER,
        fontName="Helvetica-Bold", fontSize=16, leading=20, spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="Heading", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=11, leading=14, spaceBefore=8, spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name="BodyClean", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=9.5, leading=13, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="BulletClean", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=9.5, leading=13, leftIndent=12, firstLineIndent=-7, spaceAfter=3,
    ))

    story = []
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 3))
        elif line.startswith("# "):
            story.append(Paragraph(body_text(line[2:]), styles["TitleCentered"]))
        elif line.startswith("## "):
            story.append(Paragraph(body_text(line[3:]), styles["Heading"]))
        elif line.startswith("- "):
            story.append(Paragraph("&#8226; " + body_text(line[2:]), styles["BulletClean"]))
        elif line.startswith("1. ") or line.startswith("2. ") or line.startswith("3. ") or line.startswith("4. ") or line.startswith("5. ") or line.startswith("6. ") or line.startswith("7. "):
            story.append(Paragraph(body_text(line), styles["BulletClean"]))
        else:
            story.append(Paragraph(body_text(line), styles["BodyClean"]))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawString(18 * mm, 12 * mm, "The Return Brake - GenAI Use Appendix draft")
        canvas.drawRightString(192 * mm, 12 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=20 * mm,
        title="GenAI Use Appendix - The Return Brake",
        author="Junior (VanderAI) and Codex",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == "__main__":
    build()

