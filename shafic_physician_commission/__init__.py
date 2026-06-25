# -*- coding: utf-8 -*-
from . import models


def _post_init_seed_rates(env):
    """Seed the two known rates by name match; safe no-op if not found.
    Admins can adjust or add others under Physician Commission > Rates."""
    Phys = env['hms.physician']
    Rate = env['physician.commission.rate']
    for key, pct in [('kaahiye', 25.0), ('ifrah', 10.0)]:
        phys = Phys.search([('name', 'ilike', key)], limit=1)
        if phys and not Rate.search([('physician_id', '=', phys.id)],
                                    limit=1):
            Rate.create({'physician_id': phys.id,
                         'commission_percent': pct})
