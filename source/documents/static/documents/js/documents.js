/* ==========================================================================
   documents.js  —  behaviour of the document overlay (all modules)
   Place this file at: documents/static/documents/js/documents.js
   base.html loads it after base.js.

   HOW A MODULE OPENS THE OVERLAY
   Give any button or link the attribute data-doc-overlay with the URL
   of the panel view. Example:

       <button class="tool tool--primary" type="button"
               data-doc-overlay="{% url 'documents:panel' 'accounting' 'invoice' %}">
           New Invoice
       </button>

   The script fetches the panel fragment, puts it into one shared
   <dialog>, and wires the options form to the preview frame and to
   the download link. The dialog backdrop blurs the page behind it
   (see documents.css).
   ========================================================================== */

(function () {
    "use strict";

    var dialog = null;

    // Create the shared dialog on first use. base.html then stays free
    // of markup for the overlay.
    function ensureDialog() {
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.className = "doc-overlay";
        dialog.setAttribute("aria-label", "Document preview");
        document.body.appendChild(dialog);

        // A click on the backdrop hits the dialog element itself. A click
        // inside the panel hits a child. Close on the first case only.
        dialog.addEventListener("click", function (e) {
            if (e.target === dialog) dialog.close();
        });
        // Drop the content on close, so that the preview stops.
        dialog.addEventListener("close", function () { dialog.innerHTML = ""; });
        return dialog;
    }

    function serialize(form) {
        return new URLSearchParams(new FormData(form)).toString();
    }

    // Connect the options form to the preview frame and to the download
    // link. The preview refreshes when the focus leaves a changed field
    // (the "change" event), not on each keystroke. The refresh button
    // in the panel head refreshes it at any time.
    function wirePanel(panel) {
        var form = panel.querySelector("[data-doc-form]");
        var frame = panel.querySelector("[data-doc-preview]");
        var download = panel.querySelector("[data-doc-download]");
        var send = panel.querySelector("[data-doc-send]");
        var previewUrl = panel.getAttribute("data-preview-url");
        var downloadUrl = panel.getAttribute("data-download-url");

        function setDownload(query) {
            download.href = downloadUrl + "?" + query;
            if (send) send.setAttribute("data-message-attach", download.href);
        }

        function refresh() {
            var query = serialize(form);
            frame.src = previewUrl + "?" + query;
            setDownload(query);
        }

        if (form) {
            // "change" fires when a changed text field loses the focus,
            // and at once for a select or a date picker.
            form.addEventListener("change", refresh);
            form.addEventListener("submit", function (e) {
                e.preventDefault();
                refresh();
            });
            form.querySelectorAll("[data-doc-lines]").forEach(function (box) {
                wireLines(box, form);
            });
            panel.querySelectorAll("[data-doc-refresh]").forEach(function (btn) {
                btn.addEventListener("click", refresh);
            });
            // Align the download link with the initial form state.
            setDownload(serialize(form));
        }

        panel.querySelectorAll("[data-doc-close]").forEach(function (btn) {
            btn.addEventListener("click", function () { dialog.close(); });
        });

        // The Save button issues the document, as a download does, but
        // makes no PDF. E.g. an invoice gets its journal entry. After a
        // save, the page loads again with a GET, thus the browser does not
        // send a page form again. An error shows in the hint.
        var save = panel.querySelector("[data-doc-save]");
        var hint = panel.querySelector(".doc-panel__hint");
        if (save && form) save.addEventListener("click", function () {
            function fail(errors) {
                hint.textContent = errors.join(" ");
                hint.classList.add("is-error");
                save.disabled = false;
            }
            save.disabled = true;
            fetch(panel.getAttribute("data-save-url"), {
                method: "POST",
                body: new FormData(form),
                headers: { "X-CSRFToken": panel.getAttribute("data-csrf"), "Accept": "application/json" }
            })
                .then(function (response) { return response.json(); })
                .then(function (data) {
                    if (data.saved) {
                        window.location.assign(window.location.pathname + window.location.search);
                        return;
                    }
                    fail(data.errors || ["The document was not saved."]);
                })
                .catch(function () { fail(["The document was not saved. Try again."]); });
        });
    }

    // The line item editor. The row inputs have no name attribute, thus
    // the query string carries the hidden JSON input only. This function
    // keeps that JSON in step with the rows.
    function wireLines(box, form) {
        var hidden = box.querySelector('input[type="hidden"][name]');
        var rowsBox = box.querySelector("[data-doc-lines-rows]");

        function sync() {
            var data = [];
            rowsBox.querySelectorAll("[data-doc-line]").forEach(function (row) {
                var item = {};
                row.querySelectorAll("[data-line-field]").forEach(function (input) {
                    item[input.getAttribute("data-line-field")] = input.value;
                });
                data.push(item);
            });
            hidden.value = JSON.stringify(data);
        }

        // A click on add or remove gives no change event. Sync, then
        // tell the form, so that the preview refreshes.
        function notify() {
            sync();
            form.dispatchEvent(new Event("change"));
        }

        // Build one row. Keep the structure equal to _line_row() in
        // documents/forms.py.
        function buildRow(item) {
            var row = document.createElement("div");
            row.className = "doc-lines__row";
            row.setAttribute("data-doc-line", "");
            row.innerHTML =
                '<input type="text" data-line-field="description" placeholder="Description" aria-label="Description">' +
                '<input type="hidden" data-line-field="unit">' +
                '<input type="number" data-line-field="quantity" min="0" step="any" aria-label="Quantity">' +
                '<input type="number" data-line-field="unit_price" min="0" step="0.01" aria-label="Unit price">' +
                '<button type="button" class="doc-lines__remove" data-line-remove aria-label="Remove the line">&times;</button>';
            row.querySelector('[data-line-field="description"]').value = item.description || "";
            row.querySelector('[data-line-field="unit"]').value = item.unit || "";
            row.querySelector('[data-line-field="quantity"]').value = item.quantity || "1";
            row.querySelector('[data-line-field="unit_price"]').value = item.unit_price || "";
            return row;
        }

        // Typing in a row keeps the JSON current at once. The preview
        // waits for the "change" event, which fires when the row input
        // loses the focus.
        box.addEventListener("input", sync);

        box.addEventListener("click", function (e) {
            if (e.target.closest("[data-line-remove]")) {
                e.target.closest("[data-doc-line]").remove();
                notify();
                return;
            }
            if (e.target.closest("[data-line-add-catalog]")) {
                var select = box.querySelector("[data-line-catalog]");
                var option = select.options[select.selectedIndex];
                if (!option || !option.value) return;
                rowsBox.appendChild(buildRow({
                    description: option.getAttribute("data-description"),
                    unit: option.getAttribute("data-unit"),
                    unit_price: option.getAttribute("data-price"),
                    quantity: "1"
                }));
                select.selectedIndex = 0;
                notify();
                return;
            }
            if (e.target.closest("[data-line-add-custom]")) {
                var row = buildRow({ description: "", unit: "", quantity: "1", unit_price: "0.00" });
                rowsBox.appendChild(row);
                row.querySelector("input").focus();
                notify();
            }
        });

        sync();
    }

    function showError(message) {
        dialog.innerHTML =
            '<div class="doc-overlay__loading">' +
            "<p>" + message + "</p>" +
            '<button class="tool" type="button" data-doc-close>Close</button>' +
            "</div>";
        dialog.querySelector("[data-doc-close]").addEventListener("click", function () {
            dialog.close();
        });
    }

    function openOverlay(url) {
        var d = ensureDialog();
        d.innerHTML = '<div class="doc-overlay__loading"><p>The preview loads&hellip;</p></div>';
        d.showModal();

        fetch(url, { headers: { "X-Requested-With": "fetch" } })
            .then(function (response) {
                if (!response.ok) throw new Error("HTTP " + response.status);
                return response.text();
            })
            .then(function (html) {
                d.innerHTML = html;
                var panel = d.querySelector("[data-doc-panel]");
                if (panel) wirePanel(panel);
            })
            .catch(function () {
                showError("The document panel did not load. Close the overlay and try again.");
            });
    }

    // One listener serves every trigger, also a trigger that a later
    // script adds to the page.
    document.addEventListener("click", function (e) {
        var trigger = e.target.closest("[data-doc-overlay]");
        if (!trigger) return;
        e.preventDefault();
        openOverlay(trigger.getAttribute("data-doc-overlay"));
    });

    // The search button of a widget (data-doc-search, see _search_button
    // in documents/forms.py) opens a search field below its row. The
    // field searches the options of the select in the same row, e.g. the
    // customers or the catalog items. A second click closes the field.
    function toggleSearch(button) {
        var row = button.parentElement;
        var select = row.querySelector("select");
        var open = row.nextElementSibling;
        if (open && open.hasAttribute("data-doc-search-box")) {
            open.remove();
            return;
        }

        var box = document.createElement("div");
        box.className = "doc-search";
        box.setAttribute("data-doc-search-box", "");
        box.innerHTML =
            '<input type="search" placeholder="Type to search" autocomplete="off">' +
            '<div class="doc-search__list"></div>';
        var input = box.querySelector("input");
        var list = box.querySelector(".doc-search__list");
        input.setAttribute("aria-label", button.getAttribute("aria-label"));
        row.after(box);

        // Each word of the search must be in the text of the option.
        function show() {
            var words = input.value.toLowerCase().split(/\s+/).filter(Boolean);
            list.innerHTML = "";
            Array.prototype.forEach.call(select.options, function (option) {
                var text = option.text.toLowerCase();
                if (!option.value) return;
                if (!words.every(function (word) { return text.indexOf(word) >= 0; })) return;
                var item = document.createElement("button");
                item.type = "button";
                item.className = "doc-search__item";
                item.textContent = option.text;
                item.addEventListener("click", function () { pick(option); });
                list.appendChild(item);
            });
            if (!list.children.length) list.innerHTML = '<p class="doc-search__none">No match.</p>';
        }

        // Select the option. In the catalog row, the "+" button then adds
        // the item as a line (see wireLines). The change event refreshes
        // the preview.
        function pick(option) {
            select.value = option.value;
            box.remove();
            var add = row.querySelector("[data-line-add-catalog]");
            if (add) {
                add.click();
            } else {
                select.dispatchEvent(new Event("change", { bubbles: true }));
            }
            select.focus();
        }

        input.addEventListener("input", show);
        // The search field is not an option of the document. Thus its
        // change event must not refresh the preview.
        input.addEventListener("change", function (e) { e.stopPropagation(); });
        // Enter selects the first result. It does not send the form.
        input.addEventListener("keydown", function (e) {
            if (e.key !== "Enter") return;
            e.preventDefault();
            var first = list.querySelector("button");
            if (first) first.click();
        });
        // Escape closes the search field, not the overlay.
        box.addEventListener("keydown", function (e) {
            if (e.key !== "Escape") return;
            e.preventDefault();
            box.remove();
            button.focus();
        });

        show();
        input.focus();
    }

    document.addEventListener("click", function (e) {
        var button = e.target.closest("[data-doc-search]");
        if (button) toggleSearch(button);
    });

    // A widget button with data-doc-action opens nothing itself. This
    // listener turns the click into one "doc:action" event. Another
    // script links the action, e.g. the button "new-customer" to a
    // customer overlay:
    //
    //     document.addEventListener("doc:action", function (e) {
    //         if (e.detail.action === "new-customer") { /* open it */ }
    //     });
    document.addEventListener("click", function (e) {
        var trigger = e.target.closest("[data-doc-action]");
        if (!trigger) return;
        document.dispatchEvent(new CustomEvent("doc:action", {
            detail: { action: trigger.getAttribute("data-doc-action"), trigger: trigger }
        }));
    });
})();