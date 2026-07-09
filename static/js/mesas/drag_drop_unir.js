document.addEventListener('DOMContentLoaded', function () {
    const mesas = document.querySelectorAll('.mesa-card');

    mesas.forEach(mesa => {
        mesa.setAttribute('draggable', 'true');

        mesa.addEventListener('dragstart', function (e) {
            e.dataTransfer.setData('text/plain', this.dataset.mesaId);
            this.classList.add('dragging');
        });

        mesa.addEventListener('dragend', function () {
            this.classList.remove('dragging');
            document.querySelectorAll('.mesa-card.drop-target').forEach(el => {
                el.classList.remove('drop-target');
            });
        });

        mesa.addEventListener('dragover', function (e) {
            e.preventDefault();
            this.classList.add('drop-target');
        });

        mesa.addEventListener('dragleave', function () {
            this.classList.remove('drop-target');
        });

        mesa.addEventListener('drop', function (e) {
            e.preventDefault();
            this.classList.remove('drop-target');

            const origenId = parseInt(e.dataTransfer.getData('text/plain'));
            const destinoId = parseInt(this.dataset.mesaId);

            if (origenId === destinoId) return;

            fetch('/api/v1/uniones-mesas/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken(),
                },
                body: JSON.stringify({ mesas: [origenId, destinoId] }),
            })
            .then(response => {
                if (!response.ok) throw new Error('Error al unir mesas');
                window.location.reload();
            })
            .catch(error => {
                alert('Error al unir mesas: ' + error.message);
            });
        });
    });

    function getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
});
