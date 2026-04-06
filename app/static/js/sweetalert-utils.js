/**
 * Muestra un alert simple con SweetAlert2.
 * @param {string} mensaje - Mensaje a mostrar.
 * @param {string} tipo - Tipo de alerta: success | error | warning | info | question.
 */
function alertaSwal(mensaje, tipo = 'success') {
    const tiposValidos = ['success', 'error', 'warning', 'info', 'question'];

    // Validación del tipo
    const icono = tiposValidos.includes(tipo) ? tipo : 'info';

    Swal.fire({
        icon: icono,
        title: mensaje,
        confirmButtonText: 'OK'
    });
}

/**
 * Muestra un confirm con SweetAlert2.
 * @param {string} mensaje - Mensaje de confirmación.
 * @param {function} callback - Función a ejecutar si el usuario confirma.
 */
function confirmarSwal(mensaje, callback) {
    Swal.fire({
        title: mensaje,
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#d33',
        confirmButtonText: 'Sí',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed && typeof callback === 'function') {
            callback();
        }
    });
}