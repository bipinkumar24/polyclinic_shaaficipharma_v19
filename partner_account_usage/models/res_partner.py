from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_used_in_accounting = fields.Boolean(
        string="Used In Accounting",
        default=False,
        index=True
    )

    def cron_update_partner_account_usage(self):
        """
        Update partner usage in accounting and hms.patient
        """

        # Reset all
        self.env.cr.execute("""
            UPDATE res_partner
            SET is_used_in_accounting = FALSE
        """)

        # Used in account_move
        self.env.cr.execute("""
            UPDATE res_partner p
            SET is_used_in_accounting = TRUE
            FROM account_move am
            WHERE am.partner_id = p.id
        """)

        # Used in account_move_line
        self.env.cr.execute("""
            UPDATE res_partner p
            SET is_used_in_accounting = TRUE
            FROM account_move_line aml
            WHERE aml.partner_id = p.id
        """)

        # 🔥 Used in HMS Patient
        self.env.cr.execute("""
            UPDATE res_partner p
            SET is_used_in_accounting = TRUE
            FROM hms_patient hp
            WHERE hp.partner_id = p.id
        """)

        self.env.cr.commit()
