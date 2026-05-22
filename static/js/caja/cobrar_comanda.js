document.addEventListener('DOMContentLoaded', function () {
    const metodo = document.getElementById('metodo');
    const grupoVuelto = document.getElementById('vuelto-group');
    const inputVuelto = document.getElementById('vuelto');
    const inputMonto = document.getElementById('monto');
    const inputRef = document.getElementById('referencia');
    const grupoRef = document.getElementById('referencia-group');

    function toggleCampos() {
        const val = metodo.value;
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

    if (metodo) {
        metodo.addEventListener('change', toggleCampos);
        toggleCampos();
    }
    if (inputMonto) {
        inputMonto.addEventListener('input', function () {
            const total = parseFloat(this.dataset.total) || 0;
            const recibido = parseFloat(this.value) || 0;
            inputVuelto.value = Math.max(0, recibido - total).toFixed(2);
        });
    }
});
