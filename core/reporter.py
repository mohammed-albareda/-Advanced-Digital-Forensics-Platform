from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from datetime import datetime
import arabic_reshaper
from bidi.algorithm import get_display

import re

def has_arabic(text):
    """Checks if a string contains Arabic characters."""
    return bool(re.search(r'[\u0600-\u06FF]', str(text)))

_arabic_cache = {}

def fix_arabic(text):
    """Reshapes and reorders text ONLY if it contains Arabic characters."""
    if not text:
        return ""
    
    text_str = str(text)
    if not has_arabic(text_str):
        return text_str # Keep English/Paths as they are
        
    if text_str in _arabic_cache:
        return _arabic_cache[text_str]
        
    reshaped_text = arabic_reshaper.reshape(text_str)
    display_text = get_display(reshaped_text)
    _arabic_cache[text_str] = display_text
    return display_text

from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.legends import Legend
from reportlab.lib.validators import isColor

def generate_pdf_report(output_path, directory, results):
    """Generates a premium PDF report with a dashboard and charts."""
    
    font_path = "C:\\Windows\\Fonts\\arial.ttf"
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('Arial', font_path))
        main_font = 'Arial'
    else:
        main_font = 'Helvetica'

    doc = SimpleDocTemplate(output_path, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom colors
    color_modified = colors.HexColor("#f44747") # Reddish
    color_new = colors.HexColor("#dcdcaa")      # Yellowish
    color_deleted = colors.HexColor("#ce9178")  # Orangeish
    color_intact = colors.HexColor("#4ec9b0")   # Teal/Green

    # Styles
    styles['Title'].fontName = main_font
    styles['Title'].fontSize = 26
    styles['Title'].textColor = colors.HexColor("#007acc")
    styles['Title'].alignment = 1

    styles['Normal'].fontName = main_font
    styles['Normal'].alignment = 2

    # Title
    elements.append(Paragraph(fix_arabic("تقرير مراقبة سلامة الملفات"), styles['Title']))
    elements.append(Paragraph(fix_arabic("File Integrity Professional Report"), styles['Title']))
    elements.append(Spacer(1, 20))

    # --- Dashboard Section ---
    # Calculate Stats
    stats = {"Modified": 0, "New": 0, "Deleted": 0}
    for res in results:
        if "Modified" in res['status']: stats["Modified"] += 1
        elif "New" in res['status']: stats["New"] += 1
        elif "Deleted" in res['status']: stats["Deleted"] += 1

    # Summary Table (Dashboard)
    summary_data = [
        [fix_arabic("إحصائيات الفحص"), ""],
        [fix_arabic(f"ملفات معدلة: {stats['Modified']}"), fix_arabic(f"ملفات جديدة: {stats['New']}")],
        [fix_arabic(f"ملفات محذوفة: {stats['Deleted']}"), fix_arabic(f"إجمالي التغييرات: {len(results)}")]
    ]
    
    stb = Table(summary_data, colWidths=[240, 240])
    stb.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), main_font),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#333333")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('SPAN', (0, 0), (1, 0)),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.whitesmoke),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(stb)
    elements.append(Spacer(1, 25))

    # --- Pie Chart Section ---
    if len(results) > 0:
        drawing = Drawing(400, 200)
        pc = Pie()
        pc.x = 150
        pc.y = 50
        pc.width = 100
        pc.height = 100
        pc.data = [stats['Modified'], stats['New'], stats['Deleted']]
        pc.labels = ['Modified', 'New', 'Deleted']
        pc.sideLabels = 1
        pc.slices.fontName = main_font
        pc.slices[0].fillColor = color_modified
        pc.slices[1].fillColor = color_new
        pc.slices[2].fillColor = color_deleted
        
        drawing.add(pc)
        
        # Add Legend
        lp = Legend()
        lp.x = 20
        lp.y = 120
        lp.fontName = main_font
        lp.alignment = 'right'
        lp.columnMaximum = 10
        lp.colorNamePairs = [(color_modified, 'Modified'), (color_new, 'New'), (color_deleted, 'Deleted')]
        drawing.add(lp)
        
        elements.append(drawing)
        elements.append(Spacer(1, 20))

    # --- Details Section ---
    cell_style_ar = styles["Normal"].clone("cell_style_ar")
    cell_style_ar.fontName = main_font
    cell_style_ar.fontSize = 9
    cell_style_ar.alignment = 2 
    
    cell_style_en = styles["Normal"].clone("cell_style_en")
    cell_style_en.fontName = main_font
    cell_style_en.fontSize = 8
    cell_style_en.alignment = 0 
    cell_style_en.wordWrap = 'CJK'

    data = [[Paragraph(fix_arabic("التفاصيل"), cell_style_ar), 
             Paragraph(fix_arabic("الحالة"), cell_style_ar), 
             Paragraph(fix_arabic("مسار الملف"), cell_style_ar)]]
    
    for res in results:
        s_details = cell_style_ar if has_arabic(res['details']) else cell_style_en
        s_status = cell_style_ar if has_arabic(res['status']) else cell_style_en
        data.append([
            Paragraph(fix_arabic(res['details']), s_details),
            Paragraph(fix_arabic(res['status']), s_status),
            Paragraph(res['file'], cell_style_en)
        ])

    table = Table(data, colWidths=[100, 80, 320])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#007acc")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, -1), main_font),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#f2f2f2")]),
    ]))
    
    elements.append(table)
    doc.build(elements)
