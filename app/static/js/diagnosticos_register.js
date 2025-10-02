// Submit del formulario de registro de diagnóstico
document.getElementById('diagnosticoForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);

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

    confirmarSwal('¿Desea registrar este diagnóstico?', async () => {
        try {
            const response = await fetch('/brotes/diagnosticos/registrar', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'Error inesperado');
            }

            alertaSwal('Diagnóstico registrado correctamente', 'success');

            // Limpiar formulario
            form.reset();

            // Redirigir a lista después de 1.5 segundos
            setTimeout(() => {
                window.location.href = '/brotes/diagnosticos/lista';
            }, 1500);

        } catch (err) {
            alertaSwal('Error: ' + err.message, 'error');
        }
    });
});
