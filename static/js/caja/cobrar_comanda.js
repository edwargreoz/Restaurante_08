document.addEventListener('DOMContentLoaded', function () {
    /* ---- Pago simple ---- */
    var metodo = document.getElementById('metodo');
    if (metodo) {
        var grupoVuelto = document.getElementById('vuelto-group');
        var inputVuelto = document.getElementById('vuelto');
        var inputMonto = document.getElementById('monto');
        var inputRef = document.getElementById('referencia');
        var grupoRef = document.getElementById('referencia-group');

        function toggleCampos() {
            var val = metodo.value;
            if (val === 'EFECTIVO') {
                grupoVuelto.classList.add('visible');
                inputVuelto.required = true;
                grupoRef.classList.remove('visible');
                inputRef.required = false;
            } else if (val === 'TARJETA') {
                grupoVuelto.classList.remove('visible');
                inputVuelto.required = false;
                inputVuelto.value = '0';
                grupoRef.classList.add('visible');
                inputRef.required = true;
            } else {
                grupoVuelto.classList.remove('visible');
                inputVuelto.required = false;
                inputVuelto.value = '0';
                grupoRef.classList.remove('visible');
                inputRef.required = false;
            }
        }

        metodo.addEventListener('change', toggleCampos);
        toggleCampos();

        if (inputMonto) {
            inputMonto.addEventListener('input', function () {
                var total = parseFloat(this.dataset.total) || 0;
                var recibido = parseFloat(this.value) || 0;
                inputVuelto.value = Math.max(0, recibido - total).toFixed(2);
            });
        }
    }

    /* ---- Pago dividido ---- */
    var container = document.getElementById('split-pagos-container');
    var template = document.getElementById('split-template');
    var addBtn = document.getElementById('add-split-pago');
    var totalCuentaEl = document.getElementById('split-total-cuenta');
    var totalCuenta = totalCuentaEl ? parseFloat(totalCuentaEl.textContent) || 0 : 0;

    function actualizarResumenSplit() {
        var montos = container.querySelectorAll('.split-monto');
        var suma = 0;
        montos.forEach(function (inp) {
            suma += parseFloat(inp.value) || 0;
        });
        var sumaEl = document.getElementById('split-suma-pagos');
        var restanteEl = document.getElementById('split-restante');
        var submitBtn = document.getElementById('split-submit');
        if (sumaEl) sumaEl.textContent = suma.toFixed(2);
        var restante = totalCuenta - suma;
        if (restanteEl) restanteEl.textContent = restante.toFixed(2);
        if (submitBtn) submitBtn.disabled = Math.abs(restante) > 0.01;
    }

    function toggleSplitCampos(item) {
        var metodoSelect = item.querySelector('.split-metodo');
        if (!metodoSelect) return;
        var val = metodoSelect.value;
        var vueltoGroup = item.querySelector('.split-vuelto-group');
        var refGroup = item.querySelector('.split-ref-group');
        var vueltoInput = item.querySelector('.split-vuelto');
        var refInput = item.querySelector('.split-referencia');
        if (vueltoGroup) vueltoGroup.style.display = 'none';
        if (refGroup) refGroup.style.display = 'none';
        if (vueltoInput) vueltoInput.required = false;
        if (refInput) refInput.required = false;
        if (val === 'EFECTIVO') {
            if (vueltoGroup) vueltoGroup.style.display = 'block';
            if (vueltoInput) vueltoInput.required = true;
        } else if (val === 'TARJETA') {
            if (refGroup) refGroup.style.display = 'block';
            if (refInput) refInput.required = true;
        }
    }

    function initSplitItem(item) {
        var removeBtn = item.querySelector('.remove-split-pago');
        if (removeBtn) {
            removeBtn.addEventListener('click', function () {
                item.remove();
                actualizarResumenSplit();
            });
        }
        var metodoSelect = item.querySelector('.split-metodo');
        if (metodoSelect) {
            metodoSelect.addEventListener('change', function () {
                toggleSplitCampos(item);
            });
            toggleSplitCampos(item);
        }
        var montoInput = item.querySelector('.split-monto');
        if (montoInput) {
            montoInput.addEventListener('input', actualizarResumenSplit);
        }
    }

    /* Inicializar items existentes */
    container.querySelectorAll('.split-pago-item').forEach(function (item) {
        initSplitItem(item);
    });
    actualizarResumenSplit();

    /* Agregar nuevo item clonando template */
    if (addBtn && template) {
        addBtn.addEventListener('click', function () {
            var clone = template.querySelector('.split-pago-item').cloneNode(true);
            clone.querySelectorAll('input, select').forEach(function (el) {
                el.value = '';
                el.required = false;
            });
            container.appendChild(clone);
            initSplitItem(clone);
            var allItems = container.querySelectorAll('.split-pago-item');
            allItems.forEach(function (item) {
                var btn = item.querySelector('.remove-split-pago');
                if (btn) btn.style.display = 'inline-block';
            });
            actualizarResumenSplit();
        });
    }
});
