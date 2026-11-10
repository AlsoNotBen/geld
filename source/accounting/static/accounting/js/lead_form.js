/* ==========================================================================
   lead_form.js  —  the New Lead overlay (#lead-dialog)
   module_base.html loads it on each page of the module.

   WHAT IT DOES
   1. window.openLeadForm(title, action, values, onSaved, customer) opens
      the form. leads.js uses it for New Lead and Edit Lead. customer
      shows the opening balance fields.
   2. The "+" of the customer field in the document overlays opens the
      New Lead form for a Quote, and the New Customer form for an Invoice.
      When the user saves, the form sends JSON, and the new customer
      becomes the selected option.

   MARKUP CONTRACT
       #lead-dialog                  the lead form
       [data-lead-errors]            the errors of a save with fetch
       [data-for-type=I|O]           a form field for one entity type only
       [data-for-customer]           a form field for New Customer only
       [data-for-lead]               a tab for New Lead and Edit Lead only. Its
                                     fields stay enabled, thus a new customer
                                     gets the default values of its lead.
       [data-avatar-preview]         the current avatar (base.js shows the selected image)
       [role=tab][data-tab=KEY]      a tab button; aria-controls gives its panel
       [data-file-name]              the name of the selected file (base.js)
       [data-action="new-customer"]  the "+" of the customer field
                                     (SelectWithAddButton, documents app)
       [data-customer-new]           a New Customer button or link
   ========================================================================== */
