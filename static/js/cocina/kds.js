(function() {
    var clock = document.getElementById('kdsClock');
    if (clock) {
        function updateClock() {
            var now = new Date();
            clock.textContent = now.toLocaleTimeString('es-PE', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        }
        updateClock();
        setInterval(updateClock, 1000);
    }

    var timers = document.querySelectorAll('.kds-timer-value');
    function updateTimers() {
        var now = Math.floor(Date.now() / 1000);
        timers.forEach(function(el) {
            var apertura = parseInt(el.getAttribute('data-apertura'), 10);
            if (!apertura) return;
            var diff = now - apertura;
            var mins = Math.floor(diff / 60);
            var secs = diff % 60;
            var display = mins + ':' + (secs < 10 ? '0' : '') + secs;
            el.textContent = display;
            var card = el.closest('.kds-card');
            if (card && mins >= 15) {
                el.style.color = '#e74c3c';
            } else if (card && mins >= 10) {
                el.style.color = '#f39c12';
            }
        });
    }
    updateTimers();
    setInterval(updateTimers, 1000);

    // WebSocket reemplaza el autoRefresh cada 30s
    var protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    var wsUrl = protocol + '//' + window.location.host + '/ws/kds/';
    var socket = new WebSocket(wsUrl);

    socket.onmessage = function (e) {
        var data = JSON.parse(e.data);
        if (data.action === 'refresh') {
            fetch(window.location.pathname, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(function(response) { return response.text(); })
                .then(function(html) {
                    var parser = new DOMParser();
                    var doc = parser.parseFromString(html, 'text/html');
                    var newKds = doc.querySelector('.kds-container');
                    var oldKds = document.querySelector('.kds-container');
                    if (newKds && oldKds) {
                        oldKds.innerHTML = newKds.innerHTML;
                    }
                });
        }
    };

    socket.onclose = function () {
        setTimeout(function() { location.reload(); }, 3000);
    };

    var toasts = document.querySelectorAll('.kds-toast');
    toasts.forEach(function(t) {
        setTimeout(function() {
            t.style.transition = 'opacity 0.5s';
            t.style.opacity = '0';
            setTimeout(function() { t.remove(); }, 500);
        }, 4000);
    });
})();
