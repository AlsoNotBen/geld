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

   The New Entry button opens an empty form with two lines, which goes to
   the create URL. Each line has a debit or a credit, before tax. A tax code
   adds the tax on the same side, as the server does (see entry_lines). The
   tax and the totals show below the lines. The Save button works only when
   the debits equal the credits, with the tax. The server does the same check.

   The View button opens the same form with the lines of its row (the
   data-lines JSON, see draft_rows), and it sends the form to the update
   URL of that entry. In the view, the user can change the line
   descriptions only. The other fields are disabled.
   ========================================================================== */
(function () {
    const dialog = document.getElementById("entry-dialog");
    if (!dialog) return;

    const form = dialog.querySelector("form");
    const title = dialog.querySelector(".sheet__title");
    const submit = dialog.querySelector(".tool--primary[type=submit]");
    const voidBtn = dialog.querySelector("[data-entry-void]");
    const postBtn = dialog.querySelector("[data-entry-post]");
    const addBtn = dialog.querySelector("[data-entry-line-add]");
    const lines = dialog.querySelector("[data-entry-lines]");
    const template = lines.querySelector("[data-entry-line]").cloneNode(true);
    const totalDebit = dialog.querySelector("[data-total-debit]");
    const totalCredit = dialog.querySelector("[data-total-credit]");
    const taxRow = dialog.querySelector("[data-entry-tax-row]");
    const taxDebit = dialog.querySelector("[data-tax-debit]");
    const taxCredit = dialog.querySelector("[data-tax-credit]");
    const balance = dialog.querySelector("[data-entry-balance]");
    const createUrl = form.getAttribute("action");
    const field = form.elements;
    let viewing = false;

    // Amounts in cents, thus the sums have no rounding errors.
    function cents(input) {
        return Math.round((parseFloat(input.value) || 0) * 100);
    }

    function text(value) {
        return (value / 100).toFixed(2);
    }

    function addLine(data) {
        const row = template.cloneNode(true);
        if (data) {
            row.querySelector("[name=line_id]").value = data.id;
            row.querySelector("[name=line_id]").disabled = false;
            row.querySelector("[name=line_account]").value = data.account;
            row.querySelector("[name=line_tax]").value = data.tax;
            row.querySelector("[name=line_description]").value = data.description;
            row.querySelector("[name=line_debit]").value = data.debit;
            row.querySelector("[name=line_credit]").value = data.credit;
        }
        lines.appendChild(row);
    }

    function setLines(data) {
        lines.replaceChildren();
        data.forEach(addLine);
    }

    /* The tax of an amount in cents, rounded half up as the server does.
       The rate is in hundredths of a percent, thus the product is exact. */
    function tax(amount, row) {
        const account = row.querySelector("[name=line_account]").selectedOptions[0];
        const code = row.querySelector("[name=line_tax]").selectedOptions[0];
        if (viewing || !code || (account && account.hasAttribute("data-tax-account"))) return 0;
        return Math.round(amount * Math.round(parseFloat(code.dataset.rate) * 100) / 10000);
    }

    function update() {
        let debit = 0, credit = 0, debitTax = 0, creditTax = 0, noAccount = false;
        lines.querySelectorAll("tr").forEach(function (row) {
            const lineDebit = cents(row.querySelector("[name=line_debit]"));
            const lineCredit = cents(row.querySelector("[name=line_credit]"));
            if ((lineDebit || lineCredit) && !row.querySelector("[name=line_account]").value) noAccount = true;
            debit += lineDebit;
            credit += lineCredit;
            debitTax += tax(lineDebit, row);
            creditTax += tax(lineCredit, row);
        });
        debit += debitTax;
        credit += creditTax;
        taxDebit.textContent = text(debitTax);
        taxCredit.textContent = text(creditTax);
        taxRow.hidden = viewing;        // A saved entry already has its tax lines.
        totalDebit.textContent = text(debit);
        totalCredit.textContent = text(credit);

        let problem = "";
        if (debit !== credit) problem = "Not balanced. The difference is " + text(Math.abs(debit - credit)) + ".";
        else if (!debit) problem = "Give the amounts of the lines.";
        else if (noAccount) problem = "Select an account for each line.";
        balance.textContent = viewing ? "" : problem;
        submit.disabled = !viewing && problem !== "";
    }

    // A line has a debit or a credit. A value on one side clears the other side.
    lines.addEventListener("input", function (e) {
        const row = e.target.closest("tr");
        if (e.target.name === "line_debit" && e.target.value) row.querySelector("[name=line_credit]").value = "";
        if (e.target.name === "line_credit" && e.target.value) row.querySelector("[name=line_debit]").value = "";
        update();
    });

    // Remove a line. Two lines stay, thus the form always has a debit and a credit.
    lines.addEventListener("click", function (e) {
        const button = e.target.closest("[data-entry-line-remove]");
        if (button && lines.children.length > 2) {
            button.closest("tr").remove();
            update();
        }
    });

    addBtn.onclick = function () { addLine(); };

    function lock(isLocked) {
        form.querySelectorAll(".field__control:not([name=line_description])").forEach(function (control) {
            control.disabled = isLocked;
        });
        form.querySelectorAll("[data-entry-line-remove]").forEach(function (button) { button.hidden = isLocked; });
        addBtn.hidden = isLocked;
    }

    const openBtn = document.querySelector("[data-entry-new]");
    if (openBtn) openBtn.onclick = function () {
        form.reset();
        setLines([null, null]);
        viewing = false;
        lock(false);
        const now = new Date();                   // Today in the time zone of the user
        field.date.value = new Date(now - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
        form.setAttribute("action", createUrl);
        title.textContent = "New Journal Entry";
        submit.textContent = "Save Draft";
        voidBtn.hidden = true;
        postBtn.hidden = true;
        update();
        dialog.showModal();
    };

    document.querySelectorAll("[data-entry-view]").forEach(function (btn) {
        btn.onclick = function () {
            const data = btn.dataset;
            form.setAttribute("action", data.url);
            field.date.value = data.date;
            field.entry_type.value = data.entryType;
            field.reference.value = data.reference;
            field.narration.value = data.narration;
            setLines(JSON.parse(data.lines));
            viewing = true;
            lock(true);
            title.textContent = "View Journal Entry";
            submit.textContent = "Save as Draft";
            /* Each button sends the form to its own view. The view reads the
               entry from the URL, thus it ignores the fields. */
            voidBtn.setAttribute("formaction", data.voidUrl);
            postBtn.setAttribute("formaction", data.postUrl);
            voidBtn.hidden = false;
            postBtn.hidden = false;
            update();
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
