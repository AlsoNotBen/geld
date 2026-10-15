/* ==========================================================================
   table_filter.js  —  the Filter field of a page
   module_base.html loads it on each page of the module.

   A field with the data-filter attribute filters each table of its page.
   A row stays if it holds each word of the field. Upper and lower case are
   the same, and the spaces do not count, thus "1150" finds "1 150.00".
   A row with an empty-state cell (td[colspan]) always stays. The totals in
   the foot of a table do not change.

   MARKUP CONTRACT
       input[data-filter]          the field
       [data-filter-group=TEXT]    a part with a table, e.g. one ledger
                                   account. TEXT counts for each row of the
                                   part, and the part goes away when no row
                                   stays.
   ========================================================================== */
(function () {
    "use strict";

    document.querySelectorAll("input[data-filter]").forEach(function (input) {
        const page = input.closest(".page") || document;

        input.addEventListener("input", function () {
            const words = input.value.toLowerCase().split(/\s+/).filter(Boolean);

            page.querySelectorAll(".table tbody tr").forEach(function (row) {
                if (row.querySelector("td[colspan]")) return;
                const group = row.closest("[data-filter-group]");
                const text = ((group ? group.dataset.filterGroup : "") + row.textContent).toLowerCase().replace(/\s+/g, "");
                row.hidden = !words.every((word) => text.includes(word));
            });

            page.querySelectorAll("[data-filter-group]").forEach(function (group) {
                group.hidden = !group.querySelector("tbody tr:not([hidden])");
            });
        });
    });
})();
