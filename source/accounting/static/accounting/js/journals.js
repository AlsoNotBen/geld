/* ==========================================================================
   journals.js  —  the tab control of the Accounting journals page
   Place this file at: accounting/static/accounting/js/journals.js
   journals.html loads it in the extra_js block of base.html.

   WHAT IT DOES
   The script shows one panel and hides the others. It also writes the key
   of the tab into the URL, thus a link or a page reload opens the same
   tab. Example: /accounting/journals/?journal=sales

   MARKUP CONTRACT
       [data-tabset]                  the container
       [data-tabset-param="journal"]  the name of the URL parameter
                                      (leave it out to keep the URL clean)
       [role="tab"][data-tab=KEY]     the button
       [data-panel=KEY]               the panel that the button shows
   The button must also point at its panel with aria-controls.

   The script is general. Put the same attributes on another page to get
   the same behaviour.
   ========================================================================== */
(function () {
    'use strict';

    function setUp(root) {
        var tabs = Array.prototype.slice.call(root.querySelectorAll('[role="tab"]'));
        if (tabs.length < 2) { return; }

        var param = root.getAttribute('data-tabset-param') || '';

        function panelOf(tab) {
            return document.getElementById(tab.getAttribute('aria-controls'));
        }

        /* Show one tab. The two flags keep the first call quiet: it must
           not move the focus, and it must not touch the URL. */
        function select(tab, moveFocus, writeUrl) {
            tabs.forEach(function (item) {
                var isCurrent = (item === tab);
                var panel = panelOf(item);

                item.setAttribute('aria-selected', isCurrent ? 'true' : 'false');
                item.tabIndex = isCurrent ? 0 : -1;
                if (panel) { panel.hidden = !isCurrent; }
            });

            if (moveFocus) { tab.focus(); }
            if (writeUrl) { remember(tab.getAttribute('data-tab')); }
        }

        /* The URL keeps the choice. replaceState makes no new history
           entry, thus the Back button leaves the page as the user expects. */
        function remember(key) {
            if (!param || !key || !window.history || !window.history.replaceState) { return; }
            try {
                var url = new URL(window.location.href);
                url.searchParams.set(param, key);
                window.history.replaceState(null, '', url);
            } catch (error) {
                /* An old browser has no URL object. The tabs still work. */
            }
        }

        function tabFor(key) {
            if (!key) { return null; }
            return tabs.filter(function (item) {
                return item.getAttribute('data-tab') === key;
            })[0] || null;
        }

        /* ---- Pointer ---- */
        tabs.forEach(function (tab) {
            tab.addEventListener('click', function () {
                select(tab, false, true);
            });
        });

        /* ---- Keyboard (the pattern of the WAI-ARIA tabs) ----
           The arrow keys move along the row. Home and End go to the ends.
           A button gets Enter and Space from the browser. */
        root.addEventListener('keydown', function (event) {
            var current = tabs.indexOf(document.activeElement);
            if (current === -1) { return; }

            var next = -1;
            if (event.key === 'ArrowRight') { next = (current + 1) % tabs.length; }
            else if (event.key === 'ArrowLeft') { next = (current - 1 + tabs.length) % tabs.length; }
            else if (event.key === 'Home') { next = 0; }
            else if (event.key === 'End') { next = tabs.length - 1; }
            if (next === -1) { return; }

            event.preventDefault();
            select(tabs[next], true, true);
        });

        /* ---- The first tab ----
           The URL wins. If it holds no key, the markup decides. */
        var start = null;
        if (param) {
            try {
                start = tabFor(new URL(window.location.href).searchParams.get(param));
            } catch (error) {
                start = null;
            }
        }
        if (!start) {
            start = tabs.filter(function (item) {
                return item.getAttribute('aria-selected') === 'true';
            })[0] || tabs[0];
        }
        select(start, false, false);
    }

    function init() {
        Array.prototype.forEach.call(document.querySelectorAll('[data-tabset]'), setUp);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
/* ==========================================================================
   The entry overlay. It uses the same pattern as accounts.js.

   The New Entry button opens an empty form, which goes to the create URL.
   The Edit button opens the same form with the data of its row, and it
   sends the form to the update URL of that entry. The data comes from the
   data-* attributes of the button (see journals.html).
   ========================================================================== */
(function () {
    const dialog = document.getElementById("entry-dialog");
    if (!dialog) return;

    const form = dialog.querySelector("form");
    const title = dialog.querySelector(".sheet__title");
    const submit = dialog.querySelector(".tool--primary[type=submit]");
    const voidBtn = dialog.querySelector("[data-entry-void]");
    const postBtn = dialog.querySelector("[data-entry-post]");
    const createUrl = form.getAttribute("action");
    const field = form.elements;

    const openBtn = document.querySelector("[data-entry-new]");
    if (openBtn) openBtn.onclick = function () {
        form.reset();
        form.setAttribute("action", createUrl);
        title.textContent = "New Journal Entry";
        submit.textContent = "Post Entry";
        voidBtn.hidden = true;
        postBtn.hidden = true;
        dialog.showModal();
    };

    document.querySelectorAll("[data-entry-edit]").forEach(function (btn) {
        btn.onclick = function () {
            const data = btn.dataset;
            form.setAttribute("action", data.url);
            field.date.value = data.date;
            field.entry_type.value = data.entryType;
            field.period.value = data.period;
            field.reference.value = data.reference;
            field.debit_account.value = data.debit;
            field.credit_account.value = data.credit;
            field.amount.value = data.amount;
            field.currency.value = data.currency;
            field.tax_code.value = data.tax;
            field.description.value = data.description;
            field.narration.value = data.narration;
            title.textContent = "Edit Journal Entry";
            submit.textContent = "Save as Draft";
            /* Each button sends the form to its own view. The view reads the
               entry from the URL, thus it ignores the fields. */
            voidBtn.setAttribute("formaction", data.voidUrl);
            postBtn.setAttribute("formaction", data.postUrl);
            voidBtn.hidden = false;
            postBtn.hidden = false;
            dialog.showModal();
        };
    });

    const cancelBtn = dialog.querySelector("[data-dialog-cancel]");
    if (cancelBtn) cancelBtn.onclick = () => dialog.close();

    // Close the dialog when the user clicks the backdrop.
    dialog.onclick = (e) => {
        if (e.target === dialog) dialog.close();
    };
})();