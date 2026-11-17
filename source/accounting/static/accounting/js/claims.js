/* ==========================================================================
   claims.js  —  the overlays of the Claims page

   #claim-dialog (New Claim): the tabs set the kind of the claim (the hidden
   kind field) and its default claim account (data-claim-account). An
   element with data-for-kind shows for those kinds only (e.g. "EC": expense
   and creditor). The line rows come from #claim-line-template. Each row has
   a key: its files go as line_files_<key>. An insurance line gets the
   Insurance Recoveries account when its account is empty. The form goes to
   the server with fetch(), thus the overlay stays open and shows the errors.
   ========================================================================== */
(function () {
    "use strict";

    const dialog = document.getElementById("claim-dialog");
    if (!dialog) return;

    const form = dialog.querySelector("form");
    const errors = dialog.querySelector("[data-claim-errors]");
    const submit = form.querySelector("[type=submit]");
    const tabs = Array.from(dialog.querySelectorAll("[role=tab]"));
    const lines = dialog.querySelector("[data-claim-lines]");
    const template = document.getElementById("claim-line-template");
    const insurance = dialog.dataset.insuranceAccount;
    let nextKey = 0;

    /* The default account of a line: Insurance Recoveries for an insurance claim. */
    function setLineAccount(row, kind) {
        const account = row.querySelector("[name=line_account]");
        if (kind === "I" && !account.value) account.value = insurance;
        if (kind !== "I" && account.value === insurance) account.value = "";
    }

    function updateTotal() {
        let total = 0;
        lines.querySelectorAll("[name=line_amount]").forEach((input) => { total += Number(input.value) || 0; });
        dialog.querySelector("[data-claim-total]").textContent = total.toFixed(2);
    }

    function addLine() {
        const row = template.content.firstElementChild.cloneNode(true);
        const key = String(nextKey++);
        const files = row.querySelector("[type=file]");
        row.querySelector("[name=line_key]").value = key;
        files.name = "line_files_" + key;
        files.onchange = function () {
            row.querySelector("[data-files-label]").textContent =
                files.files.length ? files.files.length + (files.files.length === 1 ? " file" : " files") : "Add";
        };
        row.querySelector("[data-line-remove]").onclick = function () {
            row.remove();
            if (!lines.children.length) addLine();
            updateTotal();
        };
        row.querySelector("[name=line_amount]").oninput = updateTotal;
        setLineAccount(row, form.elements.kind.value);
        lines.appendChild(row);
        return row;
    }

    function selectKind(tab, focus) {
        const kind = tab.dataset.kind;
        tabs.forEach(function (item) {
            const on = item === tab;
            item.setAttribute("aria-selected", String(on));
            item.tabIndex = on ? 0 : -1;
        });
        form.elements.kind.value = kind;
        form.elements.control_account.value = tab.dataset.claimAccount;
        dialog.querySelectorAll("[data-for-kind]").forEach(function (el) {
            el.hidden = !el.dataset.forKind.includes(kind);
        });
        lines.querySelectorAll("[data-claim-line]").forEach((row) => setLineAccount(row, kind));
        if (focus) tab.focus();
    }
    tabs.forEach((tab) => tab.addEventListener("click", () => selectKind(tab)));
    dialog.querySelector("[role=tablist]").addEventListener("keydown", function (e) {
        const i = tabs.indexOf(document.activeElement);
        const step = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
        if (i === -1 || !step) return;
        e.preventDefault();
        selectKind(tabs[(i + step + tabs.length) % tabs.length], true);
    });

    function showErrors(list) {
        errors.textContent = "";
        list.forEach(function (text) {
            const line = document.createElement("p");
            line.textContent = text;
            errors.appendChild(line);
        });
        errors.hidden = list.length === 0;
    }

    dialog.querySelector("[data-line-add]").onclick = () => addLine().querySelector("[name=line_reason]").focus();

    document.querySelector("[data-claim-new]").onclick = function () {
        showErrors([]);
        if (!lines.children.length) addLine();
        selectKind(tabs[0]);
        dialog.showModal();
    };

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
                showErrors(data.errors || ["The claim was not saved."]);
                submit.disabled = false;
            })
            .catch(function () {
                showErrors(["The claim was not saved. Try again."]);
                submit.disabled = false;
            });
    };

    dialog.querySelector("[data-dialog-cancel]").onclick = () => dialog.close();
    dialog.onclick = (e) => { if (e.target === dialog) dialog.close(); };
})();

/* The View overlay of a claim to review (#claim-view-ID). */
(function () {
    "use strict";

    document.querySelectorAll("[data-claim-view]").forEach(function (button) {
        const view = document.getElementById(button.dataset.claimView);
        button.onclick = () => view.showModal();
        view.querySelector("[data-dialog-cancel]").onclick = () => view.close();
        view.onclick = (e) => { if (e.target === view) view.close(); };
    });
})();
