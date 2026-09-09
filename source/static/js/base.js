/* ==========================================================================
   base.js  —  shell behaviour (profile menu, mobile drawer, shortcuts)
   static/js/base.js
   base.html loads it with the Django static tag, before the extra_js block.
   ========================================================================== */

// Small, dependency-free behaviour for the shell.
(function () {
    "use strict";

    // --- Profile menu -------------------------------------------------
    var menuBtn = document.querySelector("[data-menu-toggle]");
    var menu = document.querySelector("[data-menu]");

    function closeMenu() {
        if (!menu) return;
        menu.setAttribute("data-open", "false");
        menuBtn.setAttribute("aria-expanded", "false");
    }

    if (menuBtn && menu) {
        menuBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            var open = menu.getAttribute("data-open") === "true";
            menu.setAttribute("data-open", String(!open));
            menuBtn.setAttribute("aria-expanded", String(!open));
        });
        document.addEventListener("click", function (e) {
            if (!menu.contains(e.target)) closeMenu();
        });
    }

    // --- Mobile drawer ------------------------------------------------
    var drawerToggle = document.querySelector("[data-drawer-toggle]");
    var drawerClose = document.querySelector("[data-drawer-close]");

    function setDrawer(open) {
        document.body.setAttribute("data-drawer", String(open));
        if (drawerToggle) drawerToggle.setAttribute("aria-expanded", String(open));
    }

    if (drawerToggle) drawerToggle.addEventListener("click", function () {
        setDrawer(document.body.getAttribute("data-drawer") !== "true");
    });
    if (drawerClose) drawerClose.addEventListener("click", function () { setDrawer(false); });

    // --- Keys ---------------------------------------------------------
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") { closeMenu(); setDrawer(false); }
        // Focus the search field with Ctrl/Cmd + K.
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
            var input = document.querySelector(".search input");
            if (input) { e.preventDefault(); input.focus(); }
        }
    });
})();
/* ==========================================================================
   Number format
   A number reads more easily with a space between each group of three
   digits. This code writes the space into the page after the load, thus
   the server keeps the plain value.

       <table data-num>              each money cell of the table
       <td data-num>1234.50</td>     one cell only
       App.formatAmount("23000.00")  → "23 000.00"
   ========================================================================== */
window.App = window.App || {};      // Make the namespace before you fill it.

(function () {
    'use strict';

    var SPACE = '\u00A0';                    // a space that holds the line
    var MONEY = /^-?\d+\.\d{2}$/;

    /* Give the groups of three digits a space. The function first removes
       the separators of a previous call, thus a second call is safe. */
    App.formatAmount = function (value) {
        var text = String(value).replace(/[\s,\u00A0\u202F]/g, '');
        if (!MONEY.test(text)) { return null; }

        var parts = text.split('.');
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, SPACE);
        return parts.join('.');
    };

    /* Find each marked element. An element with the attribute gets the
       format. A container with the attribute gives it to its cells. */
    App.formatNumbers = function (root) {
        var scope = root || document;
        Array.prototype.forEach.call(scope.querySelectorAll('[data-num]'), function (node) {
            var cells = node.querySelectorAll('td, th, .num');
            var items = cells.length ? cells : [node];

            Array.prototype.forEach.call(items, function (cell) {
                if (cell.children.length) { return; }   // keep a cell with markup
                var out = App.formatAmount(cell.textContent);
                if (out !== null) { cell.textContent = out; }
            });
        });
    };

    function init() { App.formatNumbers(document); }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();