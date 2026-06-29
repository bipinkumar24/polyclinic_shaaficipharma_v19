# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
#
# Odoo 19 migration note
# ----------------------
# The base ``launch_replenishment`` was rewritten in Odoo 19 (it now uses
# ``stock.rule.run`` instead of the old ``procurement.group.run``). Rather than
# duplicating that logic we call ``super()`` and only tag the generated move with
# ``sh_in_replenshment`` (kept for backward compatibility / reporting).

from odoo import models


class ProductReplenishs(models.TransientModel):
    _inherit = 'product.replenish'

    def launch_replenishment(self):
        now = self.env.cr.now()
        res = super().launch_replenishment()
        move = self._get_record_to_notify(now)
        if move and move._name == 'stock.move':
            move.sh_in_replenshment = True
        return res
