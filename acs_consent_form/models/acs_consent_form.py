# -*- encoding: utf-8 -*-

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError

class AcsConsentFormTags(models.Model):
    _name = "acs.consent.form.tag"
    _description = "Document Tags"

    name = fields.Char('Name', required=True, translate=True)
    color = fields.Integer('Color Index')

    _name_uniq = models.Constraint('unique (name)', "Tag name already exists !")


class AcsConsentForm(models.Model):
    _name = 'acs.consent.form'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = 'Consent Form'
    _order = "id desc"

    name = fields.Char(string='Name', required=True, readonly=True, default='New', copy=False)
    subject = fields.Char(string='Subject', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete="restrict", 
        help="Partner to whom Document assigned")
    user_id = fields.Many2one('res.users', string='User', ondelete="restrict", 
        help="User who provided Document")
    date = fields.Date('Date', default=fields.Date.today)
    consent_form_content = fields.Html('Consent Form Content')
    state = fields.Selection([
        ('draft','Draft'),
        ('tosign','To Sign'),
        ('signed','Signed')
    ], 'Status', default="draft", tracking=1) 
    template_id = fields.Many2one('acs.consent.form.template', string="Template", ondelete="restrict")
    tag_ids = fields.Many2many('acs.consent.form.tag', 'ditial_document_tag_rel', 'consent_form_id', 'tag_id', 
        string='Tags', help="Classify and analyze your Consent Forms")
    print_header_in_report = fields.Boolean(string="Print Header")
    company_id = fields.Many2one('res.company', ondelete='restrict', 
        string='Company', default=lambda self: self.env.company)

    acs_signed_on = fields.Datetime("Signed On", copy=False)
    acs_signature = fields.Binary("Signature", copy=False)
    acs_has_to_be_signed = fields.Boolean("Tobe Signed", default=True, copy=False)
    acs_access_url = fields.Char(compute="get_acs_access_url", string='Portal Access Link')

    def get_acs_access_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if not rec.access_token:
                rec._portal_ensure_token()
            rec.acs_access_url = '%s/my/consentforms/%s?access_token=%s' % (base_url, rec.id, rec.access_token)

    def action_to_sign(self):
        self.name = self.env['ir.sequence'].next_by_code('acs.consent.form')
        self.state = 'tosign'

    def get_subject(self):
        subject = _('Your Consent Form')
        if self.state == 'signed':
            subject = _('Your Signed Consent Form')
        return subject

    def action_signed(self):
        self.state = 'signed'
        if self.partner_id.email:
            template = self.env.ref('acs_consent_form.acs_consent_form_email')
            template.sudo().send_mail(self.id, raise_exception=False)
    
    def action_reset_to_draft(self):
        self.state = 'draft'

    def apply_template(self):
        for rec in self:
            rendered = self.env['mail.render.mixin']._render_template(rec.template_id.consent_form_content, self._name, [rec.id])
            rec.consent_form_content = rendered[rec.id]

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for record in res:
            record._portal_ensure_token()
        return res

    def unlink(self):
        for data in self:
            if data.state!='draft':
                raise UserError(('Record Can be deleted in draft state only.'))
        return super(AcsConsentForm, self).unlink()

    def get_portal_sign_url(self):
        return "/my/consentform/%s/sign?access_token=%s" % (self.id, self.access_token)

    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s' % (self.name)

    def preview_consent_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': "/my/consentforms/%s" % (self.id),
        }

    def _get_portal_return_action(self):
        """ Return the action used to display record when returning from customer portal. """
        self.ensure_one()
        return self.env.ref('acs_consent_form.action_acs_consent_form')

    def action_send_by_mail(self):
        '''
        This function opens a window to compose an email, with the template message loaded by default
        '''
        self.ensure_one()
        template_id = self.env['ir.model.data']._xmlid_to_res_id('acs_consent_form.acs_consent_form_email', raise_if_not_found=False)

        ctx = {
            'default_model': 'acs.consent.form',
            'default_res_ids': self.ids,
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'force_email': True
        }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }


class AcsConsentFormTemplate(models.Model):
    _name = 'acs.consent.form.template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Consent Form Template'

    name = fields.Char("Template")
    consent_form_content = fields.Html('Consent Form Content')
    active = fields.Boolean(string="Active", default=True)


class Partner(models.Model):
    _inherit = 'res.partner' 

    def get_acs_consent_form_count(self):
        for rec in self:
            rec.acs_consent_form_count = len(rec.sudo().acs_consent_form_ids)

    acs_consent_form_ids = fields.One2many('acs.consent.form', 'partner_id', string='Consent Forms')
    acs_consent_form_count = fields.Integer(compute='get_acs_consent_form_count', string='# Consent Forms')

    def action_open_consent_form(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_consent_form.action_acs_consent_form")
        action['domain'] = [('partner_id','=',self.id)]
        action['context'] = {'default_partner_id': self.id}
        return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: