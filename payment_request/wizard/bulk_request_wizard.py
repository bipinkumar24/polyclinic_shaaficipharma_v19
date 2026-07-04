from odoo import api, fields, models, _
from odoo.exceptions import UserError


ADVANCE_MONTH_SEL = [
    ('01', 'January'), ('02', 'February'), ('03', 'March'),
    ('04', 'April'), ('05', 'May'), ('06', 'June'),
    ('07', 'July'), ('08', 'August'), ('09', 'September'),
    ('10', 'October'), ('11', 'November'), ('12', 'December'),
]


class BulkRequestWizardLine(models.TransientModel):
    """One line per employee in the bulk wizard."""
    _name = 'bulk.request.wizard.line'
    _description = 'Bulk Request Wizard Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    wizard_id = fields.Many2one(
        'bulk.request.wizard', required=True, ondelete='cascade',
    )
    include = fields.Boolean(string='Include', default=True)
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True,
        domain="[('company_id', '=', parent.company_id)]",
    )
    department_id = fields.Many2one(
        related='employee_id.department_id', string='Department',
        store=True, readonly=True,
    )

    # Advance-specific
    advance_amount = fields.Monetary(
        string='Advance Amount', currency_field='currency_id',
    )
    advance_percentage = fields.Float(string='% of Salary', digits=(5, 2))

    # Overtime-specific
    overtime_hours = fields.Float(string='Hours')
    overtime_rate = fields.Float(string='Rate/hr', digits=(10, 2))
    overtime_amount = fields.Monetary(
        string='OT Amount', currency_field='currency_id',
        compute='_compute_overtime_amount', store=True,
    )

    currency_id = fields.Many2one(
        related='wizard_id.currency_id', readonly=True,
    )
    description = fields.Char(string='Note / Reason')
    status = fields.Char(string='Result', readonly=True)

    @api.depends('overtime_hours', 'overtime_rate')
    def _compute_overtime_amount(self):
        for line in self:
            line.overtime_amount = (line.overtime_hours or 0.0) * (line.overtime_rate or 0.0)

    @api.onchange('wizard_id', 'employee_id')
    def _onchange_apply_defaults(self):
        """Copy wizard-level defaults onto the line."""
        if not self.wizard_id:
            return
        w = self.wizard_id
        if w.request_type == 'advance':
            if w.default_advance_percentage and not self.advance_percentage:
                self.advance_percentage = w.default_advance_percentage
        elif w.request_type == 'overtime':
            if w.default_overtime_rate and not self.overtime_rate:
                self.overtime_rate = w.default_overtime_rate
            if w.default_overtime_hours and not self.overtime_hours:
                self.overtime_hours = w.default_overtime_hours


