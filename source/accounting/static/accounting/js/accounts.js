(function () {
    const dialog = document.getElementById("account-dialog");
    if (!dialog) return;
 
    const openBtn = document.querySelector("[data-account-new]");
    const cancelBtn = dialog.querySelector("[data-dialog-cancel]");
 
    if (openBtn) openBtn.onclick = () => dialog.showModal();
    if (cancelBtn) cancelBtn.onclick = () => dialog.close();
 
    // Close the dialog when the user clicks the backdrop.
    dialog.onclick = (e) => {
        if (e.target === dialog) dialog.close();
    };
})();

/* ==========================================================================
   The Edit Tax Code overlay (#account-tax-dialog). The Edit button of an
   account row opens it (see _accounts_table.html). Save sends the form with
   fetch(), then the page loads again. The URL keeps the open tab.
   ========================================================================== */
(function () {
    const dialog = document.getElementById("account-tax-dialog");
    if (!dialog) return;

    const form = dialog.querySelector("form");
    const errors = dialog.querySelector("[data-account-tax-errors]");

    document.addEventListener("click", function (e) {
        const btn = e.target.closest("[data-account-tax-edit]");
        if (!btn) return;
        form.setAttribute("action", btn.dataset.url);
        dialog.querySelector("[data-account-tax-name]").textContent = btn.dataset.name;
        form.elements.tax_code.value = btn.dataset.tax;
        errors.hidden = true;
        dialog.showModal();
    });

    form.onsubmit = function (e) {
        e.preventDefault();
        fetch(form.action, { method: "POST", body: new FormData(form) })
            .then(function (response) {
                if (!response.ok) throw new Error();
                window.location.reload();
            })
            .catch(function () {
                errors.textContent = "The tax code was not saved. Try again.";
                errors.hidden = false;
            });
    };

    dialog.querySelector("[data-dialog-cancel]").onclick = () => dialog.close();
    // Close the dialog when the user clicks the backdrop.
    dialog.onclick = (e) => {
        if (e.target === dialog) dialog.close();
    };
})();
