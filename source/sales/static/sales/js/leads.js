/* ==========================================================================
   leads.js  —  the board of the Leads page
   Place this file at: sales/static/sales/js/leads.js
   leads.html loads it in the extra_js block.

   WHAT IT DOES
   1. A click on a lead card opens the lead overlay. The data comes from
      the data-* attributes of the card (see _lead_attrs.html).
   2. The button at the foot of a column shows the cards after the fifth.
   3. The New Lead button opens the empty form.
   4. The Edit button of the overlay opens the same form with the values
      of the lead. The form then saves to the edit URL of the lead.
   5. The filter button of a column opens a field. The field hides each
      card of the column that does not hold all the words of the field.
   6. A card moves to another column with drag and drop. The column gives
      the new stage of the lead. The card moves after the server saves it.

   MARKUP CONTRACT
       [data-lead-open]        the card, with the data-* attributes
       #lead-view              the overlay
       [data-field=KEY]        the element that shows one value
       [data-gauge=KEY]        the gauge of one measure
       [data-board-more]       the button at the foot of a long column
       [data-board-filter]     the filter button of a column
       [data-board-search]     the filter field of a column
       [data-stage-key]        the stage of a column (Lead.SaleStage)
       [data-stage-url]        the URL that saves the stage of the lead
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

    /* ---- The cards of a column ----
       A card shows if it holds each word of the filter. Upper and lower
       case are the same, and the spaces do not count. Without a filter, a
       column with a More button shows five cards until the user opens it. */
    function refresh(col) {
        const words = col.querySelector("[data-board-search]").value.toLowerCase().split(/\s+/).filter(Boolean);
        const more = col.querySelector("[data-board-more]");
        const open = !more || more.getAttribute("aria-expanded") === "true";
        col.querySelectorAll(".board__list > .lead").forEach(function (card, index) {
            const text = card.textContent.toLowerCase().replace(/\s+/g, "");
            card.hidden = words.length ? !words.every((word) => text.includes(word)) : !open && index >= 5;
        });
    }

    /* ---- More cards ----
       A column shows five cards. The button shows the rest, and a second
       click hides them again. */
    document.querySelectorAll("[data-board-more]").forEach(function (btn) {
        btn.onclick = function () {
            const open = btn.getAttribute("aria-expanded") === "true";
            btn.setAttribute("aria-expanded", open ? "false" : "true");
            refresh(btn.closest(".board__col"));
        };
    });

    /* ---- Filter ----
       The filter button opens and closes the field of its column. A closed
       field does not filter. */
    document.querySelectorAll(".board__col").forEach(function (col) {
        const btn = col.querySelector("[data-board-filter]");
        const search = col.querySelector("[data-board-search]");
        btn.onclick = function () {
            search.hidden = !search.hidden;
            btn.setAttribute("aria-expanded", String(!search.hidden));
            if (search.hidden) search.value = "";
            else search.focus();
            refresh(col);
        };
        search.oninput = () => refresh(col);
    });

    /* ---- Drag and drop ----
       The server saves the stage of the column first. The card then goes
       to the top of the column. Its data gets the new stage, thus the
       overlay and the edit form agree with the column. */
    const token = document.querySelector("[name=csrfmiddlewaretoken]");
    let dragged = null;     // the card that the user drags

    document.querySelectorAll(".board__list > .lead").forEach(function (card) {
        card.addEventListener("dragstart", function (e) {
            dragged = card;
            e.dataTransfer.effectAllowed = "move";
            e.dataTransfer.setData("text/plain", card.dataset.name);   // Firefox starts a drag only with data.
            card.classList.add("is-dragging");
        });
        card.addEventListener("dragend", function () {
            dragged = null;
            card.classList.remove("is-dragging");
            document.querySelectorAll(".board__col.is-target").forEach((col) => col.classList.remove("is-target"));
        });
    });

    document.querySelectorAll(".board__col").forEach(function (col) {
        col.addEventListener("dragover", function (e) {
            if (!dragged || dragged.closest(".board__col") === col) return;
            e.preventDefault();     // The column accepts the drop.
            col.classList.add("is-target");
        });
        col.addEventListener("dragleave", function (e) {
            if (!col.contains(e.relatedTarget)) col.classList.remove("is-target");
        });
        col.addEventListener("drop", function (e) {
            e.preventDefault();
            col.classList.remove("is-target");
            const card = dragged;
            const from = card.closest(".board__col");
            const body = new FormData();
            body.append("stage", col.dataset.stageKey);
            fetch(card.dataset.stageUrl, { method: "POST", body: body, headers: { "X-CSRFToken": token.value } })
                .then(function (r) {
                    if (!r.ok) throw new Error(r.status);
                    col.querySelector(".board__list").prepend(card);
                    card.dataset.stage = col.dataset.stage;
                    const form = JSON.parse(card.dataset.form);
                    form.stage = col.dataset.stageKey;
                    card.dataset.form = JSON.stringify(form);
                    refresh(from);
                    refresh(col);
                })
                .catch(() => alert("The lead did not move. Try again."));
        });
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
