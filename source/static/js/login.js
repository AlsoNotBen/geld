(function () {
    'use strict';

    // Show or hide the password. Only one eye icon is visible at a time.
    document.querySelectorAll('.field__toggle').forEach(function (btn) {
        var input = document.getElementById(btn.dataset.toggleFor);
        var eyeShow = btn.querySelector('.eye-show');
        var eyeHide = btn.querySelector('.eye-hide');
        if (!input || !eyeShow || !eyeHide) return;

        btn.addEventListener('click', function () {
            var visible = input.type === 'password';
            input.type = visible ? 'text' : 'password';

            eyeShow.classList.toggle('is-hidden', visible);
            eyeHide.classList.toggle('is-hidden', !visible);

            btn.setAttribute('aria-pressed', String(visible));
            btn.setAttribute('aria-label', visible ? 'Hide password' : 'Show password');
        });
    });

    // Block a second POST while the first one runs.
    var form = document.querySelector('.login__form');
    var submit = document.querySelector('.login__submit');

    if (form && submit) {
        form.addEventListener('submit', function () {
            submit.querySelector('.login__submit-text').textContent = submit.dataset.busyText;
            submit.disabled = true;
        });
    }
})();