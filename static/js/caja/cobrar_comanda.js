document.addEventListener('DOMContentLoaded', function () {
    const metodo = document.getElementById('metodo');
    const grupoVuelto = document.getElementById('vuelto-group');
    const inputVuelto = document.getElementById('vuelto');
    const inputMonto = document.getElementById('monto');
    if (metodo) {
        metodo.addEventListener('change', function () {
            if (this.value === 'EFECTIVO') {
                grupoVuelto.classList.add('visible');
                inputVuelto.required = true;
            } else {
                grupoVuelto.classList.remove('visible');
                inputVuelto.required = false;
                inputVuelto.value = '0';
            }
        });
    }
    if (inputMonto) {
        inputMonto.addEventListener('input', function () {
            const total = parseFloat(this.dataset.total) || 0;
            const recibido = parseFloat(this.value) || 0;
            inputVuelto.value = Math.max(0, recibido - total).toFixed(2);
        });
    }
});