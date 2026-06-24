# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ResUsers(models.Model):
    _inherit = "res.users"

    acs_warehouse_id = fields.Many2one('stock.warehouse', 'Default Picking Warehouse', copy=False)
    acs_picking_type_id = fields.Many2one('stock.picking.type', 'Default Picking Type', copy=False)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['acs_warehouse_id', 'acs_picking_type_id']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['acs_warehouse_id', 'acs_picking_type_id']


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    acs_account_move_line_id = fields.Many2one('account.move.line', help="Technical field to set lot properly for auto picking.")


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    tracking = fields.Selection(related='product_id.tracking', store=True)
    acs_lot_id = fields.Many2one("stock.lot", string="Batch Number",
        domain="[('product_id', '=', product_id),('product_qty','>',0),'|',('expiration_date','=',False),('expiration_date', '>', context_today().strftime('%Y-%m-%d'))]")
    exp_date = fields.Datetime(string="Expiry Date")

    @api.onchange('quantity', 'acs_lot_id')
    def onchange_batch(self):
        if self.acs_lot_id and self.move_id.move_type=='out_invoice':
            if self.acs_lot_id.product_qty < self.quantity:
                batch_product_qty = self.acs_lot_id.product_qty
                self.acs_lot_id = False
                warning = {
                    'title': "Warning",
                    'message': _("Selected Lot do not have enough qty. %s qty needed and lot have only %s" %(self.quantity,batch_product_qty)),
                }
                return {'warning': warning}

            self.exp_date = self.acs_lot_id.use_date


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _get_default_warehouse(self):
        acs_warehouse_id = self.env.user.sudo().acs_warehouse_id
        warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        return acs_warehouse_id or warehouse_id

    @api.model
    def _get_default_picking_type(self):
        return self.env.user.sudo().acs_picking_type_id or False

    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', default=_get_default_warehouse)
    create_stock_moves = fields.Boolean("Create Stock Moves?", copy=False)
    picking_id = fields.Many2one('stock.picking', 'Picking', copy=False)
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type', copy=False, default=_get_default_picking_type)
    acs_location_id = fields.Many2one('stock.location', 'Src Location', copy=False)
    acs_location_dest_id = fields.Many2one('stock.location', 'Destination Location', copy=False)

    @api.onchange('warehouse_id','move_type','create_stock_moves')
    def onchange_warehouse(self):
        if self.warehouse_id:
            default_acs_picking_type_id = self.env.user.sudo().acs_picking_type_id
            default_acs_picking_type_code = default_acs_picking_type_id and default_acs_picking_type_id.code or ''
            if self.move_type in ['out_invoice','in_refund']:
                self.picking_type_id = default_acs_picking_type_id if default_acs_picking_type_code=='outgoing' else self.warehouse_id.out_type_id.id

            elif self.move_type in ['in_invoice','out_refund']:
                self.picking_type_id = default_acs_picking_type_id if default_acs_picking_type_code=='incoming' else self.warehouse_id.in_type_id.id
            
    @api.onchange('picking_type_id','move_type','create_stock_moves')
    def onchange_picking_type(self):
        if self.warehouse_id:
            default_location_src_id = self.picking_type_id.default_location_src_id and self.picking_type_id.default_location_src_id.id
            default_location_dest_id = self.picking_type_id.default_location_dest_id and self.picking_type_id.default_location_dest_id.id

            if self.move_type == 'out_invoice':
                self.acs_location_id = default_location_src_id or self.warehouse_id.lot_stock_id.id
                self.acs_location_dest_id = default_location_dest_id or self.partner_id.property_stock_customer.id

            elif self.move_type == 'in_invoice':
                self.acs_location_id = default_location_src_id or self.partner_id.property_stock_supplier.id
                self.acs_location_dest_id = default_location_dest_id or self.warehouse_id.lot_stock_id.id

            elif self.move_type == 'out_refund':
                self.acs_location_id =  default_location_src_id or self.partner_id.property_stock_customer.id
                self.acs_location_dest_id = default_location_dest_id or self.warehouse_id.lot_stock_id.id

            elif self.move_type == 'in_refund':
                self.acs_location_id =  default_location_src_id or self.warehouse_id.lot_stock_id.id
                self.acs_location_dest_id = default_location_dest_id or self.partner_id.property_stock_supplier.id

    def acs_check_picking_possibility(self):
        create_picking = False
        if any(inv_line.product_id and inv_line.product_id.type in ['consu','product'] for inv_line in self.invoice_line_ids):
            create_picking = True
        return create_picking

    @api.model
    def move_line_from_invoice_lines(self, picking, location_id, location_dest_id):
        StockMoveL = self.env['stock.move.line']
        for line in self.invoice_line_ids:
            if line.product_id and line.product_id.type!='service':
                StockMoveL.with_context(default_immediate_transfer=True).create({
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'date': fields.datetime.now(),                    
                    'picking_id': picking.id,
                    'picking_type_id': picking.picking_type_id.id,
                    'state': 'assigned',
                    'location_id': location_id.id,
                    'location_dest_id': location_dest_id.id,
                    'lot_id': line.acs_lot_id and line.acs_lot_id.id or False, 
                    'lot_name': line.acs_lot_id and line.acs_lot_id.name or '', 
                    'acs_account_move_line_id': line.id, 
                    'quantity': line.quantity,
                    'company_id': picking.company_id.id,
                    'package_level_id': False,
                })

    @api.model
    def acs_create_picking(self, picking_type_id, location_id, location_dest_id):
        picking_id = self.env['stock.picking'].with_context(default_immediate_transfer=True).create({
            'partner_id': self.partner_id.id,
            'date': fields.datetime.now(), 
            'company_id': self.company_id.id,
            'picking_type_id': picking_type_id.id,
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
            'move_type': 'direct',
            'origin': self.name,
        })
        self.picking_id = picking_id.id
        self.move_line_from_invoice_lines(picking_id, location_id, location_dest_id)
        picking_id.button_validate()

    def action_post(self):
        res = super(AccountMove, self).action_post()
        for inv in self:
            if inv.create_stock_moves and inv.acs_check_picking_possibility():
                if (not inv.picking_type_id) or (not inv.acs_location_id) or (not inv.acs_location_dest_id):
                    inv.onchange_warehouse()
                if inv.picking_type_id and inv.acs_location_id and inv.acs_location_dest_id:
                    inv.acs_create_picking(inv.picking_type_id, inv.acs_location_id, inv.acs_location_dest_id)
        return res

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        if self.picking_id:
            self.picking_id.action_cancel()


class StockLot(models.Model):
    _inherit = 'stock.lot'
 
    product_qty = fields.Float(search="_search_product_qty")

    #canbe used for filtering lots in selection on procedures and consumed products
    def _search_product_qty(self, operator, value):
        valid_record = []
        product_id = self._context.get('acs_product_id',False)
        domain =[('product_id','=',product_id)]
        if self._context.get('acs_all_products',False):
            domain =[]
        production_lots = self.search(domain)
        for production_lot in production_lots:
            if operator == '>' and production_lot.product_qty > value:
                valid_record.append(production_lot.id)
        return [('id', 'in', valid_record)]

