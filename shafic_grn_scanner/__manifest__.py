# -*- coding: utf-8 -*-
{
    'name': 'Shafic GRN Scanner',
    'version': '19.0.1.2.0',
    'summary': 'Mobile scanner for goods receiving: scan product barcode, then '
               'read Batch/Expiry from the box by camera (on-device OCR), '
               'confirm, and post to the PO receipt.',
    'description': """
GRN Scanner
===========
A phone-friendly page (served by Odoo, same login, works on iPhone and Android)
for the inventory receiver:

1. Pick a pending receipt (auto-created from a confirmed Purchase Order).
2. Scan the product barcode -> matched against the receipt lines.
3. Point the camera at the printed Batch No. / Expiry Date on the box; the page
   reads them with on-device OCR (offline, free). The receiver confirms or
   corrects.
4. Add the quantity and submit -> move lines with lot + expiry are written to
   the receipt for the manager to review and validate in Odoo.

OCR runs in the browser (Tesseract.js). Because the page is served by Odoo it is
same-origin: the camera works over HTTPS and the data calls need no CORS.
""",
    'author': 'Shafic Retail',
    'license': 'LGPL-3',
    'category': 'Inventory',
    'depends': ['stock', 'purchase'],
    'data': [
        'views/grn_scanner_menu.xml',
    ],
    'installable': True,
    'application': True,
}
