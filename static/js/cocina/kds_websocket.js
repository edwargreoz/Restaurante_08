document.addEventListener('DOMContentLoaded', function () {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/kds/`;
    let socket = new WebSocket(wsUrl);

    socket.onmessage = function (e) {
        const data = JSON.parse(e.data);
        if (data.action === 'refresh') {
            fetch(window.location.pathname, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(response => response.text())
                .then(html => {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const newKds = doc.querySelector('.kds-container');
                    const oldKds = document.querySelector('.kds-container');
                    if (newKds && oldKds) {
                        oldKds.innerHTML = newKds.innerHTML;
                    }
                });
        }
    };

    socket.onclose = function () {
        setTimeout(() => { window.location.reload(); }, 3000);
    };
});
