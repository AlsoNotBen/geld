/* ==========================================================================
   base.js  —  shell behaviour (profile menu, mobile drawer, shortcuts)
   static/js/base.js
   base.html loads it with the Django static tag, before the extra_js block.
   ========================================================================== */

(function () {
    var banner = document.getElementById('no-js-banner');
    if (banner) { banner.classList.add('is-hidden'); }
})();

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

(function () {
    var body = document.body, item;
    if (body.dataset.module) {
        item = document.querySelector('.modules [data-key="' + body.dataset.module + '"]');
        if (item) {
            item.classList.add('is-active');
            // On a small screen the row of modules scrolls. Show the active one.
            item.scrollIntoView({ block: 'nearest', inline: 'center' });
        }
    }
    if (body.dataset.page) {
        item = document.querySelector('[data-nav="' + body.dataset.page + '"]');
        if (item) { item.classList.add('is-active'); item.setAttribute('aria-current', 'page'); }
    }
})();
/* ==========================================================================
   Company switch (base.html, at the right of the search)
   The button opens the menu. A company item submits the form, and the
   page loads again for that company. "Add New Company" opens an overlay
   instead. The
   overlay works as the message overlay (messaging.js): the form comes
   from the server with fetch(), and the answer of a submit is the form
   with the errors, or JSON with the page to go to.
   ========================================================================== */
(function () {
    "use strict";

    var toggle = document.querySelector("[data-company-toggle]");
    var menu = document.querySelector("[data-company-menu]");
    if (!toggle || !menu) return;

    var url = menu.querySelector("[data-company-new]").getAttribute("data-company-new");
    var dialog = null;

    function setMenu(open) {
        menu.setAttribute("data-open", String(open));
        toggle.setAttribute("aria-expanded", String(open));
    }

    function ensureDialog() {
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.className = "msg-overlay";
        dialog.setAttribute("aria-label", "Add New Company");
        document.body.appendChild(dialog);
        // A click on the backdrop hits the dialog element itself.
        dialog.addEventListener("click", function (e) {
            if (e.target === dialog || e.target.closest("[data-company-close]")) dialog.close();
        });
        dialog.addEventListener("close", function () { dialog.innerHTML = ""; });
        return dialog;
    }

    function note(text) {
        dialog.innerHTML = '<div class="msg-overlay__note"><p></p>' +
            '<button class="tool" type="button" data-company-close>Close</button></div>';
        dialog.querySelector("p").textContent = text;
    }

    // Put the form into the dialog and connect its submit.
    function show(html) {
        dialog.innerHTML = html;
        var form = dialog.querySelector("[data-company-form]");
        if (!form) return;
        var status = form.querySelector("[data-company-status]");
        var submit = form.querySelector('[type="submit"]');

        form.addEventListener("submit", function (e) {
            e.preventDefault();
            submit.disabled = true;
            status.textContent = "The server adds the company…";
            fetch(url, { method: "POST", body: new FormData(form) })
                .then(function (response) {
                    if (!response.ok) throw new Error("HTTP " + response.status);
                    var json = (response.headers.get("Content-Type") || "").indexOf("application/json") === 0;
                    return json ? response.json() : response.text();
                })
                .then(function (answer) {
                    if (answer.redirect) { window.location.href = answer.redirect; return; }
                    show(answer);
                })
                .catch(function () {
                    submit.disabled = false;
                    status.textContent = "The company was not added. Try again.";
                });
        });

        var first = form.querySelector("input:not([type=hidden])");
        if (first) first.focus();
    }

    function openOverlay() {
        var d = ensureDialog();
        note("The form loads…");
        d.showModal();
        fetch(url)
            .then(function (response) {
                if (!response.ok) throw new Error("HTTP " + response.status);
                return response.text();
            })
            .then(show)
            .catch(function () { note("The form did not load. Close the overlay and try again."); });
    }

    toggle.addEventListener("click", function () {
        setMenu(menu.getAttribute("data-open") !== "true");
    });
    menu.querySelector("[data-company-new]").addEventListener("click", function () {
        setMenu(false);
        openOverlay();
    });
    // The capture phase sees each click, also a click on the profile
    // button, which stops the click. A click on the toggle passes, and
    // the propagated click then closes the profile menu.
    document.addEventListener("click", function (e) {
        if (!e.target.closest("[data-company-switch]")) setMenu(false);
    }, true);
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") setMenu(false);
    });
})();


/* ---- File pick (shared/_file_pick.html) ----
   The native file input is hidden. Show the name of the selected file.
   In an .avatar-field, also show the image in the .avatar. The Remove
   button clears the selection and sets avatar_clear, thus Save removes
   the avatar. The .avatar then shows its initials (data-initials). */
(function () {
    "use strict";

    function parts(el) {
        const pick = el.closest(".file-pick");
        const field = pick.closest(".avatar-field");
        return {
            input: pick.querySelector(".file-input"),
            name: pick.querySelector("[data-file-name]"),
            clear: pick.querySelector("[data-file-clear]"),
            remove: pick.querySelector("[data-file-remove]"),
            avatar: field && field.querySelector(".avatar"),
        };
    }

    document.addEventListener("change", function (e) {
        if (!e.target.matches(".file-input")) return;
        const p = parts(e.target);
        const file = e.target.files[0];
        if (!file) return;
        p.name.textContent = file.name;
        p.clear.value = "";
        p.remove.hidden = false;
        if (!p.avatar) return;
        const img = document.createElement("img");
        img.src = URL.createObjectURL(file);
        img.alt = "";
        p.avatar.textContent = "";
        p.avatar.appendChild(img);
    });

    document.addEventListener("click", function (e) {
        const button = e.target.closest("[data-file-remove]");
        if (!button) return;
        const p = parts(button);
        p.input.value = "";
        p.name.textContent = p.name.dataset.empty;
        p.clear.value = "1";
        p.remove.hidden = true;
        if (p.avatar) p.avatar.textContent = p.avatar.dataset.initials || "";
    });
})();
