/* ==========================================================================
   lead_form.js  —  the New Lead overlay (#lead-dialog)
   module_base.html loads it on each page of the module.

   WHAT IT DOES
   1. window.openLeadForm(title, action, values, onSaved) opens the form.
      leads.js uses it for New Lead and Edit Lead.
   2. The "+" of the customer field in the Quote and Invoice overlays
      opens the form. When the user saves, the form sends JSON, and the
      new customer becomes the selected option.

   MARKUP CONTRACT
       #lead-dialog                  the lead form
       [data-for-type=I|O]           a form field for one entity type only
       [data-action="new-customer"]  the "+" of the customer field
                                     (SelectWithAddButton, documents app)
   ========================================================================== */
(function () {
    'use strict';

    const dialog = document.getElementById("lead-dialog");
    if (!dialog) return;

    const form = dialog.querySelector("form");
    const createUrl = form.action;
    let onSaved = null;     // set when an overlay waits for the new customer

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

    window.openLeadForm = function (title, action, values, saved) {
        form.reset();
        form.action = action || createUrl;
        dialog.querySelector(".sheet__title").textContent = title;
        Object.entries(values || {}).forEach(function ([key, value]) {
            if (form.elements[key]) form.elements[key].value = value ?? "";
        });
        onSaved = saved || null;
        showType();
        dialog.showModal();
    };

    /* With onSaved, send the form as fetch and stay on the page. */
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
                dialog.close();
                onSaved(lead);
            });
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

    /* ---- Close ---- */
    dialog.querySelector("[data-dialog-cancel]").onclick = () => dialog.close();
    // Close the dialog when the user clicks the backdrop.
    dialog.onclick = (e) => {
        if (e.target === dialog) dialog.close();
    };
})();
