# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = 'res.users'

    HR_READABLE_FIELDS = [
        'active',
        'child_ids',
        'employee_id',
        'employee_ids',
        'employee_parent_id',
        'hr_presence_state',
        'last_activity',
        'last_activity_time',
        'can_edit',
        'is_system',
        'employee_resource_calendar_id',
        'work_contact_id',
    ]

    HR_WRITABLE_FIELDS = [
        'additional_note',
        'private_street',
        'private_street2',
        'private_city',
        'private_state_id',
        'private_zip',
        'private_country_id',
        'private_phone',
        'private_email',
        'address_id',
        'barcode',
        'birthday',
        'category_ids',
        'children',
        'coach_id',
        'country_of_birth',
        'department_id',
        'display_name',
        'emergency_contact',
        'emergency_phone',
        'employee_bank_account_id',
        'employee_country_id',
        'gender',
        'identification_id',
        'ssnid',
        'job_title',
        'km_home_work',
        'marital',
        'mobile_phone',
        'employee_parent_id',
        'passport_id',
        'permit_no',
        'pin',
        'place_of_birth',
        'spouse_birthdate',
        'spouse_complete_name',
        'visa_expire',
        'visa_no',
        'work_email',
        'work_location_id',
        'work_phone',
        'certificate',
        'study_field',
        'study_school',
        'private_lang',
        'employee_type',
    ]
    
    branch_ids = fields.Many2many('res.branch', string="Allowed Branch")
    branch_id = fields.Many2one('res.branch', string= 'Branch')


    def write(self, values):
        if 'branch_id' in values or 'branch_ids' in values:
            self.env['ir.model.access'].call_cache_clearing_methods()
        user = super(ResUsers, self).write(values)
        return user

    @api.constrains('branch_id', 'branch_ids')
    def _check_branch_id(self):
        if self.branch_ids:
            if self.branch_id.id not in self.branch_ids.ids:
                raise UserError("Please select branch from the Allowed Branch.")


    @api.constrains('branch_id', 'branch_ids', 'active')
    def _check_branch(self):
        if self.env.context.get('params', {}).get('model') == 'res.users':
            for user in self.filtered(lambda u: u.active):
                if user.branch_id not in user.branch_ids:
                    raise ValidationError(
                        _('Branch %(branch_name)s is not in the allowed branches for user %(user_name)s (%(branch_allowed)s).',
                        branch_name=user.branch_id.name,
                        user_name=user.name,
                        branch_allowed=', '.join(user.mapped('branch_ids.name')))
                    )
    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['branch_ids', 'branch_id']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['branch_ids', 'branch_id']
