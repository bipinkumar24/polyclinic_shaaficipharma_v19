{
    'name': 'POS Customer Approval & Credit Limit',
    'version': '19.0.2.0.0',
    'category': 'Point of Sale',
    'summary': 'Control which customers appear in POS and enforce credit limits at payment',
    'description': """
        Odoo 18 compatible module.

        Features:
        ─────────
        1. Customer Allow in POS
           Set "Allow in POS" on a customer to make them visible in the POS
           customer list. Optionally use the Accountant approval workflow.

        2. Payment Method Credit Limit Flag
           Each payment method can be marked with "Check Customer Credit Limit".
           When enabled, POS checks the customer's POS Credit Limit at validate.

        3. Payment Screen Validation
           On order validation, if the selected payment method checks credit limits
           and the order total exceeds the customer's configured POS Credit Limit,
           the order is blocked with a clear error message.

        4. Back-office Approval Workflow (optional)
           When a credit limit is set on a customer, an approval request is created.
           The customer is visible in POS once an Accountant or above approves.
           Approval can be done from back-office or from inside the POS screen.
    """,
    'author': 'Salaam Investment Bank',
    'depends': ['point_of_sale', 'account', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/pos_customer_activation_views.xml',
        'views/pos_payment_method_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_customer_approval_v18/static/src/js/customer_approval_service.js',
            'pos_customer_approval_v18/static/src/js/partner_list_patch.js',
            'pos_customer_approval_v18/static/src/js/approve_customer_popup.js',
            'pos_customer_approval_v18/static/src/js/payment_screen_patch.js',
            'pos_customer_approval_v18/static/src/xml/approve_customer_popup.xml',
            'pos_customer_approval_v18/static/src/css/customer_approval.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
