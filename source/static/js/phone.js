/* ==========================================================================
   phone.js  —  the country code of each phone input (all modules)
   base.html loads it after base.js.

   Each <input type="tel"> gets a country select at its left side. The
   select shows the flag and the dialling code of the country.

   - Type "+27 76 151 6712" or "0027761516712": the script finds the
     country code and selects South Africa.
   - Type "076 151 6712": the script uses the selected country. It
     removes the first 0 (the trunk prefix).
   - Select a country: the number gets the new country code.

   The input keeps its name, thus the form sends the full number in one
   format: "+<code> <groups>", e.g. "+27 76 151 6712". The last group
   has 4 digits. The other groups have 3 digits, the first can have less.
   The flags are emoji. The font static/vendor/flags shows them on
   systems without flag emoji (e.g. Windows).
   ========================================================================== */

(function () {
    "use strict";

    // ISO code, dialling code, name. A NANP country has "1 xxx" as its code.
    var DATA =
        "AF 93 Afghanistan;AL 355 Albania;DZ 213 Algeria;AS 1 684 American Samoa;AD 376 Andorra;AO 244 Angola;" +
        "AI 1 264 Anguilla;AG 1 268 Antigua and Barbuda;AR 54 Argentina;AM 374 Armenia;AW 297 Aruba;AU 61 Australia;" +
        "AT 43 Austria;AZ 994 Azerbaijan;BS 1 242 Bahamas;BH 973 Bahrain;BD 880 Bangladesh;BB 1 246 Barbados;" +
        "BY 375 Belarus;BE 32 Belgium;BZ 501 Belize;BJ 229 Benin;BM 1 441 Bermuda;BT 975 Bhutan;BO 591 Bolivia;" +
        "BA 387 Bosnia and Herzegovina;BW 267 Botswana;BR 55 Brazil;VG 1 284 British Virgin Islands;BN 673 Brunei;" +
        "BG 359 Bulgaria;BF 226 Burkina Faso;BI 257 Burundi;KH 855 Cambodia;CM 237 Cameroon;CA 1 Canada;" +
        "CV 238 Cape Verde;KY 1 345 Cayman Islands;CF 236 Central African Republic;TD 235 Chad;CL 56 Chile;" +
        "CN 86 China;CO 57 Colombia;KM 269 Comoros;CG 242 Congo;CD 243 Congo (DRC);CK 682 Cook Islands;" +
        "CR 506 Costa Rica;CI 225 Côte d'Ivoire;HR 385 Croatia;CU 53 Cuba;CW 599 Curaçao;CY 357 Cyprus;" +
        "CZ 420 Czechia;DK 45 Denmark;DJ 253 Djibouti;DM 1 767 Dominica;DO 1 809 Dominican Republic;EC 593 Ecuador;" +
        "EG 20 Egypt;SV 503 El Salvador;GQ 240 Equatorial Guinea;ER 291 Eritrea;EE 372 Estonia;SZ 268 Eswatini;" +
        "ET 251 Ethiopia;FK 500 Falkland Islands;FO 298 Faroe Islands;FJ 679 Fiji;FI 358 Finland;FR 33 France;" +
        "GF 594 French Guiana;PF 689 French Polynesia;GA 241 Gabon;GM 220 Gambia;GE 995 Georgia;DE 49 Germany;" +
        "GH 233 Ghana;GI 350 Gibraltar;GR 30 Greece;GL 299 Greenland;GD 1 473 Grenada;GP 590 Guadeloupe;" +
        "GU 1 671 Guam;GT 502 Guatemala;GN 224 Guinea;GW 245 Guinea-Bissau;GY 592 Guyana;HT 509 Haiti;" +
        "HN 504 Honduras;HK 852 Hong Kong;HU 36 Hungary;IS 354 Iceland;IN 91 India;ID 62 Indonesia;IR 98 Iran;" +
        "IQ 964 Iraq;IE 353 Ireland;IL 972 Israel;IT 39 Italy;JM 1 876 Jamaica;JP 81 Japan;JO 962 Jordan;" +
        "KZ 7 Kazakhstan;KE 254 Kenya;KI 686 Kiribati;XK 383 Kosovo;KW 965 Kuwait;KG 996 Kyrgyzstan;LA 856 Laos;" +
        "LV 371 Latvia;LB 961 Lebanon;LS 266 Lesotho;LR 231 Liberia;LY 218 Libya;LI 423 Liechtenstein;" +
        "LT 370 Lithuania;LU 352 Luxembourg;MO 853 Macao;MG 261 Madagascar;MW 265 Malawi;MY 60 Malaysia;" +
        "MV 960 Maldives;ML 223 Mali;MT 356 Malta;MH 692 Marshall Islands;MQ 596 Martinique;MR 222 Mauritania;" +
        "MU 230 Mauritius;MX 52 Mexico;FM 691 Micronesia;MD 373 Moldova;MC 377 Monaco;MN 976 Mongolia;" +
        "ME 382 Montenegro;MS 1 664 Montserrat;MA 212 Morocco;MZ 258 Mozambique;MM 95 Myanmar;NA 264 Namibia;" +
        "NR 674 Nauru;NP 977 Nepal;NL 31 Netherlands;NC 687 New Caledonia;NZ 64 New Zealand;NI 505 Nicaragua;" +
        "NE 227 Niger;NG 234 Nigeria;KP 850 North Korea;MK 389 North Macedonia;MP 1 670 Northern Mariana Islands;" +
        "NO 47 Norway;OM 968 Oman;PK 92 Pakistan;PW 680 Palau;PS 970 Palestine;PA 507 Panama;PG 675 Papua New Guinea;" +
        "PY 595 Paraguay;PE 51 Peru;PH 63 Philippines;PL 48 Poland;PT 351 Portugal;PR 1 787 Puerto Rico;QA 974 Qatar;" +
        "RE 262 Réunion;RO 40 Romania;RU 7 Russia;RW 250 Rwanda;KN 1 869 Saint Kitts and Nevis;LC 1 758 Saint Lucia;" +
        "VC 1 784 Saint Vincent and the Grenadines;WS 685 Samoa;SM 378 San Marino;ST 239 São Tomé and Príncipe;" +
        "SA 966 Saudi Arabia;SN 221 Senegal;RS 381 Serbia;SC 248 Seychelles;SL 232 Sierra Leone;SG 65 Singapore;" +
        "SX 1 721 Sint Maarten;SK 421 Slovakia;SI 386 Slovenia;SB 677 Solomon Islands;SO 252 Somalia;" +
        "ZA 27 South Africa;KR 82 South Korea;SS 211 South Sudan;ES 34 Spain;LK 94 Sri Lanka;SD 249 Sudan;" +
        "SR 597 Suriname;SE 46 Sweden;CH 41 Switzerland;SY 963 Syria;TW 886 Taiwan;TJ 992 Tajikistan;" +
        "TZ 255 Tanzania;TH 66 Thailand;TL 670 Timor-Leste;TG 228 Togo;TO 676 Tonga;TT 1 868 Trinidad and Tobago;" +
        "TN 216 Tunisia;TR 90 Türkiye;TM 993 Turkmenistan;TC 1 649 Turks and Caicos Islands;TV 688 Tuvalu;" +
        "UG 256 Uganda;UA 380 Ukraine;AE 971 United Arab Emirates;GB 44 United Kingdom;US 1 United States;" +
        "VI 1 340 US Virgin Islands;UY 598 Uruguay;UZ 998 Uzbekistan;VU 678 Vanuatu;VE 58 Venezuela;VN 84 Vietnam;" +
        "YE 967 Yemen;ZM 260 Zambia;ZW 263 Zimbabwe";

    var COUNTRIES = DATA.split(";").map(function (item) {
        var m = item.match(/^(\w\w) ([\d ]+?) (\D.*)$/);
        return { iso: m[1], dial: m[2], digits: m[2].replace(/ /g, ""), name: m[3], flag: flag(m[1]) };
    });

    // Two or more countries can share a code. Detection then picks this one.
    var PREFERRED = { "1": "US", "7": "RU" };
    // In these countries the first 0 is part of the number. Do not remove it.
    var KEEP_ZERO = { "IT": true, "SM": true };

    function byIso(iso) {
        return COUNTRIES.filter(function (c) { return c.iso === iso; })[0];
    }

    // The country of a number without a country code. Change it here.
    var DEFAULT = byIso("ZA");

    // "ZA" -> the two regional indicator symbols of the flag emoji.
    function flag(iso) {
        return String.fromCodePoint.apply(null, iso.split("").map(function (ch) {
            return 0x1F1E6 + ch.charCodeAt(0) - 65;
        }));
    }

    // Find the country of the digits after "+". The longest code wins.
    // The current country wins when it has the same code.
    function detect(digits, current) {
        for (var length = 4; length >= 1; length--) {
            var code = digits.slice(0, length);
            var matches = COUNTRIES.filter(function (c) { return c.digits === code; });
            if (!matches.length) continue;
            if (matches.indexOf(current) >= 0) return current;
            return byIso(PREFERRED[code]) || matches[0];
        }
        return null;
    }

    // "761516712" -> "76 151 6712"
    function group(digits) {
        if (digits.length <= 4) return digits;
        var head = digits.slice(0, -4), groups = [digits.slice(-4)];
        while (head.length) {
            groups.unshift(head.slice(-3));
            head = head.slice(0, -3);
        }
        return groups.join(" ");
    }

    function format(country, national) {
        return national ? "+" + country.dial + " " + group(national) : "";
    }

    // Read a typed number. Return { country, national }, or null when the
    // text starts with "+" or "00" but has no known country code (yet).
    function parse(text, current) {
        var digits = text.replace(/\D/g, "");
        if (/^\s*(\+|00)/.test(text)) {
            if (/^\s*00/.test(text)) digits = digits.slice(2);
            var country = detect(digits, current);
            return country && { country: country, national: digits.slice(country.digits.length) };
        }
        if (!KEEP_ZERO[current.iso]) digits = digits.replace(/^0/, "");
        return { country: current, national: digits };
    }

    var nativeValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");

    function enhance(input) {
        if (input.closest(".phone")) return;

        var box = document.createElement("span");
        box.className = "phone";
        var face = document.createElement("span");
        face.className = "phone__country";
        face.setAttribute("aria-hidden", "true");
        var select = document.createElement("select");
        select.className = "phone__select";
        select.setAttribute("aria-label", "Country code");
        select.disabled = input.disabled;
        COUNTRIES.forEach(function (c) {
            select.add(new Option(c.flag + "  " + c.name + "  +" + c.dial, c.iso));
        });
        input.parentNode.insertBefore(box, input);
        box.append(face, select, input);

        var country = DEFAULT;

        function setCountry(c) {
            country = c;
            select.value = c.iso;
            face.textContent = c.flag + " +" + c.dial;
        }

        function setText(text) {
            nativeValue.set.call(input, text);
        }

        // Read the value. Select its country. Format it when "full" is
        // true, or when the text has a country code (thus the caret
        // position is easy to keep: count the digits before it).
        function sync(full) {
            var text = nativeValue.get.call(input);
            var result = parse(text, country);
            if (!result) return;
            setCountry(result.country);
            var international = /^\s*(\+|00)/.test(text);
            if (!full && !international) return;
            var next = format(result.country, result.national);
            if (!full && !result.national) next = "+" + result.country.dial;   // Typing "+27": keep it
            if (next === text) return;

            var focused = document.activeElement === input;
            var before = focused ? text.slice(0, input.selectionStart).replace(/\D/g, "").length : 0;
            if (/^\s*00/.test(text)) before = Math.max(0, before - 2);
            setText(next);
            if (focused) {
                var pos = 0, seen = 0;
                while (pos < next.length && seen < before) {
                    if (/\d/.test(next[pos])) seen++;
                    pos++;
                }
                input.setSelectionRange(pos, pos);
            }
        }

        input.addEventListener("input", function () { sync(false); });
        input.addEventListener("change", function () { sync(true); });

        // A new country keeps the national number.
        select.addEventListener("change", function () {
            var result = parse(nativeValue.get.call(input), country);
            setCountry(byIso(select.value));
            if (result && result.national) setText(format(country, result.national));
            input.dispatchEvent(new Event("change", { bubbles: true }));
        });

        // A script can set the value, e.g. the lead form fills the fields.
        // Then the country and the format follow the new value.
        Object.defineProperty(input, "value", {
            configurable: true,
            get: function () { return nativeValue.get.call(this); },
            set: function (text) { nativeValue.set.call(this, text); sync(true); }
        });
        if (input.form) input.form.addEventListener("reset", function () {
            setTimeout(function () { setCountry(DEFAULT); sync(true); });
        });

        setCountry(DEFAULT);
        sync(true);
    }

    function enhanceAll(root) {
        root.querySelectorAll('input[type="tel"]').forEach(enhance);
    }

    enhanceAll(document);
    // A dialog can add a form later, e.g. a panel that loads with fetch().
    new MutationObserver(function (records) {
        records.forEach(function (record) {
            record.addedNodes.forEach(function (node) {
                if (node.nodeType === 1 && !node.closest(".phone")) {
                    if (node.matches('input[type="tel"]')) enhance(node);
                    else enhanceAll(node);
                }
            });
        });
    }).observe(document.body, { childList: true, subtree: true });
})();
