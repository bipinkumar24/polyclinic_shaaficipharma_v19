import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";

patch(PartnerList.prototype, {

    // ── Local (already-loaded) partner filtering ──────────────────────────
    getPartners() {
        const query = (this.state.query || "").trim().toLowerCase();

        const partners = this.pos.models["res.partner"]
            .getAll()
            .filter((p) => !p.hide_in_pos);

        if (!query) {
            return partners.slice(0, 1000);
        }

        return partners.filter((p) =>
            (p.searchString || "").toLowerCase().includes(query)
        );
    },

    // ── Remote "load more" search ─────────────────────────────────────────
    async getNewPartners() {
        const limit = 30;

        // Base: always exclude hidden partners
        let domain = [["hide_in_pos", "=", false]];

        if (this.state.query) {
            const q = this.state.query;

            // Only use char/text fields — Many2one fields (state_id,
            // country_id) cannot be searched with ilike on a plain string.
            const searchFields = [
                "name",
                "parent_name",
                "phone",
                "mobile",
                "email",
                "barcode",
                "street",
                "zip",
                "city",
                "vat",
            ];

            // Build a correct OR chain:
            // ["|", "|", ...(n-1 pipes), [f1,ilike,q], [f2,ilike,q], ...]
            const orPipes = Array(searchFields.length - 1).fill("|");
            const conditions = searchFields.map((field) => [
                field,
                "ilike",
                `%${q}%`,
            ]);

            // Combine with hide_in_pos using "&"
            domain = [
                "&",
                ["hide_in_pos", "=", false],
                ...orPipes,
                ...conditions,
            ];
        }

        const result = await this.pos.data.searchRead(
            "res.partner",
            domain,
            [],
            {
                limit,
                offset: this.state.currentOffset,
            }
        );

        return result;
    },
});