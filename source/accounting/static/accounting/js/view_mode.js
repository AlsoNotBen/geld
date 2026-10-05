/* ==========================================================================
   accounting/static/accounting/js/view_mode.js
   --------------------------------------------------------------------------
   Formats each number in the content area for the viewing mode. The mode is
   on the shell: data-view="easy" or data-view="standard".

       easy       1 234.00    -1 234.00    (colored)
       standard   1,234.00    (1,234.00)   (no color)

   The script reads a comma, a no-break space or a narrow no-break space as
   the thousands separator, and also a number with no separator (1234.00).
   A number must have a separator group or a decimal part, thus dates, years
   and codes do not change.

   In easy mode, a cell that holds only an amount and has no direction class
   gets one from the sign: is-debit (red) below zero, is-credit (green) above.
   ========================================================================== */
(function () {
    var shell = document.querySelector(".shell[data-view]");
    if (!shell) return;
    var easy = shell.dataset.view === "easy";
    var NUM = /(\(?)([-\u2212]?)(\d{1,3}(?:[,\u00a0\u202f]\d{3})+(?:\.\d+)?|\d+\.\d+)(\)?)/g;
    var ONLY = /^\s*\(?-?(?:\d{1,3}(?:[, ]\d{3})+(?:\.\d+)?|\d+\.\d+)\)?\s*$/;
    var TAGGED = ".is-debit, .is-credit, .is-overdue, .is-count";
    var SKIP = ".table--ledger td:nth-child(4), .table--ledger td:nth-child(5)";

    function format(match, open, sign, digits, close) {
        var negative = sign || (open && close);
        var parts = digits.replace(/[,\u00a0\u202f]/g, "").split(".");
        var whole = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, easy ? " " : ",");
        var text = parts[1] ? whole + "." + parts[1] : whole;
        if (negative) text = easy ? "-" + text : "(" + text + ")";
        // Keep a bracket that is not part of the number.
        if (open && !close) text = "(" + text;
        if (close && !open) text = text + ")";
        return text;
    }

    function colour(el) {
        var text = el.textContent;
        if (!ONLY.test(text) || el.matches(SKIP) || el.closest(TAGGED)) return;
        if (!/[1-9]/.test(text)) return;                 // A zero has no direction.
        el.classList.add(/^\s*-/.test(text) ? "is-debit" : "is-credit");
    }

    var main = shell.querySelector(".main");
    var walker = document.createTreeWalker(main, NodeFilter.SHOW_TEXT);
    var node;
    while ((node = walker.nextNode())) {
        if (node.parentNode.closest("script, style, textarea")) continue;
        node.nodeValue = node.nodeValue.replace(NUM, format);
        if (easy) colour(node.parentNode);
    }

    // The switch text on the Module Settings page.
    var toggle = document.querySelector("[data-view-toggle]");
    if (toggle) {
        toggle.addEventListener("change", function () {
            toggle.parentNode.querySelector(".switch__text").textContent =
                toggle.checked ? "Easy Viewing" : "Accounting Standard Viewing";
        });
    }
})();
