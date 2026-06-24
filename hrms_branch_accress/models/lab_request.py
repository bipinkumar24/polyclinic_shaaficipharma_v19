from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class LaboratoryRequest(models.Model):
	_inherit = 'acs.laboratory.request'

	@api.model
	def default_get(self, default_fields):
		res = super(LaboratoryRequest, self).default_get(default_fields)
		branch_id = False
		if self._context.get('branch_id'):
			branch_id = self._context.get('branch_id')
		elif self.env.user.branch_id:
			branch_id = self.env.user.branch_id.id

		if 'branch_id' in default_fields:
			res.update({'branch_id': branch_id})
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

	def button_in_progress(self):
		# Call parent logic first
		res = super().button_in_progress()

		for record in self:
			branch_id = record.branch_id.id if record.branch_id else False

			# Set branch on created Lab Tests
			if branch_id:
				record.line_ids.mapped('patient_lab_ids').write({
					'branch_id': branch_id
				})

				# Set branch on Consumables
				# record.line_ids.mapped('patient_lab_ids').mapped('consumable_line_ids').write({
				# 	'branch_id': branch_id
				# })

		return res
		
	def action_view_lab_samples(self):
		action = super().action_view_lab_samples()

		ctx = dict(action.get('context', {}))
		ctx.update({
			'branch_id': self.branch_id.id if self.branch_id else False
		})

		action['context'] = ctx
		return action

class PatientLabTest(models.Model):
	_inherit = 'patient.laboratory.test'

	@api.model
	def default_get(self, default_fields):
		res = super(PatientLabTest, self).default_get(default_fields)
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

class PatientLabSample(models.Model):
	_inherit = "acs.patient.laboratory.sample"

	@api.model
	def default_get(self, default_fields):
		res = super(PatientLabSample, self).default_get(default_fields)
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

