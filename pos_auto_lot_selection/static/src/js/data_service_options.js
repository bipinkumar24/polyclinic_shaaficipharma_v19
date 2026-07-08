/** @odoo-module **/
import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";
import { patch } from "@web/core/utils/patch";

patch(DataServiceOptions.prototype, {
    get databaseTable() {
        return {
            ...super.databaseTable,
            "pos.pack.operation.lot": {
                key: "id",
                condition: (record) =>
                    record.pos_order_line_id?.order_id?.canBeRemovedFromIndexedDB,
                getRecordsBasedOnLines: (orderlines) =>
                    orderlines.flatMap((line) => line.pack_lot_ids),
            },
        };
    },
});
