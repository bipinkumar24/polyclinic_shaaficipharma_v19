from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class HmsAppointment(models.Model):
	_inherit = 'hms.appointment'

	@api.model
	def default_get(self, default_fields):
		res = super(HmsAppointment, self).default_get(default_fields)
		if self.env.user.branch_id and 'branch_id' in default_fields:
			res.update({
				'branch_id': self.env.user.branch_id.id or False
			})
		return res

	branch_id = fields.Many2one('res.branch')

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

	def action_radiology_request(self):
		action = super().action_radiology_request()
		ctx = dict(action.get('context', {}))
		ctx.update({
			'branch_id': self.branch_id.id if self.branch_id else False
		})

		action['context'] = ctx
		return action

	def button_pres_req(self):
		action = super().button_pres_req()
		ctx = dict(action.get('context', {}))
		ctx.update({
			'branch_id': self.branch_id.id if self.branch_id else False
		})
		action['context'] = ctx
		return action

	def action_lab_request(self):
		action = super().action_lab_request()
		ctx = dict(action.get('context', {}))
		ctx.update({
			'branch_id': self.branch_id.id if self.branch_id else False
			})
		action['context'] = ctx
		return action