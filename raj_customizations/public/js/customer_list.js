// Highlight frozen customers in the Customer list view.
// Extends (does not replace) erpnext's core listview_settings for Customer,
// using frappe's built-in `get_indicator` hook — the same extension point
// frappe itself uses for the default Enabled/Disabled badge.
// No monkey-patching of core methods, no extra requests, no DOM watchers:
// `is_frozen` just rides along in the list's existing field fetch and is
// read inside the indicator function that already runs once per row.
(function () {
    const existing = frappe.listview_settings["Customer"] || {};
    const original_get_indicator = existing.get_indicator;

    frappe.listview_settings["Customer"] = Object.assign({}, existing, {
        add_fields: [...new Set([...(existing.add_fields || []), "is_frozen", "disabled"])],
        get_indicator: function (doc) {
            if (doc.is_frozen && doc.disabled == 0) {
                return [__("Frozen"), "orange", "is_frozen,=,1"];
            }
            if (original_get_indicator) {
                return original_get_indicator(doc);
            }
        },
    });
})();
