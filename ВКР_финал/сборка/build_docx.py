#!/usr/bin/env python3
"""Сборка единого DOCX ВКР и отдельных файлов приложений из Markdown-черновиков."""

from pathlib import Path
import re

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
FINAL = ROOT / 'ВКР_финал'
APPENDICES = FINAL / 'Приложения'
OUT = FINAL / 'ВКР_полная.docx'
APPENDIX_DOCX = APPENDICES / 'docx'

MAIN_FILES = [
    FINAL / '01_Введение_черновик.md',
    FINAL / '02_Глава1_черновик.md',
    FINAL / '03_Глава2_черновик.md',
    FINAL / '04_Глава3_черновик.md',
    FINAL / '05_Заключение_черновик.md',
    FINAL / '06_Список_источников.md',
]

APPENDIX_FILES = [
    APPENDICES / 'А_Рабочая_программа_и_КТП.md',
    APPENDICES / 'Б_Технологические_карты.md',
    APPENDICES / 'В_Рабочая_тетрадь_ученика.md',
    APPENDICES / 'Г_Документация_LaserControl.md',
    APPENDICES / 'Д_КОС.md',
    APPENDICES / 'Е_Охрана_труда.md',
    APPENDICES / 'Ж_Протоколы_апробации.md',
]

INLINE_RE = re.compile(r'(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)')
TABLE_SEP_RE = re.compile(r'^\|(?:\s*:?-{3,}:?\s*\|)+$')


def set_cell_font(cell, size=9, bold=False):
    for paragraph in cell.paragraphs:
        paragraph.paragraph_format.first_line_indent = Cm(0)
        paragraph.paragraph_format.line_spacing = 1.0
        for run in paragraph.runs:
            run.font.name = 'Times New Roman'
            run.font.size = Pt(size)
            run.bold = bold


def add_inline(paragraph, text, base_size=None):
    for part in INLINE_RE.split(text):
        if not part:
            continue
        if part.startswith('**') and part.endswith('**'):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        elif part.startswith('`') and part.endswith('`'):
            run = paragraph.add_run(part[1:-1])
            run.font.name = 'Consolas'
        elif part.startswith('*') and part.endswith('*'):
            run = paragraph.add_run(part[1:-1])
            run.italic = True
        else:
            run = paragraph.add_run(part)
        run.font.name = run.font.name or 'Times New Roman'
        if base_size:
            run.font.size = Pt(base_size)


def add_table(doc, rows):
    header = [c.strip() for c in rows[0].strip().strip('|').split('|')]
    ncols = len(header)
    table = doc.add_table(rows=1, cols=ncols)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    for i, value in enumerate(header):
        cell = table.rows[0].cells[i]
        cell.text = ''
        add_inline(cell.paragraphs[0], value)
        for run in cell.paragraphs[0].runs:
            run.bold = True
    set_cell_font_row(table.rows[0], bold=True)

    for raw in rows[1:]:
        cells = [c.strip() for c in raw.strip().strip('|').split('|')]
        cells += [''] * (ncols - len(cells))
        cells = cells[:ncols]
        row = table.add_row()
        for i, value in enumerate(cells):
            cell = row.cells[i]
            cell.text = ''
            add_inline(cell.paragraphs[0], value)
        set_cell_font_row(row)
    doc.add_paragraph()


def set_cell_font_row(row, bold=False):
    for cell in row.cells:
        set_cell_font(cell, bold=bold)


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    begin = OxmlElement('w:fldChar')
    begin.set(qn('w:fldCharType'), 'begin')
    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = ' PAGE '
    separate = OxmlElement('w:fldChar')
    separate.set(qn('w:fldCharType'), 'separate')
    text = OxmlElement('w:t')
    text.text = '1'
    end = OxmlElement('w:fldChar')
    end.set(qn('w:fldCharType'), 'end')
    run._r.extend([begin, instr, separate, text, end])
    run.font.size = Pt(11)