class BulkRequestWizard(models.TransientModel):
    """Wizard to create multiple advance or overtime requests at once."""
    _name = 'bulk.request.wizard'
    _description = 'Bulk Payment Request Wizard'

    request_type = fields.Selection(
        [('advance', 'Salary Advance'), ('overtime', 'Overtime')],
        string='Request Type', required=True, default='advance',
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True,
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id, required=True,
    )
    description = fields.Text(
        string='Global Justification',
        required=True,
        placeholder='Shared reason applied to all requests (can be overridden per line)...',
    )
    date_request = fields.Date(
        string='Request Date', required=True,
        default=fields.Date.today,
    )

    # Advance defaults
    advance_month = fields.Selection(ADVANCE_MONTH_SEL, string='Advance Month')
    advance_year = fields.Integer(
        string='Advance Year',
        default=lambda self: fields.Date.today().year,
    )
    default_advance_percentage = fields.Float(
        string='Default % of Salary', digits=(5, 2),
        help='Pre-filled on all lines; edit per employee if needed.',
    )

    # Overtime defaults
    overtime_date = fields.Date(string='Overtime Work Date')
    default_overtime_hours = fields.Float(
        string='Default Hours',
        help='Pre-filled on all lines; edit per employee if needed.',
    )
    default_overtime_rate = fields.Float(
        string='Default Rate/hr', digits=(10, 2),
        help='Pre-filled on all lines; edit per employee if needed.',
    )

    # Filter helpers
    filter_department_id = fields.Many2one(
        'hr.department', string='Filter by Department',
        help='Load employees from this department.',
    )
    auto_submit = fields.Boolean(
        string='Auto-submit after creation',
        default=False,
        help='If checked, all created requests are immediately submitted for manager review.',
    )

    line_ids = fields.One2many(
        'bulk.request.wizard.line', 'wizard_id', string='Employees',
    )

    # Summary stats
    total_lines = fields.Integer(compute='_compute_summary', string='Employees')
    total_included = fields.Integer(compute='_compute_summary', string='Included')
    total_amount = fields.Monetary(
        compute='_compute_summary', string='Total Amount',
        currency_field='currency_id',
    )

    @api.depends('line_ids', 'line_ids.include',
                 'line_ids.advance_amount', 'line_ids.overtime_amount')
    def _compute_summary(self):
        for wiz in self:
            lines = wiz.line_ids
            included = lines.filtered('include')
            wiz.total_lines = len(lines)
            wiz.total_included = len(included)
            if wiz.request_type == 'advance':
                wiz.total_amount = sum(included.mapped('advance_amount'))
            else:
                wiz.total_amount = sum(included.mapped('overtime_amount'))

    @api.onchange('request_type')
    def _onchange_request_type(self):
        self.line_ids = [(5, 0, 0)]

    @api.onchange('default_overtime_rate', 'default_overtime_hours')
    def _onchange_ot_defaults(self):
        for line in self.line_ids:
            if self.default_overtime_rate and not line.overtime_rate:
                line.overtime_rate = self.default_overtime_rate
            if self.default_overtime_hours and not line.overtime_hours:
                line.overtime_hours = self.default_overtime_hours

    @api.onchange('default_advance_percentage')
    def _onchange_advance_pct(self):
        for line in self.line_ids:
            if self.default_advance_percentage and not line.advance_percentage:
                line.advance_percentage = self.default_advance_percentage

    def action_load_employees(self):
        """Load employees into lines based on department filter."""
        self.ensure_one()
        domain = [('active', '=', True), ('company_id', '=', self.company_id.id)]
        if self.filter_department_id:
            domain.append(('department_id', '=', self.filter_department_id.id))

        employees = self.env['hr.employee'].search(domain, order='name')
        if not employees:
            raise UserError(_('No active employees found for the selected filter.'))

        # Keep existing lines that are already filled in
        existing_emp_ids = self.line_ids.mapped('employee_id').ids
        new_lines = []
        for emp in employees:
            if emp.id in existing_emp_ids:
                continue
            line_vals = {
                'employee_id': emp.id,
                'include': True,
                'sequence': 10,
            }
            if self.request_type == 'advance':
                line_vals['advance_percentage'] = self.default_advance_percentage or 0.0
            else:
                line_vals['overtime_rate'] = self.default_overtime_rate or 0.0
                line_vals['overtime_hours'] = self.default_overtime_hours or 0.0
            new_lines.append((0, 0, line_vals))

        self.line_ids = list(self.line_ids._origin) and \
            [(4, l.id) for l in self.line_ids] + new_lines or new_lines
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bulk.request.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_clear_lines(self):
        self.ensure_one()
        self.line_ids = [(5, 0, 0)]
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bulk.request.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_select_all(self):
        self.line_ids.write({'include': True})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bulk.request.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_deselect_all(self):
        self.line_ids.write({'include': False})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bulk.request.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_create_requests(self):
        """Create one payment.request per included line."""
        self.ensure_one()
        included = self.line_ids.filtered('include')
        if not included:
            raise UserError(_('Please include at least one employee.'))

        if self.request_type == 'advance':
            if not self.advance_month:
                raise UserError(_('Please select the advance month.'))
            for line in included:
                if not line.advance_amount and not line.advance_percentage:
                    raise UserError(
                        _('Employee %s: please enter an advance amount or percentage.')
                        % line.employee_id.name
                    )
        elif self.request_type == 'overtime':
            if not self.overtime_date:
                raise UserError(_('Please set the overtime work date.'))
            for line in included:
                if not line.overtime_hours or not line.overtime_rate:
                    raise UserError(
                        _('Employee %s: please set overtime hours and rate.')
                        % line.employee_id.name
                    )

        created = self.env['payment.request']
        sequence = self.env['ir.sequence']

        for line in included:
            if self.request_type == 'advance':
                amount = line.advance_amount or 0.0
                note = line.description or self.description
                vals = {
                    'name': sequence.next_by_code('payment.request') or _('New'),
                    'request_type': 'advance',
                    'employee_id': line.employee_id.id,
                    'date_request': self.date_request,
                    'description': note,
                    'amount_requested': amount,
                    'amount_approved': amount,
                    'advance_month': self.advance_month,
                    'advance_year': self.advance_year,
                    'advance_percentage': line.advance_percentage,
                    'currency_id': self.currency_id.id,
                    'company_id': self.company_id.id,
                    'state': 'draft',
                }
            else:
                amount = line.overtime_amount or 0.0
                note = line.description or self.description
                vals = {
                    'name': sequence.next_by_code('payment.request') or _('New'),
                    'request_type': 'overtime',
                    'employee_id': line.employee_id.id,
                    'date_request': self.date_request,
                    'description': note,
                    'amount_requested': amount,
                    'amount_approved': amount,
                    'overtime_date': self.overtime_date,
                    'overtime_hours': line.overtime_hours,
                    'overtime_rate': line.overtime_rate,
                    'currency_id': self.currency_id.id,
                    'company_id': self.company_id.id,
                    'state': 'draft',
                }

            # Resolve partner
            emp = line.employee_id
            if emp.user_id and emp.user_id.partner_id:
                vals['partner_id'] = emp.user_id.partner_id.id

            req = self.env['payment.request'].create(vals)

            if self.auto_submit:
                try:
                    req.action_submit()
                    line.status = _('Created & Submitted')
                except Exception as e:
                    line.status = _('Created (submit failed: %s)') % str(e)[:60]
            else:
                line.status = _('Created: %s') % req.name

            created |= req

        # Show result
        type_label = 'Salary Advance' if self.request_type == 'advance' else 'Overtime'
        return {
            'type': 'ir.actions.act_window',
            'name': _('%d %s Requests Created') % (len(created), type_label),
            'res_model': 'payment.request',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created.ids)],
            'target': 'current',
        }
