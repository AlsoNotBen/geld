/* ==========================================================================
   payment_form.js  —  the Record Payment overlay (#payment-dialog)
   module_base.html loads it on each page of the module.

   A button with data-payment-new opens the overlay. The form goes to the
   server with fetch(), thus the overlay stays open and shows the errors.
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

    document.addEventListener("click", function (e) {
        if (!e.target.closest("[data-payment-new]")) return;
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
