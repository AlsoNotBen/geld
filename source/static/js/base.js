/* ==========================================================================
   base.js  —  shell behaviour (profile menu, mobile drawer, shortcuts)
   Place this file at: static/js/base.js
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