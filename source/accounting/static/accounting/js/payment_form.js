/* ==========================================================================
   payment_form.js  —  the Record Payment overlay (#payment-dialog)
   module_base.html loads it on each page of the module.

   A button with data-payment-new opens the overlay. The button can also
   fill fields of the form with data-direction, data-entity, data-amount,
   data-reference and data-account, e.g. the Pay or Receive button of a
   claim (claims.html). Such a button first resets the form. The next plain
   open resets it too, thus the values of the claim do not stay.
   The form goes to the server with fetch(), thus the overlay stays open
   and shows the errors.
   After a save, the browser goes to the Journal Entries page, where the
   draft entries of the payment wait for review.
   ========================================================================== */
(function () {
    "use strict";

    const dialog = document.getElementById("payment-dialog");
    if (!dialog) return;

    const form = dialog.querySelector("form");
    const errors = dialog.querySelector("[data-payment-errors]");
    const submit = form.querySelector("[type=submit]");

    function showErrors(list) {
        errors.textContent = "";
        list.forEach(function (text) {
            const line = document.createElement("p");
            line.textContent = text;
            errors.appendChild(line);
        });
        errors.hidden = list.length === 0;
    }

    const FIELDS = ["direction", "entity", "amount", "reference", "account"];
    let filled = false;

    document.addEventListener("click", function (e) {
        const button = e.target.closest("[data-payment-new]");
        if (!button) return;
        const values = FIELDS.filter((name) => button.dataset[name] !== undefined);
        if (values.length || filled) form.reset();
        values.forEach((name) => { form.elements[name].value = button.dataset[name]; });
        filled = values.length > 0;
        showErrors([]);
        dialog.showModal();
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
                showErrors(data.errors || ["The payment was not saved."]);
                submit.disabled = false;
            })
            .catch(function () {
                showErrors(["The payment was not saved. Try again."]);
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
