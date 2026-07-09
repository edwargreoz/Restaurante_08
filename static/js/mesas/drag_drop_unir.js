document.addEventListener('DOMContentLoaded', function () {
    var mesas = document.querySelectorAll('.mesa-card');

    function getCSRFToken() {
        var input = document.querySelector('[name=csrfmiddlewaretoken]');
        if (input) return input.value;
        var match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : '';
    }

    // --- Desunir desde el panel ---
    document.querySelectorAll('.union-panel-desunir-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var unionId = this.getAttribute('data-union-id');
            var item = this.closest('.union-panel-item');
            desunir(unionId, item);
        });
    });

    function desunir(unionId, targetEl) {
        targetEl.style.opacity = '0.5';
        fetch('/mesas/deshacer-union/' + unionId + '/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCSRFToken() },
        })
        .then(function (response) {
            if (!response.ok) throw new Error('Error al desunir');
            targetEl.classList.add('desunir-success');
            var cards = document.querySelectorAll('.mesa-card');
            cards.forEach(function (c) { c.classList.add('desunir-success'); });
            setTimeout(function () { window.location.reload(); }, 800);
        })
        .catch(function (error) {
            targetEl.style.opacity = '1';
            targetEl.classList.add('shake-error');
            var cards = document.querySelectorAll('.mesa-card');
            cards.forEach(function (c) { c.classList.add('shake-error'); });
            setTimeout(function () {
                targetEl.classList.remove('shake-error');
                cards.forEach(function (c) { c.classList.remove('shake-error'); });
            }, 600);
            alert('Error al desunir: ' + error.message);
        });
    }

    // --- Drag & Drop para unir ---
    mesas.forEach(function (mesa) {
        if (mesa.hasAttribute('data-union-id')) return;
        mesa.setAttribute('draggable', 'true');

        mesa.addEventListener('dragstart', function (e) {
            e.dataTransfer.setData('text/plain', this.dataset.mesaId);
            this.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
        });

        mesa.addEventListener('dragend', function () {
            this.classList.remove('dragging');
            document.querySelectorAll('.mesa-card.drop-target').forEach(function (el) {
                el.classList.remove('drop-target');
            });
        });

        mesa.addEventListener('dragover', function (e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            this.classList.add('drop-target');
        });

        mesa.addEventListener('dragleave', function () {
            this.classList.remove('drop-target');
        });

        mesa.addEventListener('drop', function (e) {
            e.preventDefault();
            var destinoCard = this;
            destinoCard.classList.remove('drop-target');

            if (destinoCard.hasAttribute('data-union-id')) return;

            var origenId = parseInt(e.dataTransfer.getData('text/plain'));
            var destinoId = parseInt(destinoCard.dataset.mesaId);
            var origenCard = document.querySelector('.mesa-card[data-mesa-id="' + origenId + '"]');

            if (origenId === destinoId) return;

            fetch('/api/v1/uniones-mesas/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken(),
                },
                body: JSON.stringify({ mesas_ids: [origenId, destinoId] }),
            })
            .then(function (response) {
                if (!response.ok) {
                    return response.text().then(function (body) {
                        throw new Error('HTTP ' + response.status + ': ' + body);
                    });
                }
                destinoCard.classList.add('drop-success');
                if (origenCard) origenCard.classList.add('drop-success');
                setTimeout(function () { window.location.reload(); }, 1000);
            })
            .catch(function (error) {
                destinoCard.classList.add('shake-error');
                if (origenCard) origenCard.classList.add('shake-error');
                setTimeout(function () {
                    destinoCard.classList.remove('shake-error');
                    if (origenCard) origenCard.classList.remove('shake-error');
                }, 600);
                alert('Error al unir mesas: ' + error.message);
            });
        });
    });
});
