/** @odoo-module **/

// Intentionally left as a no-op.
//
// This module used to patch PartnerList.getPartners() and getNewPartners()
// with Odoo-18 semantics. Those overrides are incompatible with the Odoo 19
// PartnerList and broke customer search:
//
//   * v19 renders TWO reactive lists — getPartners(this.state.initialPartners)
//     and getPartners(this.state.loadedPartners). The old getPartners() ignored
//     its argument and returned models["res.partner"].getAll(), so every
//     preloaded partner rendered twice (duplicate t-key / duplicate IDs) and
//     searched partners never appeared.
//
//   * v19 getNewPartners() must call get_new_partner via pos.data.callRelated
//     (which inserts ResPartner instances into the store) and push them into
//     this.state.loadedPartners so the list re-renders reactively. The old
//     override called pos.data.searchRead(... load:false ...), which returns raw
//     dicts, inserts nothing into the store, and never touched loadedPartners —
//     so a searched customer was "found" but never rendered.
//
// The "hide_in_pos" filter is now enforced entirely on the backend
// (res.partner._load_pos_data_domain for the preload and
//  res.partner.get_new_partner for search / lazy-loading), so hidden customers
// never reach the frontend and no client-side override is needed. Letting core
// PartnerList run unmodified restores correct rendering, reactivity and search.
