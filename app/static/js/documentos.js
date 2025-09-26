const modalDoc = document.getElementById('modalDocumentos');
modalDoc.addEventListener('hidden.bs.modal', function () {
    document.activeElement.blur();
});

let documentosAdjuntos = [];

function renderTablaDocumentos() {
    const contenedorTabla = document.getElementById('seccionTablaDocumentos');
    const tabla = document.getElementById('tablaDocumentos');
    let tbodyNuevos = document.getElementById('tbodyNuevos');
    const tbodyExistentes = tabla.querySelector('tbody:first-of-type'); // El primer tbody con documentos existentes

    if (!contenedorTabla || !tabla) {
        console.error("No se encontró el contenedor o la tabla de documentos.");
        return;
    }

    // Si no existe el tbody para documentos nuevos, lo creamos al final de la tabla
    if (!tbodyNuevos) {
        tbodyNuevos = document.createElement('tbody');
        tbodyNuevos.id = 'tbodyNuevos';
        tabla.appendChild(tbodyNuevos);
    }

    // Verificar si el primer tbody tiene solo la fila de "No hay documentos"
    const filaNoDocumentos = tbodyExistentes.querySelector('tr td[colspan="5"]');
    const hayDocumentosExistentes = tbodyExistentes.querySelectorAll('tr[data-tipo="existente"]').length > 0;
    
    // Si hay documentos nuevos para agregar
    if (documentosAdjuntos.length > 0) {
        // Si existe la fila de "No hay documentos", la eliminamos
        if (filaNoDocumentos && !hayDocumentosExistentes) {
            filaNoDocumentos.closest('tr').remove();
        }
        
        // Limpiar y agregar documentos nuevos
        tbodyNuevos.innerHTML = '';
        documentosAdjuntos.forEach((doc, index) => {
            const fila = document.createElement('tr');
            fila.dataset.tipo = 'nuevo';
            fila.innerHTML = `
                <td>${doc.archivo.name}</td>
                <td>${doc.tipo}</td>
                <td><input type="text" class="form-control form-control-sm" value="${doc.folio || ''}"></td>
                <td><input type="date" class="form-control form-control-sm" value="${doc.fecha || ''}"></td>
                <td>
                    <button type="button" class="btn btn-sm btn-danger btn-eliminar" data-index="${index}" title="Eliminar">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            `;
            tbodyNuevos.appendChild(fila);
        });
    } else {
        // Si no hay documentos nuevos, limpiar el tbody de nuevos
        tbodyNuevos.innerHTML = '';
        
        // Si tampoco hay documentos existentes, mostrar mensaje de "No hay documentos"
        if (!hayDocumentosExistentes && !filaNoDocumentos) {
            tbodyExistentes.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center">
                        No hay documentos asociados a este brote.
                    </td>
                </tr>
            `;
        }
    }
}


document.addEventListener('click', (e) => {
    // Verificar si el click fue en un botón con clase .btn-eliminar
    if (e.target.closest('.btn-eliminar')) {
        const button = e.target.closest('.btn-eliminar');
        const index = button.dataset.index; // Obtener índice del documento

        confirmarSwal('¿Eliminar este documento?', () => {
            documentosAdjuntos.splice(index, 1);
            renderTablaDocumentos();
            alertaSwal('El documento ha sido eliminado.', 'success');
        });
    }
});

//Funcion para eliminar documentos
function eliminarDocumento(index) {
    confirmarSwal('¿Eliminar este documento?', () => {
        documentosAdjuntos.splice(index, 1);
        renderTablaDocumentos();
        Swal.fire('Eliminado', 'El documento ha sido eliminado.', 'success');
    });
}


//Agrega documentos
document.getElementById('agregarDoc').addEventListener('click', () => {
    const tipo = document.getElementById('tipoDoc').value;
    const archivo = document.getElementById('archivoDoc').files[0];
    const folio = document.getElementById('folio_notinmed').value;
    const fecha = document.getElementById('fecha_notifica_notin').value;

    if (!tipo || !archivo) {
        alertaSwal('Tipo y archivo son obligatorios');
        return;
    }

    documentosAdjuntos.push({ tipo, archivo, folio, fecha });
    renderTablaDocumentos();

    // Limpiar inputs y cerrar modal
    ['tipoDoc', 'archivoDoc', 'folio_notinmed', 'fecha_notifica_notin'].forEach(id => {
        document.getElementById(id).value = '';
    });
    const modal = bootstrap.Modal.getInstance(document.getElementById('modalDocumentos'));
    modal.hide();
});



//FUNCION QUE VALIDA QUE TODOS LOS DOCUMENTOS TENGAN FOLIO Y FECHA
function validarDocumentos() {
    let valido = true;

    // Validar documentos existentes
    document.querySelectorAll('#tablaDocumentos tbody tr[data-tipo="existente"]').forEach((row) => {
        const folio = row.querySelector('.folioInput')?.value.trim();
        const fecha = row.querySelector('.fechaInput')?.value.trim();

        if (folio && !fecha) {
            valido = false;
        }
    });

    // Validar documentos nuevos
    documentosAdjuntos.forEach((doc) => {
        if (doc.folio && !doc.fecha) {
            valido = false;
        }
    });

    if (!valido) {
        alertaSwal('Si agregas un folio, debes ingresar también una fecha.', 'warning');
    }

    return valido;
}