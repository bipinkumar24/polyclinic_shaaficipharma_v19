import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";
import { patch } from "@web/core/utils/patch";

patch(DataServiceOptions.prototype, {
    get databaseTable() {
        console.log("here is issue");
        return {
            ...super.databaseTable,
            "prescription.order": {
                key: "id",
                condition: (record) => {
                    return record.models["pos.order.line"].find(
                        (l) => l.prescription_order_origin_id?.id === record.id
                    );
                },
            },
            "prescription.line": {
                key: "id",
                condition: (record) => {
                    return record.models["pos.order.line"].find(
                        (l) => l.prescription_order_line_id?.id === record.id
                    );
                },
            },
        };
    },
});
