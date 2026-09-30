/* ==========================================================================
   messaging.js  —  behaviour of the message overlay (all modules)
   Place this file at: messaging/static/messaging/js/messaging.js
   base.html loads it after documents.js.

   HOW A MODULE OPENS THE OVERLAY
   Give any button the attribute data-message-compose with the URL of the
   compose view. To send a file with the message, give the URL of the
   file in data-message-attach. Example:

       <button class="tool" type="button"
               data-message-compose="{% url 'messaging:compose' %}"
               data-message-attach="{% url 'documents:download' 'accounting' 'invoice' %}">
           Send
       </button>

   The script puts the form into its own <dialog>. The dialog can open
   above the document overlay. On submit, the script adds the file to the
   form data and posts all to the compose view. The answer (the form with
   the errors, or the confirmation) replaces the content of the dialog.
   ========================================================================== */

(function () {
    "use strict";

    var dialog = null;

    // Create the dialog on first use, as documents.js does.
    function ensureDialog() {
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.className = "msg-overlay";
        dialog.setAttribute("aria-label", "New message");
        document.body.appendChild(dialog);

        // A click on the backdrop hits the dialog element itself.
        dialog.addEventListener("click", function (e) {
            if (e.target === dialog || e.target.closest("[data-message-close]")) {
                dialog.close();
            }
        });
        dialog.addEventListener("close", function () { dialog.innerHTML = ""; });
        return dialog;
    }

    function readHtml(response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.text();
    }

    // Download the file. Its name comes from the Content-Disposition
    // header, e.g. "INV-2026-0042.pdf".
    function fetchFile(url) {
        return fetch(url).then(function (response) {
            if (!response.ok) throw new Error("HTTP " + response.status);
            var header = response.headers.get("Content-Disposition") || "";
            var match = /filename="([^"]+)"/.exec(header);
            var name = match ? match[1] : "attachment";
            return response.blob().then(function (blob) {
                return { blob: blob, name: name };
            });
        });
    }

    // Put a fragment into the dialog, and connect its form if it has one.
    // The argument "file" is a promise. It gives the attachment or null.
    function show(html, url, file) {
        dialog.innerHTML = html;
        var form = dialog.querySelector("[data-message-form]");
        if (!form) return;

        var status = form.querySelector("[data-message-status]");
        var submit = form.querySelector('[type="submit"]');
        var line = form.querySelector("[data-message-attachment]");

        file.then(function (f) {
            if (!f || !line) return;
            line.querySelector("span").textContent = f.name;
            line.hidden = false;
        }, function () {
            status.textContent = "The attachment did not load.";
        });

        form.addEventListener("submit", function (e) {
            e.preventDefault();
            var data = new FormData(form);
            submit.disabled = true;
            status.textContent = "The server sends the message\u2026";

            file.then(function (f) {
                if (f) data.append("attachment", f.blob, f.name);
                return fetch(url, { method: "POST", body: data });
            })
                .then(readHtml)
                .then(function (answer) { show(answer, url, file); })
                .catch(function () {
                    submit.disabled = false;
                    status.textContent = "The message did not go. Try again.";
                });
        });

        var first = form.querySelector("input:not([type=hidden]), textarea");
        if (first) first.focus();
    }

    function openOverlay(url, attachUrl) {
        var d = ensureDialog();
        d.innerHTML = '<div class="msg-overlay__note"><p>The form loads&hellip;</p></div>';
        d.showModal();

        // Start the download now. Thus the file is ready at submit.
        var file = attachUrl ? fetchFile(attachUrl) : Promise.resolve(null);

        fetch(url)
            .then(readHtml)
            .then(function (html) { show(html, url, file); })
            .catch(function () {
                d.innerHTML =
                    '<div class="msg-overlay__note">' +
                    "<p>The message form did not load. Close the overlay and try again.</p>" +
                    '<button class="tool" type="button" data-message-close>Close</button>' +
                    "</div>";
            });
    }

    // One listener serves every trigger, also a trigger in an overlay
    // that a script adds later.
    document.addEventListener("click", function (e) {
        var trigger = e.target.closest("[data-message-compose]");
        if (!trigger) return;
        e.preventDefault();
        openOverlay(
            trigger.getAttribute("data-message-compose"),
            trigger.getAttribute("data-message-attach")
        );
    });
})();
