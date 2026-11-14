/* ==========================================================================
   table_columns.js  —  the filter and the sort of each column of a table
   module_base.html loads it on each page of the module.

   WHAT IT DOES
   1. Each column head gets a filter button (the icon of the Leads board).
      The button opens a field below the head. A row stays if the cell of
      that column holds each word of the field. Upper and lower case are
      the same, and the spaces do not count. All the open fields filter
      at the same time. When you close a field, its filter stops.
   2. A click on the name of a column sorts the rows by that column. The
      first click sorts up (A to Z, 0 to 9). The next click sorts down.
      Numbers sort as numbers. A figure in brackets is negative. An empty
      cell or a dash sorts first.
   A row with an empty-state cell (td[colspan]) always stays. The totals in
   the foot of a table do not change. A head with no visible name (e.g. the
   Actions column) gets no buttons.

   MARKUP CONTRACT
       table[data-columns]            the table. A value (e.g. "ledger")
                                      joins all the tables with that value:
                                      they share the filters and the sort.
       table[data-columns-group]      each tbody is one item (e.g. a journal
                                      entry with its lines). The filter
                                      reads all the rows of the tbody. The
                                      sort reads the first row.
       tr[data-pin]                   a row that does not move and always
                                      stays, e.g. the balance brought forward.
       td[data-sort=VALUE]            the sort uses VALUE, not the text,
                                      e.g. a date as 2026-11-14.
       [data-columns-section]         a part around a table. It goes away
                                      when a filter removes all its rows.
   ========================================================================== */
(function () {
    "use strict";

    const ICON = '<svg class="icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 5h16l-6 7v6l-4 2v-8L4 5z" stroke-linecap="round" stroke-linejoin="round"/></svg>';

    /* The items of a table: each tbody, or each row. */
    function items(table) {
        const rows = table.hasAttribute("data-columns-group")
            ? Array.from(table.tBodies)
            : Array.from(table.tBodies).flatMap((body) => Array.from(body.rows));
        return rows.filter((item) => !item.querySelector("td[colspan]") && !item.hasAttribute("data-pin"));
    }

    /* The cells of one column of an item. */
    function cells(item, col) {
        const rows = item.rows ? Array.from(item.rows) : [item];
        return rows.map((row) => row.cells[col]).filter(Boolean);
    }

    function sortKey(item, col) {
        const cell = cells(item, col)[0];
        if (!cell) return "";
        const value = (cell.dataset.sort !== undefined ? cell.dataset.sort : cell.textContent).trim();
        return value === "—" ? "" : value;
    }

    /* "1 150.00" gives 1150, "(20.00)" gives -20. Other text gives NaN. */
    function number(value) {
        const s = value.replace(/[\s,]/g, "").replace("−", "-").replace(/^\((.*)\)$/, "-$1");
        return /^-?\d*\.?\d+$/.test(s) ? parseFloat(s) : NaN;
    }

    /* Empty first, then numbers, then text. */
    function compare(a, b) {
        if (!a || !b) return (a ? 1 : 0) - (b ? 1 : 0);
        const x = number(a), y = number(b);
        if (isNaN(x) !== isNaN(y)) return isNaN(x) ? 1 : -1;
        if (!isNaN(x)) return x - y;
        return a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" });
    }

    /* Show the rows that agree with the filters, in the order of the sort. */
    function apply(set) {
        const active = Object.keys(set.filters).length > 0;
        set.tables.forEach(function (table) {
            const list = items(table);

            list.forEach(function (item) {
                item.hidden = !Object.entries(set.filters).every(function ([col, words]) {
                    const text = cells(item, col).map((cell) => cell.textContent).join(" ").toLowerCase().replace(/\s+/g, "");
                    return words.every((word) => text.includes(word));
                });
            });

            if (set.sort) {
                const { col, dir } = set.sort;
                list.slice()
                    .sort((a, b) => dir * compare(sortKey(a, col), sortKey(b, col)))
                    .forEach(function (item) {
                        if (item.rows) table.insertBefore(item, table.tFoot);
                        else item.parentNode.appendChild(item);
                    });
            }

            const section = table.closest("[data-columns-section]");
            if (section) section.hidden = active && !list.some((item) => !item.hidden);

            table.querySelectorAll("thead th[data-col]").forEach(function (th) {
                const col = th.dataset.col;
                const input = th.querySelector(".th-search");
                const open = set.open.has(col);
                input.hidden = !open;
                if (!open) input.value = "";
                th.querySelector(".th-filter").setAttribute("aria-expanded", String(open));
                if (set.sort && String(set.sort.col) === col) th.setAttribute("aria-sort", set.sort.dir > 0 ? "ascending" : "descending");
                else th.removeAttribute("aria-sort");
            });
        });
    }

    /* Put the buttons and the field into one column head. */
    function setUp(th, set) {
        const col = String(th.cellIndex);
        const name = th.textContent.trim();
        th.dataset.col = col;

        const sort = document.createElement("button");
        sort.type = "button";
        sort.className = "th-sort";
        sort.innerHTML = th.innerHTML + '<span class="th-sort__mark" aria-hidden="true"></span>';

        const filter = document.createElement("button");
        filter.type = "button";
        filter.className = "board__filter th-filter";
        filter.setAttribute("aria-expanded", "false");
        filter.setAttribute("aria-label", "Filter the " + name + " column");
        filter.innerHTML = ICON;

        const input = document.createElement("input");
        input.type = "search";
        input.className = "field__control th-search";
        input.placeholder = "Filter";
        input.setAttribute("aria-label", "Filter the " + name + " column");
        input.hidden = true;

        const head = document.createElement("span");
        head.className = "th-head";
        head.append(sort, filter);
        th.replaceChildren(head, input);

        sort.onclick = function () {
            const same = set.sort && String(set.sort.col) === col;
            set.sort = { col: Number(col), dir: same ? -set.sort.dir : 1 };
            apply(set);
        };

        filter.onclick = function () {
            if (set.open.has(col)) {
                set.open.delete(col);
                delete set.filters[col];
            } else {
                set.open.add(col);
            }
            apply(set);
            if (set.open.has(col)) input.focus();
        };

        input.oninput = function () {
            const words = input.value.toLowerCase().split(/\s+/).filter(Boolean);
            if (words.length) set.filters[col] = words;
            else delete set.filters[col];
            // A joined table shows the same words in the same column.
            set.tables.forEach(function (table) {
                const other = table.querySelector('thead th[data-col="' + col + '"] .th-search');
                if (other && other !== input) other.value = input.value;
            });
            apply(set);
        };
    }

    const sets = {};
    document.querySelectorAll("table[data-columns]").forEach(function (table) {
        const key = table.dataset.columns;
        const set = key && sets[key]
            ? sets[key]
            : { tables: [], filters: {}, open: new Set(), sort: null };
        if (key) sets[key] = set;
        set.tables.push(table);

        table.querySelectorAll("thead th").forEach(function (th) {
            if (th.textContent.trim() && !th.querySelector(".visually-hidden")) setUp(th, set);
        });
    });
})();
