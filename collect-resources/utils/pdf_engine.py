"""
PDF engine module for PDF document structure and clickable link mapping.
"""

import os
import urllib.request
from typing import List, Dict, Any
from fpdf import FPDF


class PDF(FPDF):
    """Extended FPDF class with hyperlink support."""

    def __init__(self):
        super().__init__()
        self.font_family = 'Helvetica'  # default to core font
        font_dir = os.path.join(os.path.dirname(__file__), 'fonts')
        font_path = os.path.join(font_dir, 'DejaVuSans.ttf')
        if not os.path.exists(font_path):
            try:
                os.makedirs(font_dir, exist_ok=True)
                url = "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSans.ttf"
                urllib.request.urlretrieve(url, font_path)
            except Exception as e:
                # If download fails, we keep Helvetica
                pass
        # Now, if the font file exists, we try to add it
        if os.path.exists(font_path):
            try:
                self.add_font('DejaVu', '', font_path, uni=True)
                self.font_family = 'DejaVu'
            except Exception as e:
                # If adding fails, we keep Helvetica
                pass

    def header(self):
        """Add header to each page."""
        self.set_font(self.font_family, 'B', 15)
        self.cell(0, 10, 'Search Results Report', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        """Add footer to each page."""
        self.set_y(-15)
        self.set_font(self.font_family, 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


def generate_pdf(results: List[Dict[str, Any]], query: str, output_path: str):
    """
    Generate a PDF report of search results.
    Format matches the text file output for readability.

    Args:
        results: List of result dictionaries
        query: The search query
        output_path: Path where PDF should be saved
    """
    pdf = PDF()
    pdf.add_page()
    pdf.set_font(pdf.font_family, '', 12)

    # Helper function to sanitize text for PDF (replace em dash with hyphen)
    def sanitize(text):
        if text is None:
            return ''
        return str(text).replace('—', '-')

    pdf.multi_cell(w=0, h=5, txt=f'Search Query: {sanitize(query)}', border=0, ln=1, align='L')
    pdf.multi_cell(w=0, h=5, txt=f'Total Results: {len(results)}', border=0, ln=1, align='L')
    pdf.multi_cell(w=0, h=5, txt='=' * 50, border=0, ln=1, align='L')
    pdf.ln(5)  # blank line after the equals line

    pdf.set_font(pdf.font_family, 'B', 12)
    pdf.multi_cell(w=0, h=5, txt='Results:', border=0, ln=1, align='L')
    pdf.ln(5)  # space after Results:

    pdf.set_font(pdf.font_family, '', 10)
    for i, result in enumerate(results, 1):
        lines = [
            f'{i}. {sanitize(result["title"])} ({sanitize(result["source"])})',
            f'   Description: {sanitize(result["description"])}',
            f'   URL: {sanitize(result["url"])}',
            f'   Reputable: {"Yes" if result["reputable"] else "No"}',
            '-' * 50
        ]
        for line in lines:
            pdf.multi_cell(w=0, h=5, txt=line, border=0, ln=1, align='L')
        pdf.ln(2)  # extra space between entries

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or '.', exist_ok=True)

    # Save PDF
    pdf.output(output_path)


def create_simple_pdf(results: List[Dict[str, Any]], query: str, output_path: str):
    """
    Create a simple PDF report (alternative implementation).
    Kept for backward compatibility.

    Args:
        results: List of result dictionaries
        query: The search query
        output_path: Path where PDF should be saved
    """
    pdf = PDF()
    pdf.add_page()
    pdf.set_font(pdf.font_family, 'B', 16)
    pdf.cell(0, 10, 'Search Results Report', 0, 1, 'C')
    pdf.ln(10)
    pdf.set_font(pdf.font_family, '', 12)
    pdf.cell(0, 10, f'Search Query: {query}', 0, 1)
    pdf.cell(0, 10, f'Total Results: {len(results)}', 0, 1)
    pdf.ln(10)

    pdf.set_font(pdf.font_family, 'B', 12)
    pdf.cell(0, 10, 'Results:', 0, 1)
    pdf.ln(5)

    pdf.set_font(pdf.font_family, '', 10)
    for i, result in enumerate(results, 1):
        pdf.cell(0, 6, f'{i}. {result["title"]} ({result["source"]})', 0, 1)
        pdf.cell(0, 6, f'   Description: {result["description"][:100]}', 0, 1)
        pdf.cell(0, 6, f'   URL: {result["url"]}', 0, 1)
        pdf.cell(0, 6, f'   Reputable: {"Yes" if result["reputable"] else "No"}', 0, 1)
        pdf.ln(3)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or '.', exist_ok=True)

    # Save PDF
    pdf.output(output_path)