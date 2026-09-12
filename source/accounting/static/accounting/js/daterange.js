/* accounting/static/accounting/js/daterange.js
   ---------------------------------------------------------------------------
   The global date range of the module bar.

   Local storage holds the choice of the user. The script copies the same
   value into a cookie, because the server must read the range to filter
   its queries. The page reloads after a change, thus each view receives
   the new dates.

   Storage value:  {"key": "fy", "start": "2026-03-01", "end": "2027-02-28"}
   ------------------------------------------------------------------------ */
(function () {
    var root = document.querySelector('[data-daterange]');
    if (!root) { return; }

    var KEY    = 'acct_range';
    var btn    = root.querySelector('[data-range-btn]');
    var panel  = root.querySelector('[data-range-panel]');
    var label  = root.querySelector('[data-range-label]');
    var startI = root.querySelector('[data-range-start]');
    var endI   = root.querySelector('[data-range-end]');

    var LABELS = {
        fy:      'Current Financial Year',
        fy_last: 'Last Financial Year',
        quarter: 'Current Quarter',
        month:   'Current Month',
        ytd:     'Year to Date'
    };

    /* ---- Dates ---------------------------------------------------- */
    function iso(date) { return date.toISOString().slice(0, 10); }

    function shift(text, years) {
        var d = new Date(text + 'T00:00:00');
        d.setFullYear(d.getFullYear() + years);
        return iso(d);
    }

    /* The financial year comes from the server, in the data attributes. */
    function preset(key) {
        var now = new Date(), y = now.getFullYear(), q = Math.floor(now.getMonth() / 3);
        if (key === 'fy')      { return [root.dataset.fyStart, root.dataset.fyEnd]; }
        if (key === 'fy_last') { return [shift(root.dataset.fyStart, -1), shift(root.dataset.fyEnd, -1)]; }
        if (key === 'quarter') { return [iso(new Date(y, q * 3, 1)), iso(new Date(y, q * 3 + 3, 0))]; }
        if (key === 'month')   { return [iso(new Date(y, now.getMonth(), 1)), iso(new Date(y, now.getMonth() + 1, 0))]; }
        if (key === 'ytd')     { return [iso(new Date(y, 0, 1)), iso(now)]; }
        return null;
    }

    /* ---- Storage -------------------------------------------------- */
    function read() {
        try { return JSON.parse(localStorage.getItem(KEY)); } catch (e) { return null; }
    }

    function write(range) {
        try { localStorage.setItem(KEY, JSON.stringify(range)); } catch (e) { /* private mode */ }
        document.cookie = KEY + '=' + range.key + '|' + range.start + '|' + range.end +
                          ';path=/;max-age=31536000;samesite=lax';
    }

    function text(range) {
        return LABELS[range.key] || (range.start + ' – ' + range.end);
    }

    /* ---- Start ---------------------------------------------------- */
    /* The guard permits one sync reload only. Without it the page can
       refresh without end, e.g. if settings.py has no date_range
       context processor, or if the request has no company. The server
       then sends no dates, thus a comparison never agrees. */
    var GUARD = KEY + ':sync';

    function guard(value) {
        try {
            if (value) { sessionStorage.setItem(GUARD, '1'); }
            else { sessionStorage.removeItem(GUARD); }
        } catch (e) { /* private mode */ }
        try { return sessionStorage.getItem(GUARD); } catch (e) { return '1'; }
    }

    var server  = { key: root.dataset.key, start: root.dataset.start, end: root.dataset.end };
    var current = read();

    if (!current || !current.start || !current.end) {
        /* No choice yet. Keep the default of the server. */
        current = server;
        write(current);
    } else if (current.start === server.start && current.end === server.end) {
        guard(false);                       /* the server agrees */
    } else if (server.start && !guard()) {
        /* The cookie is absent or old. Write it again, then get the
           page one time with the correct range. */
        write(current);
        guard(true);
        window.location.reload();
        return;
    }

    label.textContent = text(current);
    startI.value = current.start;
    endI.value   = current.end;

    /* ---- Panel ---------------------------------------------------- */
    function open(show) {
        panel.hidden = !show;
        btn.setAttribute('aria-expanded', show ? 'true' : 'false');
    }

    btn.addEventListener('click', function () { open(panel.hidden); });

    root.querySelector('[data-range-cancel]').addEventListener('click', function () {
        startI.value = current.start;
        endI.value   = current.end;
        open(false);
    });

    document.addEventListener('click', function (event) {
        if (!root.contains(event.target)) { open(false); }
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') { open(false); }
    });

    /* A preset fills the two fields. The Apply button sends the range. */
    root.querySelectorAll('[data-preset]').forEach(function (item) {
        item.addEventListener('click', function () {
            var dates = preset(item.dataset.preset);
            if (!dates) { return; }
            apply({ key: item.dataset.preset, start: dates[0], end: dates[1] });
        });
    });

    root.querySelector('[data-range-apply]').addEventListener('click', function () {
        if (!startI.value || !endI.value || startI.value > endI.value) {
            endI.setCustomValidity('The end date must come after the start date.');
            endI.reportValidity();
            return;
        }
        apply({ key: 'custom', start: startI.value, end: endI.value });
    });

    endI.addEventListener('input', function () { endI.setCustomValidity(''); });

    function apply(range) {
        write(range);
        guard(false);
        window.location.reload();
    }
})();