/* ==========================================================================
   overview.js  —  the behaviour of the Overview page
   overview.html loads it in the extra_js block.

   1. The date range of the page is a <details> element. A click outside
      it, or the Escape key, closes it.
   2. A chart segment ([data-tip]) shows its name and its value in a
      tooltip. A card graph ([data-points]) shows the date and the amount
      below the pointer. The text goes in with textContent.
   3. A segment and its legend row (the same data-key) light up together.
   4. A click on a row of the attention table ([data-href]) opens its page.
   5. The map ([data-map]) shows the address of the company. Nominatim
      finds the place of the address one time. The browser keeps the
      answer in local storage, thus the next visit sends no request.
   Without JavaScript, each item is still a link.
   ========================================================================== */
(function () {
    "use strict";

    /* ---- 1. Date range ------------------------------------------------ */
    var range = document.querySelector("[data-dash-range]");
    if (range) {
        document.addEventListener("click", function (event) {
            if (!range.contains(event.target)) { range.open = false; }
        });
        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") { range.open = false; }
        });
    }

    /* ---- 2. Tooltip --------------------------------------------------- */
    var tip = document.createElement("div");
    var tipValue = document.createElement("strong");
    var tipLabel = document.createElement("span");
    tip.className = "dash-tip";
    tip.setAttribute("role", "tooltip");
    tip.hidden = true;
    tip.append(tipValue, tipLabel);
    document.body.appendChild(tip);

    function show(value, label, x, y) {
        tipValue.textContent = value;
        tipLabel.textContent = label;
        tip.hidden = false;
        tip.style.left = Math.max(8, Math.min(x + 14, window.innerWidth - tip.offsetWidth - 8)) + "px";
        tip.style.top = Math.max(8, y - tip.offsetHeight - 12) + "px";
    }

    function hide() { tip.hidden = true; }

    document.querySelectorAll("[data-tip]").forEach(function (item) {
        item.addEventListener("pointermove", function (event) {
            show(item.dataset.tipValue, item.dataset.tip, event.clientX, event.clientY);
        });
        item.addEventListener("pointerleave", hide);
        item.addEventListener("focus", function () {
            var box = item.getBoundingClientRect();
            show(item.dataset.tipValue, item.dataset.tip, box.left + box.width / 2, box.top);
        });
        item.addEventListener("blur", hide);
    });

    function dayText(iso) {
        return new Date(iso + "T00:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
    }

    document.querySelectorAll(".card[data-points]").forEach(function (card) {
        var points = JSON.parse(card.dataset.points);
        var graph = card.querySelector(".card__spark");
        if (!graph || points.length < 2) { return; }

        var cursor = document.createElement("span");
        cursor.className = "card__cursor";
        cursor.hidden = true;
        card.appendChild(cursor);

        graph.addEventListener("pointermove", function (event) {
            var box = graph.getBoundingClientRect();
            var last = points.length - 1;
            var i = Math.max(0, Math.min(last, Math.round((event.clientX - box.left) / box.width * last)));
            cursor.style.left = (box.left - card.getBoundingClientRect().left + i / last * box.width) + "px";
            cursor.hidden = false;
            show(App.formatAmount(points[i][1].toFixed(2)), dayText(points[i][0]), event.clientX, event.clientY);
        });
        graph.addEventListener("pointerleave", function () {
            cursor.hidden = true;
            hide();
        });
    });

    /* ---- 3. Segment and legend row ------------------------------------ */
    document.querySelectorAll("[data-sunburst]").forEach(function (chart) {
        chart.querySelectorAll("[data-key]").forEach(function (item) {
            function light(on) {
                chart.classList.toggle("has-hot", on);
                chart.querySelectorAll('[data-key="' + item.dataset.key + '"]').forEach(function (match) {
                    match.classList.toggle("is-hot", on);
                });
            }
            item.addEventListener("pointerenter", function () { light(true); });
            item.addEventListener("pointerleave", function () { light(false); });
            item.addEventListener("focus", function () { light(true); });
            item.addEventListener("blur", function () { light(false); });
        });
    });

    /* ---- 4. Attention rows -------------------------------------------- */
    document.querySelectorAll("tr[data-href]").forEach(function (row) {
        row.addEventListener("click", function (event) {
            if (!event.target.closest("a")) { window.location.href = row.dataset.href; }
        });
    });

    /* ---- 5. Map ------------------------------------------------------- */
    /* The site sends no referrer to other sites (Django sets the policy
       same-origin). The tile and Nominatim servers ask for one, thus these
       requests send the origin of the site. */
    var box = document.querySelector("[data-map]");
    if (box && window.L) {
        var KEY = "overview-map:" + box.dataset.address;
        var REFERRER = "strict-origin-when-cross-origin";

        var draw = function (point) {
            var map = L.map(box, { scrollWheelZoom: false }).setView(point, 15);
            L.tileLayer(box.dataset.tiles, {
                attribution: box.dataset.attribution, maxZoom: 19, referrerPolicy: REFERRER
            }).addTo(map);
            var label = document.createElement("div");
            var name = document.createElement("strong");
            label.className = "dash-map__popup";
            name.textContent = box.dataset.name;
            label.append(name, document.createElement("br"), box.dataset.address);
            L.marker(point, { icon: L.divIcon({ className: "dash-map__pin", iconSize: [18, 18] }), title: box.dataset.name })
                .addTo(map).bindPopup(label, { minWidth: 200 });
        };

        var fail = function (text) {
            box.classList.add("is-empty");
            box.textContent = text;
        };

        var saved = null;
        try { saved = JSON.parse(localStorage.getItem(KEY)); } catch (error) { /* private mode */ }
        if (saved) {
            draw(saved);
        } else {
            fetch("https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q=" + encodeURIComponent(box.dataset.address),
                  { referrerPolicy: REFERRER })
                .then(function (response) { return response.json(); })
                .then(function (found) {
                    if (!found.length) { fail("The map cannot find this address."); return; }
                    var point = [parseFloat(found[0].lat), parseFloat(found[0].lon)];
                    try { localStorage.setItem(KEY, JSON.stringify(point)); } catch (error) { /* private mode */ }
                    draw(point);
                })
                .catch(function () { fail("The map is not available now."); });
        }
    }
})();
