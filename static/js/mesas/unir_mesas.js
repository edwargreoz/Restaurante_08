document.addEventListener('DOMContentLoaded', function () {
    const cards = document.querySelectorAll('.union-mesa-card');
    const checkboxes = document.querySelectorAll('.union-mesa-card input[type="checkbox"]');

    // --- Validación de zonas al seleccionar mesas para unir ---
    function actualizarEstadoZonas() {
        const seleccionadas = document.querySelectorAll('.union-mesa-card input[type="checkbox"]:checked:not(:disabled)');
        let zonaSeleccionada = null;

        if (seleccionadas.length > 0) {
            zonaSeleccionada = seleccionadas[0].getAttribute('data-zona');
        }

        checkboxes.forEach(function (cb) {
            if (cb.disabled) return; // Ya unida, no tocar

            const card = cb.closest('.union-mesa-card');
            const zona = cb.getAttribute('data-zona');

            if (zonaSeleccionada && zona !== zonaSeleccionada && !cb.checked) {
                card.classList.add('zona-bloqueada');
                cb.disabled = true;
                cb.dataset.bloqueadoPorZona = 'true';
            } else {
                if (cb.dataset.bloqueadoPorZona === 'true') {
                    card.classList.remove('zona-bloqueada');
                    cb.disabled = false;
                    delete cb.dataset.bloqueadoPorZona;
                }
            }
        });
    }

    cards.forEach(function (card) {
        card.addEventListener('click', function (e) {
            if (e.target.tagName === 'BUTTON' || e.target.tagName === 'FORM') return;

            const checkbox = this.querySelector('input[type="checkbox"]');
            if (checkbox.disabled && checkbox.dataset.bloqueadoPorZona !== 'true') return;
            if (checkbox.disabled && checkbox.dataset.bloqueadoPorZona === 'true') return;

            checkbox.checked = !checkbox.checked;
            this.classList.toggle('selected', checkbox.checked);
            actualizarEstadoZonas();
        });
    });

    checkboxes.forEach(function (cb) {
        cb.addEventListener('change', actualizarEstadoZonas);
    });

    // --- Filtrar dropdown de "Agregar mesa a unión" por zona ---
    const selects = document.querySelectorAll('.select-agregar-mesa');
    selects.forEach(function (select) {
        const zonaUnion = select.getAttribute('data-zona-union');
        if (!zonaUnion) return;

        const options = select.querySelectorAll('option[data-zona]');
        options.forEach(function (option) {
            if (option.getAttribute('data-zona') !== zonaUnion) {
                option.remove();
            }
        });
    });
});