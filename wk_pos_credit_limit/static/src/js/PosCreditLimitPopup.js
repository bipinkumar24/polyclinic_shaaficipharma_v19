/** @odoo-module */
/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class PosCreditLimitPopup extends Component {
    static components = { Dialog };
    static template = "wk_pos_credit_limit.PosCreditLimitPopup";
    static defaultProps = {
        title: '',
        message: '',
        partner: '',
    };
}