/* ==========================================================================
   lead_form.js  —  the New Lead overlay (#lead-dialog)
   module_base.html loads it on each page of the module.

   WHAT IT DOES
   1. window.openLeadForm(title, action, values, onSaved, customer) opens
      the form. leads.js uses it for New Lead and Edit Lead. customer
      shows the opening balance fields.
   2. The "+" of the customer field in the Quote and Invoice overlays
      opens the form. When the user saves, the form sends JSON, and the
      new customer becomes the selected option.

   MARKUP CONTRACT
       #lead-dialog                  the lead form
       [data-lead-errors]            the errors of a save with fetch
       [data-for-type=I|O]           a form field for one entity type only
       [data-for-customer]           a form field for New Customer only
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

    window.openLeadForm = function (title, action, values, saved, customer) {
        form.reset();
        form.action = action || createUrl;
        dialog.querySelector(".sheet__title").textContent = title;
        Object.entries(values || {}).forEach(function ([key, value]) {
            if (form.elements[key]) form.elements[key].value = value ?? "";
        });
        onSaved = saved || null;
        showType();
        showErrors([]);
        dialog.querySelectorAll("[data-for-customer]").forEach(function (el) {
            el.hidden = !customer;
            el.querySelectorAll("input").forEach(function (c) { c.disabled = !customer; });
        });
        dialog.showModal();
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

    /* The "+" of the customer field in the Quote and Invoice overlays.
       documents.js sends the click as a "doc:action" event. */
    document.addEventListener("doc:action", function (e) {
        if (e.detail.action !== "new-customer") return;
        const select = e.detail.trigger.closest("[data-doc-form]").elements.customer;
        window.openLeadForm("Create New Lead", null, null, function (lead) {
            select.add(new Option(lead.name, lead.id, true, true));
            select.dispatchEvent(new Event("change", { bubbles: true }));
        });
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
