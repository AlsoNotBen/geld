/* Upload field: drag and drop, file list, remove. Works on every [data-upload]. */
(function () {
    "use strict";

    var REMOVE_ICON = '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>';

    function formatSize(bytes) {
        var units = ["B", "KB", "MB", "GB"], i = 0;
        while (bytes >= 1024 && i < units.length - 1) { bytes /= 1024; i++; }
        return bytes.toFixed(i ? 1 : 0) + " " + units[i];
    }

    function init(root) {
        var input = root.querySelector(".upload__input");
        var zone = root.querySelector(".upload__zone");
        var list = root.querySelector(".upload__list");
        var files = [];

        // Copy the list into the real input, so a normal form submit sends it.
        function sync() {
            var dt = new DataTransfer();
            files.forEach(function (f) { dt.items.add(f); });
            input.files = dt.files;
            render();
        }

        function add(picked) {
            picked = Array.prototype.slice.call(picked);
            files = input.multiple ? files.concat(picked) : picked.slice(0, 1);
            sync();
        }

        function render() {
            list.textContent = "";
            files.forEach(function (file, index) {
                var li = document.createElement("li");
                li.className = "upload__item";

                var name = document.createElement("span");
                name.className = "upload__name";
                name.textContent = name.title = file.name;

                var size = document.createElement("span");
                size.className = "upload__size";
                size.textContent = formatSize(file.size);

                var remove = document.createElement("button");
                remove.type = "button";
                remove.className = "upload__remove";
                remove.setAttribute("aria-label", "Remove " + file.name);
                remove.innerHTML = REMOVE_ICON;
                remove.addEventListener("click", function () {
                    files.splice(index, 1);
                    sync();
                    input.focus();
                });

                li.append(name, size, remove);
                list.appendChild(li);
            });
        }

        input.addEventListener("change", function () {
            // An empty change comes from a cancelled dialog. Keep the old list.
            if (input.files.length) { add(input.files); } else { sync(); }
        });

        ["dragenter", "dragover"].forEach(function (type) {
            zone.addEventListener(type, function (e) {
                e.preventDefault();
                zone.classList.add("is-over");
            });
        });
        ["dragleave", "drop"].forEach(function (type) {
            zone.addEventListener(type, function () { zone.classList.remove("is-over"); });
        });
        zone.addEventListener("drop", function (e) {
            e.preventDefault();
            add(e.dataTransfer.files);
        });
    }

    document.querySelectorAll("[data-upload]").forEach(init);
})();