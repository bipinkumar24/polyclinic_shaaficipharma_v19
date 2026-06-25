# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def default_get(self, default_fields):
        res = super(StockQuant, self).default_get(default_fields)
        if 'branch_id' in default_fields:
            if self.env.user.branch_id:
                res.update({
                    'branch_id' : self.env.user.branch_id.id or False
                })
        return res

    branch_id = fields.Many2one('res.branch', string="Branch")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not self.env.context.get('branch'):
                vals.update({'branch_id':self.env.user.branch_id.id})
        return super(StockQuant, self).create(vals_list)

    def write(self, vals):
        user = self.env.user

        if 'branch_id' in vals:
            new_branch_id = vals.get('branch_id')

            for record in self:
                if user.has_group('branch.group_multi_branch'):
                    allowed_branch_ids = self.env.context.get('allowed_branch_ids', [])
                    if new_branch_id not in allowed_branch_ids:
                        raise UserError(_(
                            "You can only assign a branch that is within your allowed branches.\n\n"
                            "Please select a valid branch."
                        ))
                else:
                    if new_branch_id != user.branch_id.id:
                        raise UserError(_(
                            "You are not allowed to assign a different branch.\n\n"
                            "Please use your assigned branch or contact the administrator."
                        ))

        return super(StockQuant, self).write(vals)
    
    @api.model
    def _get_inventory_fields_create(self):
        res = super(StockQuant, self)._get_inventory_fields_create()
        res.append('branch_id')
        return res


    @api.model
    def _get_inventory_fields_write(self):
        res = super(StockQuant, self)._get_inventory_fields_write()
        res.append('branch_id')
        return res

    @api.onchange('branch_id')
    def _onchange_branch_id(self): 
        selected_branch = self.branch_id
        user = self.env.user 
        if selected_branch: 
            if user.has_group('branch.group_multi_branch'):
                allowed_branch_ids = self.env.context.get('allowed_branch_ids', [])
                if selected_branch.id not in allowed_branch_ids:
                    raise UserError(_(
                        "Please select an active branch only. Other branches may cause data inconsistency.\n\n"
                        "If you wish to work in another branch, switch to it using the top-right menu."
                    ))
            else: 
                if selected_branch != user.branch_id:
                    raise UserError(_(
                        "You are not allowed to switch branches.\n\n"
                        "Please use your assigned branch or contact an administrator."
                    ))



    def action_apply_inventory(self):
        res = super(StockQuant, self).action_apply_inventory()
        for quant in self:
            if not self.env.context.get('branch'):
                quant.branch_id = self.env.user.branch_id.id or False
        return res


    @api.model
    def _update_available_quantity(self, product_id, location_id, quantity=False, reserved_quantity=False, lot_id=None, package_id=None, owner_id=None, in_date=None):
        """ Increase or decrease `quantity` or 'reserved quantity' of a set of quants for a given set of
        product_id/location_id/lot_id/package_id/owner_id.

        :param product_id:
        :param location_id:
        :param quantity:
        :param lot_id:
        :param package_id:
        :param owner_id:
        :param datetime in_date: Should only be passed when calls to this method are done in
                                 order to move a quant. When creating a tracked quant, the
                                 current datetime will be used.
        :return: tuple (available_quantity, in_date as a datetime)
        """
        if not (quantity or reserved_quantity):
            raise ValidationError(_('Quantity or Reserved Quantity should be set.'))
        self = self.sudo()
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True)
        if lot_id and quantity > 0:
            quants = quants.filtered(lambda q: q.lot_id)

        if location_id.should_bypass_reservation():
            incoming_dates = []
        else:
            incoming_dates = [quant.in_date for quant in quants if quant.in_date and
                              float_compare(quant.quantity, 0, precision_rounding=quant.product_uom_id.rounding) > 0]
        if in_date:
            incoming_dates += [in_date]
        # If multiple incoming dates are available for a given lot_id/package_id/owner_id, we
        # consider only the oldest one as being relevant.
        if incoming_dates:
            in_date = min(incoming_dates)
        else:
            in_date = fields.Datetime.now()

        quant = None
        if quants:
            # see _acquire_one_job for explanations
            self._cr.execute("SELECT id FROM stock_quant WHERE id IN %s ORDER BY lot_id LIMIT 1 FOR NO KEY UPDATE SKIP LOCKED", [tuple(quants.ids)])
            stock_quant_result = self._cr.fetchone()
            if stock_quant_result:
                quant = self.browse(stock_quant_result[0])
        
        if self.env.context.get('branch'):
            if quant:
                vals = {'in_date': in_date,'branch_id':self.env.context.get('branch')}
                if quantity:
                    vals['quantity'] = quant.quantity + quantity
                if reserved_quantity:
                    vals['reserved_quantity'] = quant.reserved_quantity + reserved_quantity
                quant.write(vals)
            else:
                vals = {
                    'product_id': product_id.id,
                    'location_id': location_id.id,
                    'lot_id': lot_id and lot_id.id,
                    'package_id': package_id and package_id.id,
                    'owner_id': owner_id and owner_id.id,
                    'in_date': in_date,
                    'branch_id':self.env.context.get('branch')
                }
                if quantity:
                    vals['quantity'] = quantity
                if reserved_quantity:
                    vals['reserved_quantity'] = reserved_quantity
                self.create(vals)
        else:
            if quant:
                vals = {'in_date': in_date}
                if quantity:
                    vals['quantity'] = quant.quantity + quantity
                if reserved_quantity:
                    vals['reserved_quantity'] = quant.reserved_quantity + reserved_quantity
                quant.write(vals)
            else:
                vals = {
                    'product_id': product_id.id,
                    'location_id': location_id.id,
                    'lot_id': lot_id and lot_id.id,
                    'package_id': package_id and package_id.id,
                    'owner_id': owner_id and owner_id.id,
                    'in_date': in_date,
                }
                if quantity:
                    vals['quantity'] = quantity
                if reserved_quantity:
                    vals['reserved_quantity'] = reserved_quantity
                self.create(vals)
        return self._get_available_quantity(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=False, allow_negative=True), in_date
