document.addEventListener('DOMContentLoaded', function () {
    var mesas = document.querySelectorAll('.mesa-card');

    function getCSRFToken() {
        var input = document.querySelector('[name=csrfmiddlewaretoken]');
        if (input) return input.value;
        var match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : '';
    }

    // --- Drag & Drop para unir ---
    mesas.forEach(function (mesa) {
        mesa.setAttribute('draggable', 'true');

        var link = mesa.querySelector('a.card-link-mesa');
        if (link) {
            link.addEventListener('dragover', function (e) {
                e.preventDefault();
                e.stopPropagation();
            });
            link.addEventListener('drop', function (e) {
                e.preventDefault();
                e.stopPropagation();
                mesa.dispatchEvent(new DragEvent('drop', {
                    dataTransfer: e.dataTransfer,
                    bubbles: false
                }));
            });
            link.addEventListener('dragenter', function (e) {
                e.preventDefault();
                e.stopPropagation();
            });
            link.addEventListener('dragleave', function (e) {
                e.stopPropagation();
            });
        }

        mesa.addEventListener('dragstart', function (e) {
            var transferData = {
                mesaId: this.dataset.mesaId,
                unionId: this.hasAttribute('data-union-id') ? this.getAttribute('data-union-id') : null
            };
            e.dataTransfer.setData('application/json', JSON.stringify(transferData));
            // Fallback for older browsers
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

        mesa.addEventListener('dragenter', function (e) {
            e.preventDefault();
            this.classList.add('drop-target');
            return false;
        });

        mesa.addEventListener('dragover', function (e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            return false;
        });

        mesa.addEventListener('dragleave', function () {
            this.classList.remove('drop-target');
        });

        mesa.addEventListener('drop', function (e) {
            e.preventDefault();
            var destinoCard = this;
            destinoCard.classList.remove('drop-target');

            var transferDataStr = e.dataTransfer.getData('application/json');
            var origenId, origenUnionId;

            if (transferDataStr) {
                var td = JSON.parse(transferDataStr);
                origenId = parseInt(td.mesaId);
                origenUnionId = td.unionId;
            } else {
                origenId = parseInt(e.dataTransfer.getData('text/plain'));
                origenUnionId = null;
            }

            if (!origenId || isNaN(origenId)) return;

            var origenCard = document.querySelector('.mesa-card[data-mesa-id="' + origenId + '"]');

            var destinoId = parseInt(destinoCard.dataset.mesaId);
            if (origenId === destinoId) return;

            var unionIdToTarget = null;
            var mesaIdToAdd = null;

            if (destinoCard.hasAttribute('data-union-id')) {
                unionIdToTarget = destinoCard.getAttribute('data-union-id');
                mesaIdToAdd = origenId;
            } else if (origenUnionId) {
                unionIdToTarget = origenUnionId;
                mesaIdToAdd = destinoId;
            }

            if (unionIdToTarget) {
                fetch('/api/v1/uniones-mesas/' + unionIdToTarget + '/agregar-mesa/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken(),
                    },
                    body: JSON.stringify({ mesa_id: mesaIdToAdd }),
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
                    alert('Error al agregar mesa a la unión: ' + error.message);
                });
                return;
            }

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
