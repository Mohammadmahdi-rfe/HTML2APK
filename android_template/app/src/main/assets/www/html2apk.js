/**
 * html2apk.js — Native Bridge (Cordova-compatible style)
 * Injected automatically into every page by MainActivity.
 *
 * Usage:
 *   html2apk.device.getInfo(function(info) { console.log(info.model); });
 *   html2apk.vibrate(500);
 *   html2apk.toast.show("Hello!");
 *   html2apk.network.isOnline(function(on) { ... });
 *   html2apk.clipboard.copy("some text");
 */
(function () {
    'use strict';

    if (window.html2apk) return; // already injected

    var _cbs = {};
    var _cid = 0;

    function _reg(success, error) {
        var id = 'h2a_' + (++_cid);
        _cbs[id] = { s: success || null, e: error || null };
        return id;
    }

    var html2apk = {

        // ── internal: called from Java ──────────────────────
        _callbackSuccess: function (id, result, keep) {
            var cb = _cbs[id];
            if (cb && cb.s) cb.s(result);
            if (!keep) delete _cbs[id];
        },

        _callbackError: function (id, err) {
            var cb = _cbs[id];
            if (cb && cb.e) cb.e(err);
            delete _cbs[id];
        },

        // ── core exec ───────────────────────────────────────
        exec: function (success, error, service, action, args) {
            if (!window._H2ABridge) {
                // Running in browser — graceful no-op
                if (error) error('Native bridge not available');
                return;
            }
            var id = _reg(success, error);
            _H2ABridge.exec(service, action, JSON.stringify(args || []), id);
        },

        // ── Device ──────────────────────────────────────────
        device: {
            /**
             * success(info) — info: { platform, version, sdk, model,
             *                         manufacturer, brand, product }
             */
            getInfo: function (success, error) {
                html2apk.exec(success, error, 'Device', 'getInfo', []);
            }
        },

        // ── Vibration ───────────────────────────────────────
        /**
         * html2apk.vibrate(ms)
         * html2apk.vibrate(ms, onDone)
         */
        vibrate: function (ms, success, error) {
            html2apk.exec(success || null, error || null,
                'Vibration', 'vibrate', [ms != null ? ms : 500]);
        },

        // ── Toast ───────────────────────────────────────────
        toast: {
            /**
             * html2apk.toast.show("message")
             * html2apk.toast.show("message", "long")
             * html2apk.toast.show("message", "short", onDone)
             */
            show: function (message, duration, success, error) {
                html2apk.exec(success || null, error || null,
                    'Toast', 'show', [message, duration || 'short']);
            }
        },

        // ── Network ─────────────────────────────────────────
        network: {
            /** success(true|false) */
            isOnline: function (success, error) {
                html2apk.exec(success, error, 'Network', 'isOnline', []);
            },
            /** success("wifi"|"cellular"|"other"|"none") */
            getConnectionType: function (success, error) {
                html2apk.exec(success, error, 'Network', 'getConnectionType', []);
            }
        },

        // ── Clipboard ────────────────────────────────────────
        clipboard: {
            /** copy text to clipboard */
            copy: function (text, success, error) {
                html2apk.exec(success || null, error || null,
                    'Clipboard', 'copy', [text]);
            },
            /** success(text) */
            paste: function (success, error) {
                html2apk.exec(success, error, 'Clipboard', 'paste', []);
            }
        }
    };

    window.html2apk = html2apk;

    // Fire "html2apkready" event — analogous to Cordova's "deviceready"
    var evt = document.createEvent('Event');
    evt.initEvent('html2apkready', true, false);
    document.dispatchEvent(evt);

})();
