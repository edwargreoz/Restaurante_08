(function () {
    var containerSel = '.kds-container';
    var socket = null;
    var reconnectTimeout = null;
    var debounceTimer = null;

    function connect() {
        var protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        socket = new WebSocket(protocol + '//' + window.location.host + '/ws/kds/');

        socket.onopen = function () {
            console.log('[KDS] WebSocket conectado');
        };

        socket.onmessage = function (e) {
            var data = JSON.parse(e.data);
            if (data.action === 'refresh') {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(function () {
                    fetch(window.location.pathname, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                        .then(function (response) { return response.text(); })
                        .then(function (html) {
                            var parser = new DOMParser();
                            var doc = parser.parseFromString(html, 'text/html');
                            var newContent = doc.querySelector(containerSel);
                            var oldContent = document.querySelector(containerSel);
                            if (newContent && oldContent) {
                                oldContent.innerHTML = newContent.innerHTML;
                            }
                        });
                }, 100);
            }
        };

        socket.onclose = function () {
            console.log('[KDS] WebSocket cerrado, reconectando en 3s...');
            reconnectTimeout = setTimeout(connect, 3000);
        };

        socket.onerror = function (err) {
            console.error('[KDS] WebSocket error:', err);
            socket.close();
        };
    }

    connect();
})();
