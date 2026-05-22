document.addEventListener('DOMContentLoaded', function () {
    const cards = document.querySelectorAll('.union-mesa-card');
    cards.forEach(function (card) {
        card.addEventListener('click', function (e) {
            if (e.target.tagName !== 'BUTTON' && e.target.tagName !== 'FORM') {
                const checkbox = this.querySelector('input[type="checkbox"]');
                checkbox.checked = !checkbox.checked;
                this.classList.toggle('selected', checkbox.checked);
            }
        });
    });
});