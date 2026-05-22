"""Generate a text-based sample invoice PDF for testing."""

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

INVOICE_TEXT = """PDF Invoice

Invoice #: INV-2024-001
Vendor: Acme Corp
Date: 2024-01-15
Currency: USD

Line Items:
  - Web Hosting Services   $500.00
  - SSL Certificate         $50.00
  - Support (5hrs @ $30)   $150.00

Subtotal: $700.00
Tax (10%):  $70.00
Total:     $770.00
"""


def main():
    output = Path(__file__).resolve().parent.parent / 'samples' / 'invoice_acme.pdf'
    output.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(output), pagesize=letter)
    width, height = letter
    y = height - 72

    for line in INVOICE_TEXT.strip().split('\n'):
        c.drawString(72, y, line)
        y -= 16

    c.save()
    print(f'Created {output}')


if __name__ == '__main__':
    main()