def add_toc(doc):
    paragraph = doc.add_paragraph()
    run = paragraph.add_run()
    begin = OxmlElement('w:fldChar')
    begin.set(qn('w:fldCharType'), 'begin')
    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = 'TOC \\o "1-3" \\h \\z \\u'
    separate = OxmlElement('w:fldChar')
    separate.set(qn('w:fldCharType'), 'separate')
    hint = OxmlElement('w:t')
    hint.text = 'Обновите поле (F9) после сборки документа.'
    end = OxmlElement('w:fldChar')
    end.set(qn('w:fldCharType'), 'end')
    run._r.extend([begin, instr, separate, hint, end])


def setup_document():
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(3.0)
    section.right_margin = Cm(1.5)

    normal = doc.styles['Normal']
    normal.font.name = 'Times New Roman'
    normal.font.size = Pt(14)
    normal.element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.first_line_indent = Cm(1.25)

    for name, size in [('Heading 1', 16), ('Heading 2', 15), ('Heading 3', 14), ('Heading 4', 14)]:
        style = doc.styles[name]
        style.font.name = 'Times New Roman'
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.first_line_indent = Cm(0)
        style.paragraph_format.space_before = Pt(12)
        style.paragraph_format.space_after = Pt(6)
        style.paragraph_format.keep_with_next = True

    add_page_number(section.footer.paragraphs[0])
    return doc


def render_markdown(doc, text, start_new_page=True):
    lines = text.splitlines()
    i = 0
    first_block = True
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if not stripped or stripped == '---':
            i += 1
            continue

        if stripped.startswith('```'):
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1
            p = doc.add_paragraph()
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.line_spacing = 1.0
            run = p.add_run('\n'.join(code_lines))
            run.font.name = 'Consolas'
            run.font.size = Pt(10)
            continue

        if stripped.startswith('|') and i + 1 < len(lines) and TABLE_SEP_RE.match(lines[i + 1].strip()):
            rows = [line]
            i += 2
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append(lines[i])
                i += 1
            add_table(doc, rows)
            continue

        heading = re.match(r'^(#{1,4})\s+(.*)$', stripped)
        if heading:
            level = len(heading.group(1))
            p = doc.add_paragraph(style=f'Heading {level}')
            if level == 1 and not (first_block and not start_new_page):
                p.paragraph_format.page_break_before = True
            add_inline(p, heading.group(2))
            first_block = False
            i += 1
            continue

        if stripped.startswith('> '):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(1.0)
            p.paragraph_format.first_line_indent = Cm(0)
            add_inline(p, stripped[2:])
            for r in p.runs:
                r.italic = True
            i += 1
            continue

        bullet = re.match(r'^[-–]\s+(.*)$', stripped)
        if bullet:
            p = doc.add_paragraph(style='List Bullet')
            add_inline(p, bullet.group(1))
            i += 1
            continue

        numbered = re.match(r'^(\d+)\.\s+(.*)$', stripped)
        if numbered:
            p = doc.add_paragraph(style='List Number')
            add_inline(p, numbered.group(2))
            i += 1
            continue

        p = doc.add_paragraph()
        add_inline(p, stripped)
        first_block = False
        i += 1


def add_title_page(doc):
    center = WD_ALIGN_PARAGRAPH.CENTER
    def line(text, bold=False, size=14, space_after=6):
        p = doc.add_paragraph()
        p.alignment = center
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(space_after)
        r = p.add_run(text)
        r.bold = bold
        r.font.size = Pt(size)
        return p

    line('МИНИСТЕРСТВО ПРОСВЕЩЕНИЯ РОССИЙСКОЙ ФЕДЕРАЦИИ', size=12)
    line('ФЕДЕРАЛЬНОЕ ГОСУДАРСТВЕННОЕ БЮДЖЕТНОЕ ОБРАЗОВАТЕЛЬНОЕ УЧРЕЖДЕНИЕ '
         'ВЫСШЕГО ОБРАЗОВАНИЯ «РОССИЙСКИЙ ГОСУДАРСТВЕННЫЙ ПЕДАГОГИЧЕСКИЙ '
         'УНИВЕРСИТЕТ им. А. И. ГЕРЦЕНА»', size=12)
    line('Институт информационных технологий и технологического образования', size=12)
    line('Кафедра технологического образования', size=12, space_after=24)
    line('Направление подготовки 44.04.01 «Педагогическое образование»', size=12)
    line('Направленность (профиль) «Робототехника, предпринимательство и дизайн '
         'в технологическом образовании»', size=12, space_after=24)
    line('ВЫПУСКНАЯ КВАЛИФИКАЦИОННАЯ РАБОТА', bold=True, size=16)
    line('(магистерская диссертация)', size=12, space_after=24)
    line('на тему: «Разработка и апробация комплекса дидактических материалов '
         'для модуля „Автоматизированные системы“ с использованием визуального '
         'программирования (mBlock) и лазерного гравера ACMER S1»', bold=True, size=14, space_after=30)
    line('Выполнил(а): обучающийся(ая) {{курс, форма}} Шкаликов Никита Николаевич', size=12)
    line('Научный руководитель: {{учёная степень, звание}} Рыжова Наталья Ивановна', size=12, space_after=36)
    line('Санкт-Петербург, {{год защиты}}', size=12)
    doc.add_page_break()


