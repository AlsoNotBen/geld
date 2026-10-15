/* ==========================================================================
   notes.js  —  the notes of a page (see _notes.html and note_tags.py)
   _notes.html loads this file after Quill. Both scripts have the defer
   attribute, thus they run in that order when the page is ready.

   WHAT IT DOES
   1. The Note button opens the New Note overlay. A note card opens the
      overlay of its note. A link in a card keeps its own action.
   2. The description field becomes a Quill editor. If Quill did not
      load, the plain text field stays.
   3. The Permanent switch disables the expiry date.
   4. The form goes to the server with fetch(), thus the overlay stays
      open and shows the errors. After a save, the page loads again.

   MARKUP CONTRACT
       [data-note-new]          the Note button of the action bar
       [data-note-open=ID]      a note card or its title. It opens the overlay ID.
       #note-new                the New Note overlay
       [data-note-body]         the text field of the description
       [data-note-permanent]    the Permanent switch
       [data-note-errors]       the errors of the New Note overlay
       .note-sheet              each overlay of _notes.html
   ========================================================================== */
(function () {
    "use strict";

    const dialog = document.getElementById("note-new");
    if (!dialog) return;

    const form = dialog.querySelector("form");
    const errors = dialog.querySelector("[data-note-errors]");
    const submit = form.querySelector("[type=submit]");
    const body = form.querySelector("[data-note-body]");
    const permanent = form.querySelector("[data-note-permanent]");
    const expires = form.elements.expires_on;

    /* ---- Rich text ----
       The formats agree with the tags that the rich_text filter keeps.
       Tab moves to the next field, as in the other fields of the form. */
    let editor = null;
    if (window.Quill) {
        const box = document.createElement("div");
        body.after(box);
        body.hidden = true;
        editor = new Quill(box, {
            theme: "snow",
            bounds: dialog,
            placeholder: "Write the note.",
            formats: ["bold", "italic", "underline", "list", "link"],
            modules: {
                toolbar: [["bold", "italic", "underline"], [{ list: "ordered" }, { list: "bullet" }], ["link", "clean"]],
                keyboard: { bindings: { tab: false } },
            },
        });
        editor.root.setAttribute("aria-label", "Description");
    }

    function showErrors(list) {
        errors.textContent = "";
        list.forEach(function (text) {
            const line = document.createElement("p");
            line.textContent = text;
            errors.appendChild(line);
        });
        errors.hidden = list.length === 0;
    }

    /* ---- Open ---- */
    document.addEventListener("click", function (e) {
        if (e.target.closest("[data-note-new]")) {
            showErrors([]);
            dialog.showModal();
            return;
        }
        const card = e.target.closest("[data-note-open]");
        if (card && !e.target.closest("a")) document.getElementById(card.dataset.noteOpen).showModal();
    });

    permanent.onchange = () => { expires.disabled = permanent.checked; };

    /* ---- Save ----
       Quill 2 writes each space as &nbsp;. The text then cannot wrap,
       thus the spaces change back here. */
    form.onsubmit = function (e) {
        e.preventDefault();
        if (editor) body.value = editor.getText().trim() ? editor.getSemanticHTML().replaceAll("&nbsp;", " ") : "";
        submit.disabled = true;
        fetch(form.action, { method: "POST", body: new FormData(form), headers: { "Accept": "application/json" } })
            .then((r) => r.json())
            .then(function (data) {
                if (data.saved) {
                    window.location.reload();
                    return;
                }
                showErrors(data.errors || ["The note was not saved."]);
                submit.disabled = false;
            })
            .catch(function () {
                showErrors(["The note was not saved. Try again."]);
                submit.disabled = false;
            });
    };

    /* ---- Close ---- */
    document.querySelectorAll(".note-sheet").forEach(function (sheet) {
        sheet.querySelector("[data-dialog-cancel]").onclick = () => sheet.close();
        // Close the overlay when the user clicks the backdrop.
        sheet.onclick = (e) => {
            if (e.target === sheet) sheet.close();
        };
    });

    /* ---- A link to one note ----
       The Overview links to a note as page#note-ID. The page then opens it. */
    const linked = location.hash && document.getElementById(location.hash.slice(1));
    if (linked && linked.classList.contains("note-sheet")) linked.showModal();
})();
