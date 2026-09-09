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
 
