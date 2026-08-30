/* ==========================================================================
   journals.js  —  the tab control of the Accounting journals page
   Place this file at: accounting/static/accounting/js/journals.js
   journals.html loads it in the extra_js block of base.html.

   WHAT IT DOES
   The script shows one panel and hides the others. It also writes the key
   of the tab into the URL, thus a link or a page reload opens the same
   tab. Example: /accounting/journals/?journal=sales

   MARKUP CONTRACT
       [data-tabset]                  the container
       [data-tabset-param="journal"]  the name of the URL parameter
                                      (leave it out to keep the URL clean)
       [role="tab"][data-tab=KEY]     the button
       [data-panel=KEY]               the panel that the button shows
   The button must also point at its panel with aria-controls.

   The script is general. Put the same attributes on another page to get
   the same behaviour.
   ========================================================================== */
(function () {
    'use strict';

    function setUp(root) {
        var tabs = Array.prototype.slice.call(root.querySelectorAll('[role="tab"]'));
        if (tabs.length < 2) { return; }

        var param = root.getAttribute('data-tabset-param') || '';

        function panelOf(tab) {
            return document.getElementById(tab.getAttribute('aria-controls'));
        }

        /* Show one tab. The two flags keep the first call quiet: it must
           not move the focus, and it must not touch the URL. */
        function select(tab, moveFocus, writeUrl) {
            tabs.forEach(function (item) {
                var isCurrent = (item === tab);
                var panel = panelOf(item);

                item.setAttribute('aria-selected', isCurrent ? 'true' : 'false');
                item.tabIndex = isCurrent ? 0 : -1;
                if (panel) { panel.hidden = !isCurrent; }
            });

            if (moveFocus) { tab.focus(); }
            if (writeUrl) { remember(tab.getAttribute('data-tab')); }
        }

        /* The URL keeps the choice. replaceState makes no new history
           entry, thus the Back button leaves the page as the user expects. */
        function remember(key) {
            if (!param || !key || !window.history || !window.history.replaceState) { return; }
            try {
                var url = new URL(window.location.href);
                url.searchParams.set(param, key);
                window.history.replaceState(null, '', url);
            } catch (error) {
                /* An old browser has no URL object. The tabs still work. */
            }
        }

        function tabFor(key) {
            if (!key) { return null; }
            return tabs.filter(function (item) {
                return item.getAttribute('data-tab') === key;
            })[0] || null;
        }

        /* ---- Pointer ---- */
        tabs.forEach(function (tab) {
            tab.addEventListener('click', function () {
                select(tab, false, true);
            });
        });

        /* ---- Keyboard (the pattern of the WAI-ARIA tabs) ----
           The arrow keys move along the row. Home and End go to the ends.
           A button gets Enter and Space from the browser. */
        root.addEventListener('keydown', function (event) {
            var current = tabs.indexOf(document.activeElement);
            if (current === -1) { return; }

            var next = -1;
            if (event.key === 'ArrowRight') { next = (current + 1) % tabs.length; }
            else if (event.key === 'ArrowLeft') { next = (current - 1 + tabs.length) % tabs.length; }
            else if (event.key === 'Home') { next = 0; }
            else if (event.key === 'End') { next = tabs.length - 1; }
            if (next === -1) { return; }

            event.preventDefault();
            select(tabs[next], true, true);
        });

        /* ---- The first tab ----
           The URL wins. If it holds no key, the markup decides. */
        var start = null;
        if (param) {
            try {
                start = tabFor(new URL(window.location.href).searchParams.get(param));
            } catch (error) {
                start = null;
            }
        }
        if (!start) {
            start = tabs.filter(function (item) {
                return item.getAttribute('aria-selected') === 'true';
            })[0] || tabs[0];
        }
        select(start, false, false);
    }

    function init() {
        Array.prototype.forEach.call(document.querySelectorAll('[data-tabset]'), setUp);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();