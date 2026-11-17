"""Exporta PDF do mesmo conteúdo usado no DOCX, sem depender do Microsoft Word."""
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from gerar_relatorio import ROOT, report_blocks

def export(blocks, output, title):
    fonts = Path('C:/Windows/Fonts')
    for name, file in [('Arial', 'arial.ttf'), ('Arial-Bold', 'arialbd.ttf'), ('Arial-Italic', 'ariali.ttf')]:
        pdfmetrics.registerFont(TTFont(name, str(fonts / file)))
    styles = {'p': ParagraphStyle('body', fontName='Arial', fontSize=10.5, leading=14, spaceAfter=7), 'title': ParagraphStyle('title', fontName='Arial-Bold', fontSize=24, leading=28, spaceAfter=10), 'subtitle': ParagraphStyle('subtitle', fontName='Arial', fontSize=12, leading=16, spaceAfter=9), 'h': ParagraphStyle('heading', fontName='Arial-Bold', fontSize=12.5, leading=16, spaceBefore=9, spaceAfter=6, keepWithNext=True), 'caption': ParagraphStyle('caption', fontName='Arial-Italic', fontSize=8.5, leading=11, spaceAfter=8), 'ref': ParagraphStyle('reference', fontName='Arial', fontSize=9, leading=12, spaceAfter=8, wordWrap='CJK'), 'cell': ParagraphStyle('cell', fontName='Arial', fontSize=9, leading=11), 'header': ParagraphStyle('header', fontName='Arial-Bold', fontSize=9, leading=11, textColor=colors.white)}

    def paragraph(value, style):
        return Paragraph(escape(str(value)).replace('\n', '<br/>'), styles[style])
    story = []
    for b in blocks:
        k = b['kind']
        if k == 'group':
            story.append(KeepTogether([paragraph(child['text'], child['kind']) for child in b['children']]))
        elif k == 'break':
            story.append(PageBreak())
        elif k == 'table':
            rows = [[paragraph(v, 'header' if j == 0 else 'cell') for v in row] for j, row in enumerate([b['headers'], *b['rows']])]
            widths = [w / sum(b['widths']) * (A4[0] - 100) for w in b['widths']]
            t = Table(rows, colWidths=widths, repeatRows=1, hAlign='LEFT')
            t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#213A52')), ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F2F5F7'), colors.white]), ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#D9D9D9')), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6), ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]))
            story += [t, Spacer(1, 7)]
        elif k == 'image':
            from PIL import Image as PILImage
            file = ROOT / 'graficos' / b['filename']
            with PILImage.open(file) as im:
                w, h = im.size
            width = A4[0] - 100
            story += [Image(str(file), width=width, height=width * h / w), Spacer(1, 4)]
        else:
            story.append(paragraph(b['text'], k if k in styles else 'p'))

    def footer(c, doc):
        c.setFont('Arial', 8)
        c.setFillColor(colors.HexColor('#52616D'))
        c.drawRightString(A4[0] - 50, 27, f'MC851A   {doc.page}')
    doc = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=50, leftMargin=50, topMargin=42, bottomMargin=42, title=title, author='Alexandre Adler e André Macarini')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)

if __name__ == "__main__":
    export(report_blocks(), ROOT / "relatorio" / "relatorio-final.pdf", "Impacto da busca no desempenho do MkDocs")
