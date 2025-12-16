const modalDoc = document.getElementById('modalDocumentos');
modalDoc.addEventListener('hidden.bs.modal', function () {
    document.activeElement.blur();
});

let documentosAdjuntos = [];

// function renderTablaDocumentos() {
//     const contenedorTabla = document.getElementById('seccionTablaDocumentos');
//     const tabla = document.getElementById('tablaDocumentos');
//     let tbodyNuevos = document.getElementById('tbodyNuevos');
//     const tbodyExistentes = tabla.querySelector('tbody:first-of-type');

//     if (!contenedorTabla || !tabla) {
//         console.error("No se encontró el contenedor o la tabla de documentos.");
//         return;
//     }
    
//     if (!tbodyNuevos) {
//         tbodyNuevos = document.createElement('tbody');
//         tbodyNuevos.id = 'tbodyNuevos';
//         tabla.appendChild(tbodyNuevos);
//     }
    
//     const filaNoDocumentos = tbodyExistentes.querySelector('tr td[colspan="5"]');
//     const hayDocumentosExistentes = tbodyExistentes.querySelectorAll('tr[data-tipo="existente"]').length > 0;
        
//     if (documentosAdjuntos.length > 0) {    
//         if (filaNoDocumentos && !hayDocumentosExistentes) {
//             filaNoDocumentos.closest('tr').remove();
//         }        
        
//         tbodyNuevos.innerHTML = '';
//         documentosAdjuntos.forEach((doc, index) => {
//             const fila = document.createElement('tr');
//             fila.dataset.tipo = 'nuevo';
//             fila.innerHTML = `
//                 <td>${doc.archivo.name}</td>
//                 <td>${doc.tipo}</td>
//                 <td><input type="text" class="form-control form-control-sm" value="${doc.folio || ''}"></td>
//                 <td><input type="date" class="form-control form-control-sm" value="${doc.fecha || ''}"></td>
//                 <td>
//                     <button type="button" class="btn btn-sm btn-outline-danger btn-eliminar" data-index="${index}" title="Eliminar">
//                         <i class="fas fa-trash"></i>
//                     </button>                    
//                 </td>
//             `;
//             tbodyNuevos.appendChild(fila);
//         });
//     } else {        
//         tbodyNuevos.innerHTML = '';        
        
//         if (!hayDocumentosExistentes && !filaNoDocumentos) {
//             tbodyExistentes.innerHTML = `
//                 <tr>
//                     <td colspan="5" class="text-center">
//                         No hay documentos asociados a este brote.
//                     </td>
//                 </tr>
//             `;
//         }
//     }
// }





