# -*- coding: utf-8 -*-
{
    'name': 'Shafic Dental Scheduling',
    'version': '19.0.1.0.0',
    'summary': 'Dental appointment scheduling on top of acs_hms: chairs, '
               'double-booking prevention, visit-type durations and a '
               'chair/dentist Gantt board',
    'description': """
Shafic Dental Scheduling
========================
Extends the existing acs_hms appointment engine for dental operations
instead of replacing it. Dental visits remain ordinary hms.appointment
records, so they keep flowing into invoicing, physician commission and
the prescription worklist.

Adds:
* A 'Dental' department type and a starter Dental department.
* Dental chairs managed as appointment cabins (with archiving + ordering).
* Visit types (appointment purposes) with a default duration that
  auto-sets the appointment end time.
* Double-booking prevention: a dental appointment cannot overlap another
  appointment on the same dentist or the same chair (configurable per
  company).
* A Dental Schedule board with a Gantt grouped by chair (drag to
  reschedule) plus calendar and list views.
""",
    'author': 'Shafic',
    'category': 'Medical',
    'license': 'LGPL-3',
    'depends': ['acs_hms', 'web_gantt'],
    'data': [
        'views/appointment_cabin_views.xml',
        'views/appointment_purpose_views.xml',
        'views/hms_appointment_views.xml',
        'views/res_company_views.xml',
        'views/dental_menus.xml',
        'data/dental_data.xml',
    ],
    'installable': True,
    'application': True,
}
