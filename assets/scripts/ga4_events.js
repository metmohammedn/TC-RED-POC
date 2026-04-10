(function() {
    "use strict";

    function ga(eventName, params) {
        if (typeof gtag === "function") {
            gtag("event", eventName, params);
        }
    }

    function onReady(fn) {
        if (document.readyState !== "loading") {
            setTimeout(fn, 1500);
        } else {
            document.addEventListener("DOMContentLoaded", function() {
                setTimeout(fn, 1500);
            });
        }
    }

    function debounce(fn, ms) {
        var timer;
        return function() {
            clearTimeout(timer);
            var args = arguments;
            var ctx = this;
            timer = setTimeout(function() { fn.apply(ctx, args); }, ms);
        };
    }

    onReady(function() {
        // Track system selection
        var systemSelect = document.getElementById("cyclone-system-select");
        if (systemSelect) {
            new MutationObserver(debounce(function() {
                ga("tc_system_select", { component: "cyclone-system-select" });
            }, 1000)).observe(systemSelect, { attributes: true, subtree: true });
        }

        // Track advisory selection
        var advisorySelect = document.getElementById("cyclone-advisory-select");
        if (advisorySelect) {
            new MutationObserver(debounce(function() {
                ga("tc_advisory_select", { component: "cyclone-advisory-select" });
            }, 1000)).observe(advisorySelect, { attributes: true, subtree: true });
        }

        // Track client selection
        var clientSelect = document.getElementById("cyclone-client-select");
        if (clientSelect) {
            new MutationObserver(debounce(function() {
                ga("tc_client_select", { component: "cyclone-client-select" });
            }, 1000)).observe(clientSelect, { attributes: true, subtree: true });
        }

        // Track toggle switches and button clicks
        document.addEventListener("click", function(e) {
            var target = e.target;
            var id = target.id || (target.closest && target.closest("[id]") || {}).id;

            if (id === "cyclone-export-csv-btn" || (target.closest && target.closest("#cyclone-export-csv-btn"))) {
                ga("tc_export_csv", { component: "cyclone-export-csv-btn" });
            }
            if (id === "cyclone-reset-view-btn" || (target.closest && target.closest("#cyclone-reset-view-btn"))) {
                ga("tc_reset_view", { component: "cyclone-reset-view-btn" });
            }
        });
    });
})();
