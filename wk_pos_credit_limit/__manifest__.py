#  -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2019-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE URL <https://store.webkul.com/license.html/> for full copyright and licensing details.
#################################################################################
{
    'name'                  :  "Pos Credit Limit",
    "summary"               :  "POS Credit Limit allows you to add a credit limit for your customers and manage credit functions such as hold, block, and several other criteria. Further, the module shows validation errors in the POS session based on credit limit configuration. Also, you can configure different limits and configurations for distinct customers. Credit Limit | Credit Limit in Odoo | POS Credit Limit | Credit Management in Odoo | Point of Sale Credit Limit | Credit Hold | POS Customer Credit Limit",
    "category"              :  "Point of Sale",
    "version"               :  "19.0.0.1",
    "sequence"              :  1,
    "author"                :  "Webkul Software Pvt. Ltd.",
    "license"               :  "Other proprietary",
    "website"               :  "https://store.webkul.com/odoo-pos-credit-limit.html",
    'description'           :  """
                                Odoo POS Credit Limit lets you configure a lending limit for customers individually. You can enable various configurations, like block, hold, etc., from the backend.
                                Odoo, Odoo POS, 
                                Odoo Admin,
                                Credit Limit, 
                                Credit Limit in Odoo, 
                                POS Credit Limit, 
                                Credit Management in Odoo, 
                                Point of Sale Credit Limit, 
                                Credit Hold, 
                                POS Customer Credit Limit
                              """,
    "live_test_url"         :  "http://odoodemo.webkul.com/?module=wk_pos_credit_limit&custom_url=/pos/auto",
    'depends'               :  ['point_of_sale'],
    'data'                  :  ['view/res_partner.xml'],
    "demo"                 :  [
                                'demo/demo.xml',
                            ],
    "assets"                :  {
                                  'point_of_sale._assets_pos': [
                                      'web/static/lib/jquery/jquery.js',
                                      'wk_pos_credit_limit/static/src/js/**/*',
                                      'wk_pos_credit_limit/static/src/xml/**/*',
                                  ],
                              },
    "images"                :  ['static/description/Banner.png'],
    "application"           :  True,
    "installable"           :  True,
    "auto_install"          :  False,
    "price"                 :  99,
    "currency"              :  "USD",
    "pre_init_hook"         :  "pre_init_check",
}