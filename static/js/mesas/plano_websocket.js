document.addEventListener('DOMContentLoaded', function () {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/plano/`;
    let socket = new WebSocket(wsUrl);

    socket.onmessage = function (e) {
        const data = JSON.parse(e.data);
        if (data.action === 'refresh') {
            fetch(window.location.pathname, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(response => response.text())
                .then(html => {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const newPlano = doc.querySelector('.plano-container');
                    const oldPlano = document.querySelector('.plano-container');
                    if (newPlano && oldPlano) {
                        oldPlano.innerHTML = newPlano.innerHTML;
                        if (typeof initDragDrop === 'function') initDragDrop();
                    }
                });
        }
    };

    socket.onclose = function () {
        setTimeout(() => { window.location.reload(); }, 3000);
    };
});
