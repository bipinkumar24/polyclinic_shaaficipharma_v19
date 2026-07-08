/** @odoo-module **/
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    // Belt-and-suspenders guard. A restored / offline order can briefly hold an
    // orphan pos.pack.operation.lot whose `pos_order_line_id` no longer resolves
    // (e.g. IndexedDB corrupted by an earlier build before the persistence fix in
    // data_service_options.js). Core's getter does
    // `l.pos_order_line_id.product_id.tracking` and crashes the Payment Screen /
    // customer display with
    // "Cannot read properties of undefined (reading 'product_id')".
    //
    // We reproduce core's output byte-for-byte for valid lots and simply skip any
    // dangling entry. This does NOT change the packLotLines data structure or
    // lifecycle — it only prevents the render crash. The actual root-cause fix
    // (never persisting orphan lots + purging existing ones) lives in
    // data_service_options.js; this is purely defensive for already-corrupted
    // client caches.
    get packLotLines() {
        return (this.pack_lot_ids ?? [])
            .filter((l) => l && l.pos_order_line_id?.product_id)
            .map(
                (l) =>
                    `${l.pos_order_line_id.product_id.tracking == "lot" ? "Lot Number" : "SN"} ${
                        l.lot_name
                    }`
            );
    },
});