(function () {
    'use strict';

    const dialog = document.getElementById("lead-dialog");
    if (!dialog) return;

    const form = dialog.querySelector("form");
    const errors = dialog.querySelector("[data-lead-errors]");
    const createUrl = form.action;
    let onSaved = null;     // set when an overlay waits for the new customer

    function showErrors(list) {
        errors.textContent = "";
        list.forEach(function (text) {
            const line = document.createElement("p");
            line.textContent = text;
            errors.appendChild(line);
        });
        errors.hidden = list.length === 0;
    }

    /* Show the fields of the selected type. Disabled fields do not
       send a value, and the browser does not validate them. */
    function showType() {
        const type = form.elements.type.value;
        dialog.querySelector("label[for=ld-name]").textContent =
            type === "I" ? "First name" : "Name";
        dialog.querySelectorAll("[data-for-type]").forEach(function (el) {
            const on = el.dataset.forType === type;
            el.hidden = !on;
            el.querySelectorAll("input, select").forEach(function (c) { c.disabled = !on; });
        });
    }
    form.elements.type.onchange = showType;

    /* The avatar preview: the image of the lead, else the initials of the
       name. form.reset() clears the file input, thus the file name goes back
       to its first text. Remove (base.js) shows only when there is an image. */
    const preview = dialog.querySelector("[data-avatar-preview]");
    const fileName = dialog.querySelector("[data-file-name]");
    const clear = dialog.querySelector("[data-file-clear]");
    const remove = dialog.querySelector("[data-file-remove]");
    function showAvatar(url, name) {
        preview.dataset.initials = (name || "").split(/\s+/).slice(0, 2).map((w) => w.charAt(0)).join("").toUpperCase();
        preview.textContent = preview.dataset.initials;
        fileName.textContent = fileName.dataset.empty;
        clear.value = "";       // reset() does not reset a hidden input
        remove.hidden = !url;
        if (!url) return;
        preview.textContent = "";
        const img = document.createElement("img");
        img.src = url;
        img.alt = "";
        preview.appendChild(img);
    }

    /* ---- Tabs ----
       One panel shows at a time. The arrow keys move along the row. */
    const tabs = Array.from(dialog.querySelectorAll("[role=tab]"));
    function selectTab(tab, focus) {
        tabs.forEach(function (item) {
            const on = item === tab;
            item.setAttribute("aria-selected", String(on));
            item.tabIndex = on ? 0 : -1;
            document.getElementById(item.getAttribute("aria-controls")).hidden = !on;
        });
        if (focus) tab.focus();
    }
    tabs.forEach((tab) => tab.addEventListener("click", () => selectTab(tab)));
    dialog.querySelector("[role=tablist]").addEventListener("keydown", function (e) {
        const shown = tabs.filter((tab) => !tab.hidden);
        const i = shown.indexOf(document.activeElement);
        const step = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
        if (i === -1 || !step) return;
        e.preventDefault();
        selectTab(shown[(i + step + shown.length) % shown.length], true);
    });

    /* A field that is not valid can be in a hidden panel. The browser can
       then not show the message. Thus open the tab of the first such field. */
    form.addEventListener("invalid", function (e) {
        const panel = e.target.closest("[role=tabpanel]");
        if (panel && panel.hidden) selectTab(document.getElementById(panel.getAttribute("aria-labelledby")));
    }, true);

    window.openLeadForm = function (title, action, values, saved, customer) {
        form.reset();
        form.action = action || createUrl;
        dialog.querySelector(".sheet__title").textContent = title;
        Object.entries(values || {}).forEach(function ([key, value]) {
            if (form.elements[key]) form.elements[key].value = value ?? "";
        });
        onSaved = saved || null;
        showAvatar(values && values.avatar_url, values && values.name);
        showType();
        showErrors([]);
        dialog.querySelectorAll("[data-for-customer]").forEach(function (el) {
            el.hidden = !customer;
            el.querySelectorAll("input").forEach(function (c) { c.disabled = !customer; });
        });
        dialog.querySelectorAll("[data-for-lead]").forEach((el) => { el.hidden = !!customer; });
        selectTab(tabs[0]);
        dialog.showModal();
        form.elements.name.focus();     // else the browser focuses the tab row (a scroll box)
    };

    /* With onSaved, send the form as fetch and stay on the page. An error
       (e.g. no open period for the opening balance) keeps the form open. */
    form.onsubmit = function (e) {
        if (!onSaved) return;
        e.preventDefault();
        fetch(form.action, {
            method: "POST",
            body: new FormData(form),
            headers: { "Accept": "application/json" },
        })
            .then((r) => r.json())
            .then(function (lead) {
                if (lead.errors) {
                    showErrors(lead.errors);
                    return;
                }
                dialog.close();
                onSaved(lead);
            })
            .catch(() => showErrors(["The form was not saved. Try again."]));
    };

    /* The "+" of the customer field in the document overlays. documents.js
       sends the click as a "doc:action" event. A Quote opens New Lead.
       The other documents (e.g. an Invoice) open New Customer. */
    document.addEventListener("doc:action", function (e) {
        if (e.detail.action !== "new-customer") return;
        const trigger = e.detail.trigger;
        const select = trigger.closest("[data-doc-form]").elements.customer;
        const panel = trigger.closest("[data-doc-panel]");
        const isQuote = !!panel && panel.dataset.docKey === "quote";
        window.openLeadForm(isQuote ? "Create New Lead" : "Create New Customer", null, null, function (lead) {
            select.add(new Option(lead.name, lead.id, true, true));
            select.dispatchEvent(new Event("change", { bubbles: true }));
        }, !isQuote);
    });

    /* The New Customer buttons (the Customers page and menu). A customer
       is an entity with a lead, thus they open the same form, with the
       opening balance. After the save, the browser goes to the href of
       the button, else it reloads. */
    document.addEventListener("click", function (e) {
        const button = e.target.closest("[data-customer-new]");
        if (!button) return;
        e.preventDefault();
        window.openLeadForm("Create New Customer", null, null, function () {
            window.location.assign(button.getAttribute("href") || window.location.href);
        }, true);
    });

    /* ---- Close ---- */
    dialog.querySelector("[data-dialog-cancel]").onclick = () => dialog.close();
    // Close the dialog when the user clicks the backdrop.
    dialog.onclick = (e) => {
        if (e.target === dialog) dialog.close();
    };
})();
