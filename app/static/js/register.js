let documentosAdjuntos = [];

//Funcion para mostrar documentos en formulario
function renderTablaDocumentos() {
    const tbody = document.querySelector('#tablaDocumentos tbody');
    const contenedorTabla = document.getElementById('seccionTablaDocumentos');
    tbody.innerHTML = '';

    if (documentosAdjuntos.length === 0) {
        contenedorTabla.style.display = 'none';
        return;
    }

    contenedorTabla.style.display = 'block';

    documentosAdjuntos.forEach((doc, index) => {
        const fila = document.createElement('tr');
        fila.innerHTML = `
            <td>${doc.archivo.name}</td>
            <td>${doc.tipo}</td>
            <td>${doc.folio || '-'}</td>
            <td>${doc.fecha || '-'}</td>
            <td><button class="btn btn-sm btn-danger" onclick="eliminarDocumento(${index})">Eliminar</button></td>
        `;
        tbody.appendChild(fila);
    });
}


//Funcion para eliminar documentos
function eliminarDocumento(index) {
    documentosAdjuntos.splice(index, 1);
    renderTablaDocumentos();
}

//Agrega documentos
document.getElementById('agregarDoc').addEventListener('click', () => {
    const tipo = document.getElementById('tipoDoc').value;
    const archivo = document.getElementById('archivoDoc').files[0];
    const folio = document.getElementById('folio_notinmed').value;
    const fecha = document.getElementById('fecha_notifica_notin').value;

    if (!tipo || !archivo) {
        alert('Tipo y archivo son obligatorios');
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


//Funcion para enviar datos al servidor
document.getElementById('broteForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData();

    // Agregar campos del formulario, excepto los archivos
    [...form.elements].forEach(el => {
        if (el.name && el.type !== 'file') {
            formData.append(el.name, el.value);
        }
    });

    // Agregar los documentos como listas paralelas
    documentosAdjuntos.forEach((doc, index) => {
        formData.append(`documentos[${index}][tipo]`, doc.tipo);
        formData.append(`documentos[${index}][archivo]`, doc.archivo);
        formData.append(`documentos[${index}][folio]`, doc.folio);
        formData.append(`documentos[${index}][fecha]`, doc.fecha);
    });


    confirmarSwal('¿Desea registrar brote?', async () => {
        try {
            const response = await fetch('/brotes/registrar_con_documentos', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'Error inesperado');

            alertaSwal('Brote registrado correctamente');
            form.reset();
            documentosAdjuntos = [];
            renderTablaDocumentos();
        } catch (err) {
            alertaSwal('Error: ' + err.message, 'error');
        }
    });


});