// ============================================
// FUNCIÓN PARA RENDERIZAR LA TABLA
// ============================================
function renderTablaDocumentos() {
    const contenedorTabla = document.getElementById('seccionTablaDocumentos');
    const tabla = document.getElementById('tablaDocumentos');
    let tbodyNuevos = document.getElementById('tbodyNuevos');
    const tbodyExistentes = tabla.querySelector('tbody:first-of-type');

    if (!contenedorTabla || !tabla) {
        console.error("No se encontró el contenedor o la tabla de documentos.");
        return;
    }
    
    if (!tbodyNuevos) {
        tbodyNuevos = document.createElement('tbody');
        tbodyNuevos.id = 'tbodyNuevos';
        tabla.appendChild(tbodyNuevos);
    }
    
    const filaNoDocumentos = tbodyExistentes.querySelector('tr td[colspan="5"]');
    const hayDocumentosExistentes = tbodyExistentes.querySelectorAll('tr[data-tipo="existente"]').length > 0;
        
    if (documentosAdjuntos.length > 0) {    
        if (filaNoDocumentos && !hayDocumentosExistentes) {
            filaNoDocumentos.closest('tr').remove();
        }        
        
        tbodyNuevos.innerHTML = '';
        documentosAdjuntos.forEach((doc, index) => {
            const fila = document.createElement('tr');
            fila.dataset.tipo = 'nuevo';
            fila.innerHTML = `
                <td>${doc.archivo.name}</td>
                <td>${doc.tipo}</td>
                <td><input type="text" class="form-control form-control-sm doc-folio" value="${doc.folio || ''}" data-index="${index}"></td>
                <td><input type="date" class="form-control form-control-sm doc-fecha" value="${doc.fecha || ''}" data-index="${index}"></td>
                <td>
                    <button type="button" class="btn btn-sm btn-outline-danger btn-eliminar" data-index="${index}" title="Eliminar">
                        <i class="fas fa-trash"></i>
                    </button>                    
                </td>
            `;
            tbodyNuevos.appendChild(fila);
        });
    } else {        
        tbodyNuevos.innerHTML = '';        
        
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




// ============================================
// EVENTO: ELIMINAR DOCUMENTOS NUEVOS
// ============================================
document.addEventListener('click', (e) => {    
    if (e.target.closest('.btn-eliminar')) {
        const button = e.target.closest('.btn-eliminar');
        const index = parseInt(button.dataset.index, 10);
        
        // Validar que el índice sea válido
        if (isNaN(index) || index < 0 || index >= documentosAdjuntos.length) {
            console.error('Índice inválido:', index);
            alertaSwal('Error al eliminar el documento.', 'error');
            return;
        }

        const nombreArchivo = documentosAdjuntos[index].archivo.name;

        confirmarSwal(`¿Eliminar el documento "${nombreArchivo}"?`, () => {
            // Eliminar del array
            documentosAdjuntos.splice(index, 1);
            
            // Re-renderizar la tabla
            renderTablaDocumentos();
            
            // Mostrar mensaje de éxito
            alertaSwal('El documento ha sido eliminado correctamente.', 'success');
        });
    }
});


// ============================================
// EVENTO: ELIMINAR DOCUMENTOS EXISTENTES
// ============================================
document.addEventListener('click', (e) => {    
    if (e.target.closest('.btn-eliminar-doc')) {
        const button = e.target.closest('.btn-eliminar-doc');
        const docId = button.dataset.docId;
        const nombreArchivo = button.dataset.nombre;
        
        if (!docId) {
            console.error('ID de documento no encontrado');
            alertaSwal('Error al eliminar el documento.', 'error');
            return;
        }

        confirmarSwal(`¿Eliminar el documento "${nombreArchivo}"?`, () => {
            fetch(`/brotes/documento/eliminar/${docId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest' 
                }
            })
            .then(response => {
                return response.json().then(data => ({
                    status: response.status,
                    ok: response.ok,
                    data: data
                }));
            })
            .then(result => {
                console.log('Respuesta:', result);

                // Si la respuesta NO es OK o el backend indicó success: false
                if (!result.ok || !result.data || result.data.success === false) {
                    const msg = (result.data && (result.data.mensaje || result.data.error)) 
                                || `Error al eliminar el documento (código ${result.status}).`;
                    alertaSwal(msg, 'error');
                    return; // No seguimos con la parte de éxito
                }
    
                
                if (result.status === 200 && result.data.success) {
                    // Eliminar la fila del DOM
                    const fila = button.closest('tr');
                    fila.remove();
                    
                    // Verificar si quedan documentos
                    const tbodyExistentes = document.querySelector('#tablaDocumentos tbody:first-of-type');
                    const hayDocumentosExistentes = tbodyExistentes ? 
                        tbodyExistentes.querySelectorAll('tr[data-tipo="existente"]').length > 0 : false;
                    
                    if (!hayDocumentosExistentes && documentosAdjuntos.length === 0) {
                        if (tbodyExistentes) {
                            tbodyExistentes.innerHTML = `
                                <tr>
                                    <td colspan="5" class="text-center">
                                        No hay documentos asociados a este brote.
                                    </td>
                                </tr>
                            `;
                        }
                    }
                    
                    alertaSwal(result.data.mensaje || 'Documento eliminado correctamente.', 'success');
                    
                } else {
                    alertaSwal(result.data.mensaje || 'Error al eliminar el documento.', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alertaSwal('Error de conexión al eliminar el documento.', 'error');
            });
        });
    }
});




// document.addEventListener('click', (e) => {    
//     if (e.target.closest('.btn-eliminar')) {
//         const button = e.target.closest('.btn-eliminar');
//         const index = button.dataset.index;

//         confirmarSwal('¿Eliminar este documento?', () => {
//             documentosAdjuntos.splice(index, 1);
//             renderTablaDocumentos();
//             alertaSwal('El documento ha sido eliminado.', 'success');
//         });
//     }
// });


// function eliminarDocumento(index) {
//     confirmarSwal('¿Eliminar este documento?', () => {
//         documentosAdjuntos.splice(index, 1);
//         renderTablaDocumentos();
//         Swal.fire('Eliminado', 'El documento ha sido eliminado.', 'success');
//     });
// }


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