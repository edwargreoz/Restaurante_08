document.addEventListener('DOMContentLoaded', function () {
    const containerSel = '.plano-container';
    let socket = null;
    let reconnectTimeout = null;
    let debounceTimer = null;

    function connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        socket = new WebSocket(`${protocol}//${window.location.host}/ws/plano/`);

        socket.onopen = function () {
            console.log('[Plano] WebSocket conectado');
        };

        socket.onmessage = function (e) {
            const data = JSON.parse(e.data);
            if (data.action === 'refresh') {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(function () {
                    fetch(window.location.pathname, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                        .then(function (response) { return response.text(); })
                        .then(function (html) {
                            const parser = new DOMParser();
                            const doc = parser.parseFromString(html, 'text/html');
                            const newContent = doc.querySelector(containerSel);
                            const oldContent = document.querySelector(containerSel);
                            if (newContent && oldContent) {
                                oldContent.innerHTML = newContent.innerHTML;
                                if (typeof initDragDrop === 'function') initDragDrop();
                            }
                        });
                }, 100);
            }
        };

        socket.onclose = function () {
            console.log('[Plano] WebSocket cerrado, reconectando en 3s...');
            reconnectTimeout = setTimeout(connect, 3000);
        };

        socket.onerror = function (err) {
            console.error('[Plano] WebSocket error:', err);
            socket.close();
        };
    }

    connect();
});
