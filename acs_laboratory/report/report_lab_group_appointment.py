from odoo import models

class ReportLabTestGrouped(models.AbstractModel):
    _name = 'report.acs_laboratory.report_acs_lab_test_all'
    _description = 'Lab Report Grouped by Appointment'

    def _get_report_values(self, docids, data=None):

        docs = self.env['patient.laboratory.test'].browse(docids)

        appointment_map = {}

        for test in docs:
            appointment = test.appointment_id
            appointment_map.setdefault(appointment, []).append(test)

        grouped_docs = [
            {'appointment': appointment, 'tests': tests}
            for appointment, tests in appointment_map.items()
        ]

        return {
            'grouped_docs': grouped_docs
        }
