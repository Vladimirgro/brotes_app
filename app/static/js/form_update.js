const formUpdate = document.getElementById('form_update');

document.getElementById('form_update').addEventListener('submit', async function (e) {
    e.preventDefault();

    const form = e.target;

    // Validar antes de continuar
    if (!validarDocumentos()) return;

    const formData = new FormData();

    // Agregar campos del formulario, excepto los archivos
    [...form.elements].forEach(el => {
        if (el.name && el.type !== 'file') {
            formData.append(el.name, el.value);
        }
    });

    // **Capturar documentos existentes**
    document.querySelectorAll('#tablaDocumentos tbody tr[data-tipo="existente"]').forEach((row, index) => {
        const idDocumento = row.getAttribute('data-id');
        const folio = row.querySelector('.folioInput')?.value || '';
        const fecha = row.querySelector('.fechaInput')?.value || '';

        formData.append(`existentes[${index}][iddocumento]`, idDocumento);
        formData.append(`existentes[${index}][folio]`, folio);
        formData.append(`existentes[${index}][fecha]`, fecha);
    });

    // **Capturar documentos nuevos desde documentosAdjuntos**
    documentosAdjuntos.forEach((doc, index) => {
        const validTypes = [
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel.sheet.macroenabled.12'
        ];

        // Verificar si el documento es existente, si hay archivo y validar el tipo de documento
        if (doc.archivo && validTypes.includes(doc.archivo.type)) {
            formData.append(`nuevos[${index}][tipo]`, doc.tipo);
            formData.append(`nuevos[${index}][archivo]`, doc.archivo);
            formData.append(`nuevos[${index}][folio]`, doc.folio || '');
            formData.append(`nuevos[${index}][fecha]`, doc.fecha || '');
        } else {
            Swal.fire('Error', 'Solo se permiten archivos de tipo DOC, DOCX, XLSX, XLS, XLSM', 'error');
            return;
        }
    });


    confirmarSwal('¿Desea actualizar brote?', async () => {
        try {
            const response = await fetch(`/brotes/actualizar_brote/${form.idbrote.value}`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'Error inesperado');

            alertaSwal('Brote actualizado correctamente.', 'success');

            setTimeout(() => {
                location.replace(location.href);
            }, 1000);

            form.reset();
            documentosAdjuntos = [];

        } catch (err) {
            alertaSwal('Error: ' + err.message, 'error');
        }
    });


});