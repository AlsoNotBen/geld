/* ==========================================================================
   leads.js  —  the board of the Leads page
   Place this file at: accounting/static/accounting/js/leads.js
   leads.html loads it in the extra_js block.

   WHAT IT DOES
   1. A click on a lead card opens the lead overlay. The data comes from
      the data-* attributes of the card (see _lead_attrs.html).
   2. The button at the foot of a column shows the cards after the fifth.
   3. The New Lead button opens the empty form.
   4. The Edit button of the overlay opens the same form with the values
      of the lead. The form then saves to the edit URL of the lead.

   MARKUP CONTRACT
       [data-lead-open]        the card, with the data-* attributes
       #lead-view              the overlay
       [data-field=KEY]        the element that shows one value
       [data-gauge=KEY]        the gauge of one measure
       [data-board-more]       the button at the foot of a long column
       [data-lead-new]         the New Lead button
       [data-lead-edit]        the Edit button of the overlay
       [data-edit-url]         the URL that saves the changes of the lead
       [data-form]             the values of the form, as JSON
   The lead form (#lead-dialog) is in lead_form.js.
   A gauge with no value in the card becomes hidden.
   ========================================================================== */
(function () {
    'use strict';

    const view = document.getElementById("lead-view");
    if (!view) return;

    const field = {};
    view.querySelectorAll("[data-field]").forEach(function (el) {
        field[el.dataset.field] = el;
    });

    const gauge = {};
    view.querySelectorAll("[data-gauge]").forEach(function (el) {
        gauge[el.dataset.gauge] = el;
    });

    /* Fill one gauge. A gauge with no level stays hidden. */
    function setGauge(key, level, text) {
        const el = gauge[key];
        if (!el) return;
        el.hidden = !level;
        if (!level) return;
        el.style.setProperty("--v", level + "%");
        el.querySelector(".gauge__value").textContent = text || level;
    }

    function show(key, text) {
        if (field[key]) field[key].textContent = text || "—";
    }

    let current = null;     // the card that the overlay shows

    document.querySelectorAll("[data-lead-open]").forEach(function (card) {
        card.onclick = function () {
            current = card;
            const data = card.dataset;

            show("name", data.name);
            show("stage", data.stage);
            show("status", data.status);
            show("desc", data.desc);
            show("owner", data.owner);
            show("turn", data.turn === "yours" ? "Your turn" : "Their turn");
            show("when", data.when);
            show("email", data.email);
            show("phone", data.phone);

            setGauge("size", data.size, data.sizeLabel);
            setGauge("score", data.score, data.score);
            setGauge("temp", data.temp, data.tempLabel);
            setGauge("resp", data.resp, data.respLabel);

            view.showModal();
        };
    });

    /* ---- More cards ----
       A column shows five cards. The button shows the rest, and a second
       click hides them again. */
    document.querySelectorAll("[data-board-more]").forEach(function (btn) {
        btn.onclick = function () {
            const open = btn.getAttribute("aria-expanded") === "true";
            btn.setAttribute("aria-expanded", open ? "false" : "true");
            btn.closest(".board__col")
               .querySelectorAll(".board__list > .lead")
               .forEach(function (card, index) {
                   if (index >= 5) card.hidden = open;
               });
        };
    });

    /* ---- The lead form ----
       lead_form.js holds the form. The Edit button puts the values of the
       lead in the fields, and the form saves to the edit URL of the lead. */
    const newBtn = document.querySelector("[data-lead-new]");
    if (newBtn) newBtn.onclick = () => window.openLeadForm("Create New Lead");

    const editBtn = view.querySelector("[data-lead-edit]");
    if (editBtn) editBtn.onclick = function () {
        view.close();
        window.openLeadForm("Edit Lead", current.dataset.editUrl, JSON.parse(current.dataset.form));
    };

    /* ---- Close ---- */
    const cancel = view.querySelector("[data-dialog-cancel]");
    if (cancel) cancel.onclick = () => view.close();
    // Close the dialog when the user clicks the backdrop.
    view.onclick = (e) => {
        if (e.target === view) view.close();
    };
})();