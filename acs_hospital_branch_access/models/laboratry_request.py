#-*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.osv import expression


class AcsLaboratoryRequest(models.Model):
    _inherit = "acs.laboratory.request"

    based_on = fields.Selection([('cash', 'Cash'), ('credit', 'Credit')], string='Customer Type')
    laboratory_payment_id = fields.Many2one('account.payment', string="Laboratory Payment", copy=False)
    hide_customer_discount = fields.Boolean(
        compute="_compute_hide_customer_discount",
    )

    def _compute_hide_customer_discount(self):
        group_xml_id = "acs_hospital_branch_access.group_hide_discount_customer"
        for record in self:
            record.hide_customer_discount = self.env.user.has_group(group_xml_id)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        if not self.env.context.get('is_amazon_partner', True):
            domain = [('is_amz_customer', '=', False)] + list(domain)
        return super(ResPartner, self)._search(domain, offset, limit, order, access_rights_uid)

    def view_payment(self):
        self.ensure_one()
        if not self.laboratory_payment_id:
            return False

        return {
            'name': 'Payment',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'res_id': self.laboratory_payment_id.id,
            'target': 'current',
        }

    @api.model
    def _search(self, domain, *args, **kwargs):

        user = self.env.user

        LAB_GROUPS = [
            'acs_laboratory.group_hms_lab_sample_user',
            'acs_laboratory.group_hms_lab_user',
            'acs_laboratory.group_hms_lab_manager',
            'acs_laboratory.group_manage_collection_center',
        ]

        EXCLUDED_GROUPS = [
            'acs_hms_cashier.group_acs_cashier',
            'acs_hms.group_hms_doctor',
            'acs_hms.group_hms_jr_doctor',
        ]

        if (
            any(user.has_group(g) for g in LAB_GROUPS)
            and not any(user.has_group(g) for g in EXCLUDED_GROUPS)
        ):
            domain = expression.AND([
                domain,
                [('state', 'not in', ['draft', 'requested'])]
            ])

        return super()._search(domain, *args, **kwargs)

    def button_accept(self):
        company_id = self.sudo().company_id
        if not self.invoice_id:
            raise UserError(_('Invoice has not been created yet. Please create it first.'))
        if company_id.acs_laboratory_invoice_policy=='in_advance' and (not self.invoice_exempt):
            if not self.invoice_id:
                raise UserError(_('Invoice is not created yet.'))
            elif self.invoice_id and company_id.acs_check_laboratory_payment and self.payment_state not in ['in_payment','paid']:
                raise UserError(_('Invoice is not Paid yet.'))
        if self.sudo().company_id.acs_auto_create_lab_sample:
            self.create_sample()
        # if self.based_on == 'cash':
        #     view_id = self.env.ref('acs_hospital_branch_access.view_account_of_payment_register_form_lab_request').id
        #     wizard = self.env['account.payment.laboratry'].create({})
        #     wizard.set_default_values_lab_request(self)
        #     res = {'type': 'ir.actions.act_window',
        #            'name': _('Cashier Payment'),
        #            'res_model': 'account.payment.laboratry',
        #            'target': 'new',
        #            'view_mode': 'form',
        #            'views': [[view_id, 'form']],
        #            'res_id': wizard.id,
        #            }
        #     return res
        # else:
        self.state = 'accepted'


class AcsRadiologyRequest(models.Model):
    _inherit = "acs.radiology.request"

    based_on = fields.Selection([('cash', 'Cash'), ('credit', 'Credit')], string='Customer Type')
    radiology_payment_id = fields.Many2one('account.payment', string="Radiology Payment", copy=False)
    hide_customer_discount = fields.Boolean(
        compute="_compute_hide_customer_discount",
    )

    def _compute_hide_customer_discount(self):
        group_xml_id = "acs_hospital_branch_access.group_hide_discount_customer"
        for record in self:
            record.hide_customer_discount = self.env.user.has_group(group_xml_id)

    def view_payment(self):
        self.ensure_one()
        if not self.radiology_payment_id:
            return False

        return {
            'name': 'Payment',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'res_id': self.radiology_payment_id.id,
            'target': 'current',
        }

    @api.model
    def _search(self, domain, *args, **kwargs):

        user = self.env.user

        LAB_GROUPS = [
            'acs_radiology.group_hms_radiology_user',
            'acs_radiology.group_hms_radiology_manager',
        ]

        EXCLUDED_GROUPS = [
            'acs_hms_cashier.group_acs_cashier',
            'acs_hms.group_hms_doctor',
            'acs_hms.group_hms_jr_doctor',
        ]

        if (
            any(user.has_group(g) for g in LAB_GROUPS)
            and not any(user.has_group(g) for g in EXCLUDED_GROUPS)
        ):
            domain = expression.AND([
                domain,
                [('state', 'not in', ['draft', 'requested'])]
            ])

        return super()._search(domain, *args, **kwargs)


    def button_accept(self):
        company_id = self.sudo().company_id
        if not self.invoice_id:
            raise UserError(_('Invoice has not been created yet. Please create it first.'))
        if company_id.acs_radiology_invoice_policy=='in_advance':
            if not self.invoice_id:
                raise UserError(_('Invoice is not created yet.'))
            elif self.invoice_id and company_id.acs_check_radiology_payment and self.payment_state not in ['in_payment','paid']:
                raise UserError(_('Invoice is not Paid yet.'))
        # if self.based_on == 'cash':
        #     view_id = self.env.ref('acs_hospital_branch_access.view_account_of_payment_register_form_lab_request').id
        #     wizard = self.env['account.payment.laboratry'].create({})
        #     wizard.set_default_values_radiology_request(self)
        #     res = {'type': 'ir.actions.act_window',
        #            'name': _('Cashier Payment'),
        #            'res_model': 'account.payment.laboratry',
        #            'target': 'new',
        #            'view_mode': 'form',
        #            'views': [[view_id, 'form']],
        #            'res_id': wizard.id,
        #            }
        #     return res
        # else:
        self.state = 'accepted'


