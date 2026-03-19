"""
PDF Report Generator - Creates a simple two-section max pain PDF report
using reportlab. No branding, no photos — clean tabular output only.

Sections:
  1. Sorted by Net Premium (abs value descending)
  2. Sorted by Ticker Symbol (alphabetical)

Each section shows indices (SPY/QQQ/IWM) at the top, then stocks.
Columns: Ticker | Close | Max Pain | % Change | Net Call/(Put) Premium
Top 20 by abs(net_premium) are marked with an asterisk.
"""

import logging
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak, HRFlowable, Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# Tickers treated as indices (shown in a separate block at the top of each section)
INDEX_TICKERS = {'SPY', 'QQQ', 'IWM'}

# Colour palette
GREEN = colors.HexColor('#27ae60')
RED = colors.HexColor('#c0392b')
HEADER_BG = colors.HexColor('#2c3e50')
INDEX_BG = colors.HexColor('#eaf4fb')
ALT_ROW_BG = colors.HexColor('#f8f8f8')
WHITE = colors.white
BLACK = colors.black
LIGHT_GREY = colors.HexColor('#dddddd')


class PdfReportGenerator:
    """Generates a simple two-section max pain PDF report."""

    def __init__(self, config):
        self.logger = logging.getLogger('max_pain.pdf_report_generator')
        self.config = config
        self.output_dir = config.get('OUTPUT', 'output_dir', fallback='results')
        self.highlight_top_n = config.getint('OUTPUT', 'highlight_top_n', fallback=20)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def generate_pdf_report(self, results_list):
        """
        Generate the PDF report.

        Args:
            results_list: list of result dicts (already has is_top_n flag set)

        Returns:
            Path to the generated PDF file
        """
        pdf_dir = os.path.join(self.output_dir, 'pdf')
        os.makedirs(pdf_dir, exist_ok=True)

        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = f"{date_str}_max_pain_report.pdf"
        filepath = os.path.join(pdf_dir, filename)

        # Extract expiration date from first result that has it
        expiration_date = next(
            (r.get('expiration_date') for r in results_list if r.get('expiration_date')),
            None
        )

        # Resolve Max's photo path relative to this source file
        _here = os.path.dirname(os.path.abspath(__file__))
        max_photo_path = os.path.join(_here, '..', 'user_input', 'max_template.png')

        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            leftMargin=0.5 * inch,
            rightMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
        )

        styles = self._build_styles()
        story = []

        # ---- Section 1: sorted by net premium (with Max's photo) ----
        sorted_by_premium = sorted(
            results_list,
            key=lambda x: abs(x.get('net_call_put_premium', 0)),
            reverse=True,
        )
        story += self._build_section(
            sorted_by_premium,
            title='SORTED BY: NET PREMIUM ($)',
            date_str=date_str,
            expiration_date=expiration_date,
            styles=styles,
            max_photo_path=max_photo_path,
        )

        story.append(PageBreak())

        # ---- Section 2: sorted alphabetically ----
        sorted_alpha = sorted(results_list, key=lambda x: x.get('ticker', ''))
        story += self._build_section(
            sorted_alpha,
            title='SORTED BY: TICKER SYMBOL',
            date_str=date_str,
            expiration_date=expiration_date,
            styles=styles,
        )

        story.append(PageBreak())

        # ---- Section 3: verification links ----
        story += self._build_verification_section(results_list, styles)

        doc.build(story)
        self.logger.info(f"PDF report saved to: {filepath}")
        return filepath

    # ------------------------------------------------------------------
    # Section builder
    # ------------------------------------------------------------------

    def _build_section(self, results, title, date_str, expiration_date, styles,
                       max_photo_path=None):
        """Build flowables for one section (header + index block + stocks table)."""
        elements = []

        # Header row: title/subtitle on left, Max's photo on right (first page only)
        if max_photo_path and os.path.exists(max_photo_path):
            title_para = Paragraph('MAX PAIN ANALYSIS', styles['report_title'])
            subtitle_parts = [datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %Y').upper()]
            if expiration_date:
                subtitle_parts.append(f'Options Expiration: {expiration_date}')
            subtitle_para = Paragraph('  |  '.join(subtitle_parts), styles['report_subtitle'])
            title_block = [[title_para], [subtitle_para]]
            title_tbl = Table(title_block, colWidths=[5.5 * inch])
            title_tbl.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            photo = Image(max_photo_path, width=1.2 * inch, height=0.9 * inch)
            header_row = [[title_tbl, photo]]
            header_tbl = Table(header_row, colWidths=[6.3 * inch, 1.2 * inch])
            header_tbl.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            elements.append(header_tbl)
        else:
            elements.append(Paragraph('MAX PAIN ANALYSIS', styles['report_title']))
            subtitle_parts = [datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %Y').upper()]
            if expiration_date:
                subtitle_parts.append(f'Options Expiration: {expiration_date}')
            elements.append(Paragraph('  |  '.join(subtitle_parts), styles['report_subtitle']))

        elements.append(Spacer(1, 6))
        elements.append(HRFlowable(width='100%', thickness=1, color=LIGHT_GREY))
        elements.append(Spacer(1, 4))

        # Disclaimer
        disclaimer = (
            '<b>Max pain is not a guarantee</b> and is intended to be used solely for '
            '<i>directional clues</i>. All values below are computed using the data '
            'provided by <b>Yahoo Finance</b>. We cannot attest to the accuracy of the data. '
            'Trade at your own risk.'
        )
        elements.append(Paragraph(disclaimer, styles['disclaimer']))
        elements.append(Spacer(1, 4))

        asterisk_note = (
            '*An asterisk indicates a stock ranking in the top '
            f'{self.highlight_top_n} in terms of net premium (absolute value).'
        )
        elements.append(Paragraph(asterisk_note, styles['note']))
        elements.append(Spacer(1, 8))

        # Sorted-by banner
        elements.append(Paragraph(title, styles['section_banner']))
        elements.append(Spacer(1, 6))

        # Split into indices vs stocks
        indices = [r for r in results if r.get('ticker', '') in INDEX_TICKERS]
        stocks = [r for r in results if r.get('ticker', '') not in INDEX_TICKERS]

        # Column header row
        col_header = self._col_header_row(expiration_date)

        # Index block
        if indices:
            index_rows = [col_header] + [self._data_row(r, is_index=True) for r in indices]
            elements.append(self._build_table(index_rows, is_index_block=True))
            elements.append(Spacer(1, 4))

        # Stocks table
        if stocks:
            stock_rows = [col_header] + [self._data_row(r, is_index=False) for r in stocks]
            elements.append(self._build_table(stock_rows, is_index_block=False))

        return elements

    # ------------------------------------------------------------------
    # Table helpers
    # ------------------------------------------------------------------

    def _col_header_row(self, expiration_date=None):
        max_pain_label = f'Max Pain\n({expiration_date})' if expiration_date else 'Max Pain'
        return ['Ticker', 'Close', max_pain_label, '% Change', 'Net Call/(Put)\nPremium']

    def _data_row(self, result, is_index=False):
        ticker = result.get('ticker', '')
        is_top = result.get('is_top_n', False)

        ticker_label = f"{ticker}*" if (is_top and not is_index) else ticker

        close = result.get('current_price', 0) or 0
        max_pain = result.get('max_pain_price', 0) or 0
        pct = result.get('pct_change', 0) or 0
        net_prem = result.get('net_call_put_premium', 0) or 0

        close_str = f"{close:,.2f}"
        max_pain_str = f"{max_pain:,.2f}"
        pct_str = f"{pct:+.2f}%"
        net_prem_str = f"({abs(net_prem):,.0f})" if net_prem < 0 else f"{net_prem:,.0f}"

        return [ticker_label, close_str, max_pain_str, pct_str, net_prem_str]

    def _build_table(self, rows, is_index_block=False):
        """Build a reportlab Table with styling."""
        col_widths = [0.9 * inch, 0.85 * inch, 0.85 * inch, 0.85 * inch, 2.2 * inch]

        table = Table(rows, colWidths=col_widths, repeatRows=1)

        # Base style
        style_cmds = [
            # Header row
            ('BACKGROUND',  (0, 0), (-1, 0), HEADER_BG),
            ('TEXTCOLOR',   (0, 0), (-1, 0), WHITE),
            ('FONTNAME',    (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',    (0, 0), (-1, 0), 8),
            ('ALIGN',       (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
            # Data rows
            ('FONTNAME',    (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE',    (0, 1), (-1, -1), 7.5),
            ('ALIGN',       (1, 1), (-1, -1), 'RIGHT'),   # numbers right-aligned
            ('ALIGN',       (0, 1), (0, -1), 'LEFT'),     # ticker left-aligned
            ('TOPPADDING',  (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('GRID',        (0, 0), (-1, -1), 0.25, LIGHT_GREY),
            ('LINEBELOW',   (0, 0), (-1, 0), 1, HEADER_BG),
        ]

        # Alternating row backgrounds and % change colours
        for row_idx in range(1, len(rows)):
            result_idx = row_idx - 1  # 0-based into data
            row_data = rows[row_idx]

            # Alternating background
            bg = INDEX_BG if is_index_block else (ALT_ROW_BG if row_idx % 2 == 0 else WHITE)
            style_cmds.append(('BACKGROUND', (0, row_idx), (-1, row_idx), bg))

            # % Change colour (column 3)
            pct_str = row_data[3] if len(row_data) > 3 else ''
            try:
                pct_val = float(pct_str.replace('%', '').replace('+', ''))
                pct_colour = GREEN if pct_val > 0 else (RED if pct_val < 0 else BLACK)
            except ValueError:
                pct_colour = BLACK
            style_cmds.append(('TEXTCOLOR', (3, row_idx), (3, row_idx), pct_colour))

            # Top-N rows: bold ticker
            ticker_str = row_data[0] if row_data else ''
            if ticker_str.endswith('*'):
                style_cmds.append(('FONTNAME', (0, row_idx), (0, row_idx), 'Helvetica-Bold'))

        table.setStyle(TableStyle(style_cmds))
        return table

    # ------------------------------------------------------------------
    # Verification section
    # ------------------------------------------------------------------

    def _build_verification_section(self, results, styles):
        """Build a final page with static verification source information."""
        elements = []

        elements.append(Paragraph('VERIFICATION SOURCES', styles['report_title']))
        elements.append(Spacer(1, 4))
        elements.append(HRFlowable(width='100%', thickness=1, color=LIGHT_GREY))
        elements.append(Spacer(1, 8))

        note = (
            'Use the sources below to manually cross-check max pain values. '
            'Replace TICKER in the URL patterns with the symbol you want to verify.'
        )
        elements.append(Paragraph(note, styles['disclaimer']))
        elements.append(Spacer(1, 16))

        sources = [
            (
                '1.  maximum-pain.com',
                'Shows max pain strike + dollar value bars per strike. '
                'Closest to what this report is computing.',
                'maximum-pain.com',
            ),
            (
                '2.  barchart.com',
                'Very reputable data source, free max pain chart.',
                'barchart.com/stocks/quotes/TICKER/max-pain-chart',
            ),
            (
                '3.  optioncharts.io',
                'Clean visual max pain chart.',
                'optioncharts.io/options/TICKER/max-pain',
            ),
        ]

        for label, desc, url in sources:
            elements.append(Paragraph(f'<b>{label}</b>', styles['section_banner_left']))
            elements.append(Spacer(1, 2))
            elements.append(Paragraph(desc, styles['disclaimer']))
            elements.append(Spacer(1, 2))
            elements.append(Paragraph(f'URL:  {url}', styles['note']))
            elements.append(Spacer(1, 12))

        return elements

    # ------------------------------------------------------------------
    # Styles
    # ------------------------------------------------------------------

    def _build_styles(self):
        base = getSampleStyleSheet()
        styles = {}

        styles['report_title'] = ParagraphStyle(
            'report_title',
            parent=base['Normal'],
            fontSize=14,
            fontName='Helvetica-Bold',
            textColor=HEADER_BG,
            alignment=TA_LEFT,
            spaceAfter=2,
        )
        styles['report_subtitle'] = ParagraphStyle(
            'report_subtitle',
            parent=base['Normal'],
            fontSize=9,
            fontName='Helvetica',
            textColor=colors.HexColor('#666666'),
            alignment=TA_LEFT,
        )
        styles['disclaimer'] = ParagraphStyle(
            'disclaimer',
            parent=base['Normal'],
            fontSize=7.5,
            fontName='Helvetica',
            leading=10,
            alignment=TA_LEFT,
        )
        styles['note'] = ParagraphStyle(
            'note',
            parent=base['Normal'],
            fontSize=7.5,
            fontName='Helvetica-Oblique',
            leading=10,
            alignment=TA_LEFT,
        )
        styles['section_banner'] = ParagraphStyle(
            'section_banner',
            parent=base['Normal'],
            fontSize=9,
            fontName='Helvetica-Bold',
            textColor=BLACK,
            alignment=TA_CENTER,
            borderPad=4,
        )
        styles['section_banner_left'] = ParagraphStyle(
            'section_banner_left',
            parent=base['Normal'],
            fontSize=9,
            fontName='Helvetica-Bold',
            textColor=BLACK,
            alignment=TA_LEFT,
            borderPad=4,
        )
        return styles