def add_front_matter(doc):
    p = doc.add_paragraph(style='Heading 1')
    p.add_run('АННОТАЦИЯ')
    title_src = (FINAL / '00_титул_и_структура.md').read_text(encoding='utf-8')
    ann = title_src.split('## 2. Аннотация (заготовка)', 1)[1].split('## 3. Содержание', 1)[0]
    ann = ann.replace('**Аннотация.**', '').replace('**Ключевые слова:**', 'Ключевые слова: ')
    ann = ann.replace('**Abstract.**', '').replace('**Keywords:**', 'Keywords: ')
    ann = ann.replace('*После титула по требованию кафедры: задание на ВКР, задание руководителя, '
                      'график-календарь, отзыв и рецензия (на отдельных листах).*', '')
    render_markdown(doc, ann, start_new_page=False)

    h = doc.add_paragraph(style='Heading 1')
    h.add_run('СПИСОК СОКРАЩЕНИЙ')
    abbreviations = [
        'АС — автоматизированная система',
        'ИОТ — инструкция по охране труда',
        'КОС — контрольно-оценочные средства',
        'КТП — календарно-тематическое планирование',
        'КГ — контрольная группа',
        'ОУ — образовательное учреждение',
        'РТ — рабочая тетрадь',
        'СИЗ — средства индивидуальной защиты',
        'ТБ — техника безопасности',
        'ТК — технологическая карта',
        'УМК — учебно-методический комплекс',
        'УУД — универсальные учебные действия',
        'ЭГ — экспериментальная группа',
        'ЧПУ — числовое программное управление',
        'GRBL — прошивка станков ЧПУ, исполняющая G-код',
        'SVG — формат векторной графики',
        'ШИМ — широтно-импульсная модуляция',
    ]
    for item in abbreviations:
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)
        p.add_run(item)

    h = doc.add_paragraph(style='Heading 1')
    h.add_run('ОГЛАВЛЕНИЕ')
    add_toc(doc)
    note = doc.add_paragraph()
    note.paragraph_format.first_line_indent = Cm(0)
    r = note.add_run('Номера страниц проставляются после обновления поля оглавления в текстовом редакторе.')
    r.italic = True
    doc.add_page_break()


def clean_source(text, path):
    if path.name == '01_Введение_черновик.md':
        text = '\n'.join(l for l in text.splitlines() if not l.startswith('> '))
        text = text.replace('# ВВЕДЕНИЕ (черновик финальной версии)', '# ВВЕДЕНИЕ')
    return text


def build_main():
    doc = setup_document()
    add_title_page(doc)
    add_front_matter(doc)
    for path in MAIN_FILES:
        text = clean_source(path.read_text(encoding='utf-8'), path)
        render_markdown(doc, text)
    for path in APPENDIX_FILES:
        render_markdown(doc, path.read_text(encoding='utf-8'))
    doc.save(OUT)
    print(f'Main document: {OUT.relative_to(ROOT)}')


def build_appendix_files():
    APPENDIX_DOCX.mkdir(parents=True, exist_ok=True)
    for path in APPENDIX_FILES:
        doc = setup_document()
        render_markdown(doc, path.read_text(encoding='utf-8'), start_new_page=False)
        out = APPENDIX_DOCX / (path.stem + '.docx')
        doc.save(out)
        print(f'Appendix: {out.relative_to(ROOT)}')


if __name__ == '__main__':
    build_main()
    build_appendix_files()
