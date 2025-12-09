// Submit del formulario de edición de diagnóstico
document.getElementById('diagnosticoFormUpdate').addEventListener('submit', async function (e) {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);
    const iddiag = formData.get('iddiag');

    // Validaciones adicionales
    const nombre = formData.get('nombre').trim();
    const periodo = formData.get('periodo_incubacion');

    if (!nombre) {
        alertaSwal('El nombre del diagnóstico es obligatorio', 'error');
        return;
    }

    if (!periodo || periodo <= 0) {
        alertaSwal('El periodo de incubación debe ser mayor a 0', 'error');
        return;
    }

    confirmarSwal('¿Desea actualizar este diagnóstico?', async () => {
        try {
            const response = await fetch(`/brotes/diagnosticos/actualizar/${iddiag}`, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'Error inesperado');
            }

            alertaSwal('Diagnóstico actualizado correctamente', 'success');

            // Redirigir a lista después de 1.5 segundos
            setTimeout(() => {
                window.location.href = result.redirect_url || '/brotes/diagnosticos/lista';
            }, 1500);

        } catch (err) {
            alertaSwal('Error: ' + err.message, 'error');
        }
    });
});
