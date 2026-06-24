/** @almightycs-module **/

import { whenReady } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
    
whenReady(() => {

    // Activate popover
    $(function () {
        $('[data-toggle="popover"]').popover({
            html: true,
            sanitize: false
        })
    })

    //close on focus
    $('.popover-dismiss').popover({
        trigger: 'focus'
    })

    $("#AcsProcedureRecordSearch").on('keyup', function() {
        var input, filter, records, rec, i, txtValue;
        input = document.getElementById("AcsProcedureRecordSearch");
        filter = input.value.toUpperCase();
        records = document.getElementsByClassName("acs_dental_procedure");
        for (i = 0; i < records.length; i++) {
            rec = records[i].getElementsByClassName("acs_procedure_label")[0];
            txtValue = rec.textContent || rec.innerText;
            if (txtValue.toUpperCase().indexOf(filter) > -1) {
                records[i].style.display = "";
            } else {
                records[i].style.display = "none";
            }
        }
    });

    $('.acs_procedure_note_submit').click(function (event) {
        const $form = $(this).closest('form');
        const procedure_id = parseInt($form.find('input[name="procedure_id"]').val());
        const notes = $form.find('input[name="notes"]').val();
        rpc('/acs/procedure/notes',  {
            'procedure_id': procedure_id,
            'notes': notes
        }).then(function (data) {
            if (data && data.success) {
                location.reload();
            } else {
                alert('Failed to save notes. Please try again.');
            }
        });
    });

});