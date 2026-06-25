/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useBarcodeReader } from "@point_of_sale/app/hooks/barcode_reader_hook";

patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        // A prescription QR carries a bare order number that matches no product
        // nomenclature rule, so it arrives as an "error" (unrecognised) scan.
        // Try to resolve it as a prescription before falling back to the
        // standard unknown-barcode notice.
        useBarcodeReader({
            error: (parsed) => this.pos.shaficScanRx(parsed),
        });
    },
});