class AcsPatientProcedure(models.Model):
    _inherit="acs.patient.procedure"

    based_on = fields.Selection([('cash', 'Cash'), ('credit', 'Credit')], string='Customer Type')
    procedure_payment_id = fields.Many2one('account.payment', string="Procedure Payment", copy=False)

    def view_payment(self):
        self.ensure_one()
        if not self.procedure_payment_id:
            return False

        return {
            'name': 'Payment',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'res_id': self.procedure_payment_id.id,
            'target': 'current',
        }

    def button_accept(self):
        company_id = self.sudo().company_id
        if not self.invoice_id:
            raise UserError(_('Invoice has not been created yet. Please create it first.'))
        # if self.based_on == 'cash':
        #     view_id = self.env.ref('acs_hospital_branch_access.view_account_of_payment_register_form_lab_request').id
        #     wizard = self.env['account.payment.laboratry'].create({})
        #     wizard.set_default_values_procedure_request(self)
        #     res = {'type': 'ir.actions.act_window',
        #            'name': _('Cashier Payment'),
        #            'res_model': 'account.payment.laboratry',
        #            'target': 'new',
        #            'view_mode': 'form',
        #            'views': [[view_id, 'form']],
        #            'res_id': wizard.id,
        #            }
        #     return res
        # else:
        self.state = 'accepted'

class HMSPhysician(models.Model):
    _inherit = 'hms.physician'

    appointment_counter = fields.Integer(
        string="Appointment Counter",
        default=0
    )

    @api.model
    def create_daily_range_for_sequence(self):
        physicians = self.search([])  # 🔹 all physicians
        for physician in physicians:
            physician.appointment_counter = 0  # 🔥 reset daily
        return True

class HmsAppointment(models.Model):
    _inherit="hms.appointment"

    @api.model_create_multi
    def default_get(self, default_fields):
        res = super(HmsAppointment, self).default_get(default_fields)
        if 'branch_id' in default_fields:
            if self.env.user.branch_id:
                res.update({
                    'branch_id': self.env.user.branch_id.id or False
                })
        return res

    branch_id = fields.Many2one('res.branch', string="Branch")

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_branch = self.branch_id
        user = self.env.user
        if selected_branch:
            if user.has_group('branch.group_multi_branch'):
                allowed_branch_ids = self.env.context.get(
                    'allowed_branch_ids', [])
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


    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:

    #         branch = self.env['res.branch'].browse(
    #             vals.get('branch_id')
    #         )

    #         if not branch:
    #             raise UserError(_("Please select a branch first."))

    #         # 🔹 Main Appointment Number (Branch-wise)
    #         if vals.get('name', 'New') == 'New':
    #             if not branch.appointment_sequence_id:
    #                 raise UserError(_(
    #                     "No appointment sequence configured for branch %s."
    #                 ) % branch.name)

    #             vals['name'] = branch.appointment_sequence_id.next_by_id()

    #         # 🔹 Daily Number (Branch-wise + Daily Reset)
    #         if vals.get('daily_number', 'New') == 'New':
    #             if not branch.appointment_daily_sequence_id:
    #                 raise UserError(_(
    #                     "No daily appointment sequence configured for branch %s."
    #                 ) % branch.name)

    #             vals['daily_number'] = (
    #                 branch.appointment_daily_sequence_id.next_by_id()
    #             )

    #     return super().create(vals_list)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:

            # 🔹 Branch Logic (same as yours)
            branch = self.env['res.branch'].browse(vals.get('branch_id'))

            if not branch:
                raise UserError(_("Please select a branch first."))

            if vals.get('name', 'New') == 'New':
                print('1111111111111 branch', branch.appointment_sequence_id)
                if not branch.appointment_sequence_id:
                    raise UserError(_(
                        "No appointment sequence configured for branch %s."
                    ) % branch.name)

                vals['name'] = branch.appointment_sequence_id.next_by_id()

            # 🔥 Physician-based Counter Logic
            physician = self.env['hms.physician'].browse(vals.get('physician_id'))

            if not physician:
                raise UserError(_("Please select a physician first."))

            # increment counter
            physician.appointment_counter += 1

            # assign 3-digit value
            vals['daily_number'] = str(physician.appointment_counter).zfill(3)

        return super().create(vals_list)

class ResBranch(models.Model):
    _inherit = "res.branch"

    appointment_sequence_id = fields.Many2one(
        'ir.sequence',
        string="Appointment Sequence"
    )

    appointment_daily_sequence_id = fields.Many2one(
        'ir.sequence',
        string="Daily Appointment Sequence"
    )
