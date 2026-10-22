/* ==========================================================================
   bills.js  —  the New Bill overlay (#bill-dialog) of the Bills page

   The New Bill button opens the overlay. Add line copies the first line
   with empty fields. The Recurring switch shows the frequency. The form
   goes to the server with fetch(), thus the overlay stays open and shows
   the errors. After a save, the page loads again and the new draft bill
   shows in the Review part.
   ========================================================================== */
(function () {
    "use strict";

    const dialog = document.getElementById("bill-dialog");
    if (!dialog) return;

    const form = dialog.querySelector("form");
    const errors = dialog.querySelector("[data-bill-errors]");
    const submit = form.querySelector("[type=submit]");
    const lines = dialog.querySelector("[data-bill-lines]");
    const template = lines.querySelector("[data-bill-line]").cloneNode(true);

    // The frequency applies only to a recurring bill.
    const recurring = form.elements.recurring;
    const frequency = form.elements.frequency.closest(".field");
    recurring.onchange = () => { frequency.hidden = !recurring.checked; };
    recurring.onchange();

    function showErrors(list) {
        errors.textContent = "";
        list.forEach(function (text) {
            const line = document.createElement("p");
            line.textContent = text;
            errors.appendChild(line);
        });
        errors.hidden = list.length === 0;
    }

    document.querySelector("[data-bill-new]").onclick = function () {
        showErrors([]);
        dialog.showModal();
    };

    dialog.querySelector("[data-bill-line-add]").onclick = function () {
        lines.appendChild(template.cloneNode(true));
    };

    // Remove a line. The last line stays, thus the form always has one.
    lines.addEventListener("click", function (e) {
        const button = e.target.closest("[data-bill-line-remove]");
        if (button && lines.children.length > 1) button.closest("tr").remove();
    });

    form.onsubmit = function (e) {
        e.preventDefault();
        submit.disabled = true;
        fetch(form.action, { method: "POST", body: new FormData(form), headers: { "Accept": "application/json" } })
            .then((r) => r.json())
            .then(function (data) {
                if (data.redirect) {
                    window.location.href = data.redirect;
                    return;
                }
                showErrors(data.errors || ["The bill was not saved."]);
                submit.disabled = false;
            })
            .catch(function () {
                showErrors(["The bill was not saved. Try again."]);
                submit.disabled = false;
            });
    };

    /* ---- Close ---- */
    dialog.querySelector("[data-dialog-cancel]").onclick = () => dialog.close();
    // Close the dialog when the user clicks the backdrop.
    dialog.onclick = (e) => {
        if (e.target === dialog) dialog.close();
    };
})();

/* ==========================================================================
   The View overlay of a bill to review (#bill-view-ID). The View button of
   the row opens it. Deny and Approve send its form to the server.
   ========================================================================== */
(function () {
    "use strict";

    document.querySelectorAll("[data-bill-view]").forEach(function (button) {
        const view = document.getElementById(button.dataset.billView);
        button.onclick = () => view.showModal();
        view.querySelector("[data-dialog-cancel]").onclick = () => view.close();
        // Close the dialog when the user clicks the backdrop.
        view.onclick = (e) => {
            if (e.target === view) view.close();
        };
    });
})();
