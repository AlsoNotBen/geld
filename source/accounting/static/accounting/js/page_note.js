/* ==========================================================================
   page_note.js  —  the Info button of the page title
   module_base.html loads it on each page of the module.

   accounting.css hides the paragraph below the page title (.page__note).
   This script adds a small grey Info button to the title of each
   .page__head with a .page__note. The button shows and hides the
   paragraph: it sets the class is-open on the head.
   ========================================================================== */
(function () {
    "use strict";

    const ICON =
        '<svg class="icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
        '<circle cx="12" cy="12" r="9"/><path d="M12 11v5" stroke-linecap="round"/>' +
        '<circle cx="12" cy="7.8" r="1" fill="currentColor" stroke="none"/></svg>';

    document.querySelectorAll(".page__head").forEach(function (head, index) {
        const title = head.querySelector(":scope > .page__title");
        const note = head.querySelector(":scope > .page__note");
        if (!title || !note) return;

        note.id = note.id || "page-note-" + index;
        const button = document.createElement("button");
        button.type = "button";
        button.className = "page__info";
        button.title = "About this page";
        button.innerHTML = ICON;
        button.setAttribute("aria-label", "About this page");
        button.setAttribute("aria-controls", note.id);
        button.setAttribute("aria-expanded", "false");
        // The button goes after the text of the title, before the Notes pill.
        title.insertBefore(button, title.querySelector(".notes-pill"));

        button.onclick = function () {
            button.setAttribute("aria-expanded", String(head.classList.toggle("is-open")));
        };
    });
})();
