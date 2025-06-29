console.log('scripts.js loaded and executing.'); // Debug para confirmar carga

function actualizarDetalleComanda() {
    const tbody = document.getElementById('detalle-comanda');
    tbody.innerHTML = '';
    
    comandaItems.forEach(item => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${item.nombre}</td>
            <td>
                <input type="number" min="1" value="${item.cantidad}" 
                       onchange="actualizarCantidad(${item.id}, this.value)" 
                       class="form-control form-control-sm" style="width: 70px;">
            </td>
            <td>$${item.precio.toFixed(2)}</td>
            <td>$${item.total.toFixed(2)}</td>
            <td>
                <button class="btn btn-danger btn-sm" onclick="eliminarItem(${item.id})">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function calcularTotal() {
    const total = comandaItems.reduce((sum, item) => sum + item.total, 0);
    document.getElementById('total-comanda').textContent = total.toFixed(2);
}

// Funciones similares para guardar, imprimir, limpiar comanda, etc.

// Funciones para el manager
function cargarSeccion(seccion, link = null) {
    // Actualizar clase activa en el menú
    document.querySelectorAll('.nav-link').forEach(navLink => {
        navLink.classList.remove('active');
    });
    if (link) {
        link.classList.add('active');
    }

    // Cerrar sidebar en móviles después de seleccionar una sección
    if (window.innerWidth <= 768) {
        toggleSidebar();
    }

    // Mostrar indicador de carga
    const contenidoSeccion = document.getElementById('contenido-seccion');
    if (!contenidoSeccion) {
        console.error('No se encontró el elemento #contenido-seccion');
        return;
    }

    contenidoSeccion.innerHTML = `
        <div class="card">
            <div class="card-body text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Cargando...</span>
                </div>
                <p class="mt-2">Cargando contenido...</p>
            </div>
        </div>
    `;

    // Cargar el contenido de la sección
    fetch(`/manager/${seccion}`)
        .then(response => response.text())
        .then(html => {
            contenidoSeccion.innerHTML = html;
            
            // Inicializar eventos específicos según la sección
            if (seccion === 'comandas') {
                inicializarComandas();
            } else if (seccion === 'ventas') {
                inicializarVentas();
            } else if (seccion === 'impresoras') {
                // Asegurarse de que el script de impresoras se ejecute
                if (typeof inicializarImpresoras === 'function') {
                    inicializarImpresoras();
                } else {
                    console.warn('inicializarImpresoras function not found.');
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            contenidoSeccion.innerHTML = `
                <div class="card">
                    <div class="card-body">
                        <div class="alert alert-danger">
                            <i class="bi bi-exclamation-triangle"></i> Error al cargar la sección
                        </div>
                    </div>
                </div>
            `;
        });
}

function inicializarComandas() {
    const detalleModal = document.getElementById('detalleComandaModal');
    if (detalleModal) {
        detalleModal.addEventListener('hidden.bs.modal', function () {
            document.getElementById('comanda-id').textContent = '';
            document.getElementById('comanda-mesa').textContent = '';
            document.getElementById('comanda-fecha').textContent = '';
            document.getElementById('comanda-total').textContent = '';
            document.getElementById('detalle-comanda-body').innerHTML = '';
        });
    }
}

function mostrarFormulario(titulo, campos, registroId = null) {
    document.getElementById('modalTitle').textContent = titulo;
    
    // Construir formulario dinámicamente
    let formHTML = '<form id="modalForm">';
    
    campos.forEach(campo => {
        formHTML += `
            <div class="mb-3">
                <label for="${campo}" class="form-label">${campo.charAt(0).toUpperCase() + campo.slice(1)}</label>
                <input type="${campo === 'password' ? 'password' : 'text'}" 
                       class="form-control" id="${campo}" name="${campo}">
            </div>
        `;
    });
    
    formHTML += '</form>';
    document.getElementById('modalBody').innerHTML = formHTML;
    
    // Si es edición, cargar datos
    if (registroId) {
        // Aquí harías una petición para obtener los datos del registro
    }
    
    // Mostrar modal
    const modal = new bootstrap.Modal(document.getElementById('formModal'));
    modal.show();
}

// scripts.js - Agrega estas funciones

// Manejar eventos de los botones en el manager
document.addEventListener('click', function(e) {
    const btn = e.target.closest('button');
    if (!btn) return;

    // Determinar qué tipo de botón se clickeó
    if (btn.classList.contains('btn-agregar')) {
        e.preventDefault();
        mostrarFormularioAgregar(btn.dataset.tipo);
    } 
    else if (btn.classList.contains('btn-editar')) {
        e.preventDefault();
        mostrarFormularioEditar(btn.dataset.tipo, btn.dataset.id);
    }
    else if (btn.classList.contains('btn-eliminar')) {
        e.preventDefault();
        confirmarEliminar(btn.dataset.tipo, btn.dataset.id);
    }
});

function mostrarFormularioAgregar(tipo) {
    let url = '';
    switch(tipo) {
        case 'usuarios':
            url = '/formulario/usuarios';
            break;
        case 'items':
            url = '/formulario/items';
            break;
        case 'grupos':
            url = '/formulario/grupos';
            break;
        case 'mesas':
            url = '/formulario/mesas';
            break;
        case 'impresoras':
            url = '/formulario/impresoras';
            break;
        case 'productos':
            url = '/formulario/producto';
            break;
        default:
            url = `/formulario/${tipo}`;
    }
    
    fetch(url)
        .then(response => response.text())
        .then(html => {
            document.getElementById('modalBody').innerHTML = html;
            document.getElementById('modalTitle').textContent = `Nuevo ${tipo.charAt(0).toUpperCase() + tipo.slice(1)}`;
            const modal = new bootstrap.Modal(document.getElementById('formModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error:', error);
            mostrarNotificacion('Error al cargar el formulario', 'error');
        });
}

function mostrarFormularioEditar(tipo, id) {
    const titulo = tipo === 'usuarios' ? 'Editar Usuario' : 
                  tipo === 'items' ? 'Editar Item' :
                  tipo === 'grupos' ? 'Editar Grupo' : 'Editar Registro';
    
    fetch(`/formulario/${tipo}?id=${id}`)
        .then(response => response.text())
        .then(html => {
            document.getElementById('modalTitle').textContent = titulo;
            document.getElementById('modalBody').innerHTML = html;
            const modal = new bootstrap.Modal(document.getElementById('formModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error:', error);
            mostrarNotificacion('Error al cargar el formulario', 'error');
        });
}

function confirmarEliminar(tipo, id) {
    if (confirm('¿Está seguro de eliminar este registro?')) {
        fetch(`/api/${tipo}/${id}`, { 
            method: 'DELETE',
            headers: {
                'Accept': 'application/json'
            }
        })
        .then(response => response.json())
        .then(resultado => {
            if (resultado.success) {
                mostrarNotificacion(resultado.message || 'Registro eliminado correctamente');
                cargarSeccion(tipo);
            } else {
                throw new Error(resultado.message || 'Error al eliminar el registro');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            mostrarNotificacion(error.message, 'error');
        });
    }
}

function guardarFormulario() {
    const form = document.getElementById('modalForm');
    if (!form) {
        console.error('No se encontró el formulario');
        return;
    }

    const formData = new FormData(form);
    const data = {};
    formData.forEach((value, key) => {
        if (key === 'precio') {
            data[key] = parseFloat(value) || 0;
        } else if (key === 'existencia') {
            data[key] = parseInt(value) || 0;
        } else if (key === 'id' && value) {
            data[key] = value;
        } else {
            data[key] = value;
        }
    });

    console.log('Datos del formulario:', data); // Debug

    // Validaciones específicas para items
    if (data.tipo === 'items') {
        if (!data.nombre || !data.grupo_codigo || data.precio <= 0 || data.existencia < 0) {
            mostrarNotificacion('Por favor complete todos los campos correctamente', 'error');
            return;
        }
    }

    // Validaciones específicas para usuarios
    if (data.tipo === 'usuarios') {
        if (!data.user || !data.nombre_completo || !data.rol) {
            mostrarNotificacion('Por favor complete todos los campos', 'error');
            return;
        }
        // Para nuevos usuarios, la contraseña es requerida
        if (!data.id && !data.password) {
            mostrarNotificacion('La contraseña es requerida para nuevos usuarios', 'error');
            return;
        }
        // Para edición, si la contraseña está vacía, eliminarla del objeto
        if (data.password === '') {
            delete data.password;
        }
    }

    // Validaciones específicas para grupos
    if (data.tipo === 'grupos') {
        if (!data.id || !data.nombre || !data.formato) {
            mostrarNotificacion('Por favor complete todos los campos requeridos', 'error');
            return;
        }
    }

    // Determinar si es creación o actualización
    const isEdit = formData.get('is_edit') === 'true';
    const url = isEdit ? `/api/${data.tipo}/${data.id}` : `/api/${data.tipo}`;
    const method = isEdit ? 'PUT' : 'POST';

    console.log('Operación:', isEdit ? 'Actualización' : 'Creación');
    console.log('Enviando datos:', { url, method, data }); // Debug

    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        console.log('Respuesta del servidor:', response); // Debug
        if (!response.ok) {
            return response.json().then(err => {
                throw new Error(err.message || 'Error en la respuesta del servidor');
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('Datos recibidos:', data); // Debug
        if (data.success) {
            const modal = bootstrap.Modal.getInstance(document.getElementById('formModal'));
            modal.hide();
            mostrarNotificacion(data.message || 'Registro guardado correctamente');
            // Recargar la sección actual
            const activeLink = document.querySelector('.nav-link.active');
            if (activeLink) {
                const seccion = activeLink.getAttribute('onclick').match(/'([^']+)'/)[1];
                cargarSeccion(seccion);
            }
        } else {
            throw new Error(data.message || 'Error al guardar');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        mostrarNotificacion(error.message, 'error');
    });
}

document.addEventListener('DOMContentLoaded', function() {
//document.getElementById('modalSaveBtn').addEventListener('click', guardarFormulario);
});

function mostrarAlerta(tipo, mensaje) {
    const alerta = document.createElement('div');
    alerta.className = `alert alert-${tipo} alert-dismissible fade show`;
    alerta.role = 'alert';
    alerta.innerHTML = `
        ${mensaje}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    const contenedor = document.getElementById('alert-container');
    contenedor.innerHTML = '';
    contenedor.appendChild(alerta);
    
    setTimeout(() => {
        alerta.classList.remove('show');
        setTimeout(() => alerta.remove(), 150);
    }, 5000);
}

function mostrarNotificacion(mensaje, tipo = 'success') {
    const notificacion = document.createElement('div');
    notificacion.className = `alert alert-${tipo} position-fixed top-0 end-0 m-3`;
    notificacion.style.zIndex = '1100';
    notificacion.innerHTML = `
        ${mensaje}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    document.body.appendChild(notificacion);
    
    // Auto-cerrar después de 5 segundos
    setTimeout(() => {
        notificacion.remove();
    }, 5000);
}

// Inicialización al cargar la página
document.addEventListener('DOMContentLoaded', function() {
    // Cargar la sección de usuarios por defecto
    cargarSeccion('dashboard', document.querySelector('.nav-link.active'));
    
    // Configurar el modal para limpiar su contenido al cerrarse
    const formModal = document.getElementById('formModal');
    if (formModal) {
        formModal.addEventListener('hidden.bs.modal', function () {
            document.getElementById('modalBody').innerHTML = '';
        });
    }
});

// Variables globales para comandas
window.comandaActual = null;

// Funciones para comandas
window.verDetalleComanda = function(id) {
    console.log('Ver detalle comanda:', id); // Debug
    fetch(`/api/comandas/${id}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Error al obtener los detalles de la comanda');
            }
            return response.json();
        })
        .then(comanda => {
            console.log('Comanda recibida:', comanda); // Debug
            window.comandaActual = comanda;
            
            // Actualizar el contenido del modal
            document.getElementById('comanda-id').textContent = comanda.id;
            document.getElementById('comanda-mesa').textContent = comanda.mesa_nombre;
            document.getElementById('comanda-fecha').textContent = new Date(comanda.fecha).toLocaleString();
            document.getElementById('comanda-total').textContent = comanda.total.toFixed(2);
            document.getElementById('comanda-estatus').textContent = comanda.estatus;
            
            // Actualizar el botón de pagar según el estatus
            const btnPagar = document.getElementById('btn-pagar');
            if (btnPagar) {
                if (comanda.estatus === 'pagada') {
                    btnPagar.style.display = 'none';
                } else {
                    btnPagar.style.display = 'inline-block';
                }
            }
            
            // Actualizar la tabla de detalles
            const tbody = document.getElementById('detalle-comanda-body');
            if (tbody) {
                tbody.innerHTML = '';
                comanda.detalles.forEach(detalle => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${detalle.item_nombre}</td>
                        <td class="text-center">${detalle.cantidad}</td>
                        <td class="text-end">$${detalle.precio_unitario.toFixed(2)}</td>
                        <td class="text-end">$${detalle.total.toFixed(2)}</td>
                    `;
                    tbody.appendChild(tr);
                });
            }
            
            // Mostrar el modal
            const modal = new bootstrap.Modal(document.getElementById('detalleComandaModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error:', error);
            window.mostrarNotificacion('Error al cargar los detalles de la comanda', 'danger');
        });
};

window.marcarComoPagada = function(id = null) {
    console.log('Marcar como pagada:', id); // Debug
    const comandaId = id || (window.comandaActual ? window.comandaActual.id : null);
    if (!comandaId) {
        window.mostrarNotificacion('No se pudo identificar la comanda', 'danger');
        return;
    }

    if (confirm('¿Está seguro de marcar esta comanda como pagada? Esto liberará la mesa.')) {
        fetch(`/api/comandas/${comandaId}/pagar`, { 
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Error al marcar la comanda como pagada');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                window.mostrarNotificacion('Comanda marcada como pagada correctamente', 'success');
                // Cerrar el modal si está abierto
                const modal = bootstrap.Modal.getInstance(document.getElementById('detalleComandaModal'));
                if (modal) {
                    modal.hide();
                }
                // Recargar la página para actualizar el listado
                location.reload();
            } else {
                throw new Error(data.message || 'Error al marcar la comanda como pagada');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            window.mostrarNotificacion(error.message, 'danger');
        });
    }
};

window.imprimirComanda = function(id) {
    console.log('Imprimir comanda:', id); // Debug
    fetch(`/api/comandas/${id}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Error al obtener los datos de la comanda');
            }
            return response.json();
        })
        .then(comanda => {
            console.log('Comanda para imprimir:', comanda); // Debug
            const ventana = window.open('', '_blank');
            ventana.document.write(`
                <html>
                    <head>
                        <title>Comanda #${comanda.id}</title>
                        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
                        <style>
                            @media print {
                                body { margin: 0; padding: 15px; }
                                .no-print { display: none; }
                            }
                            .ticket {
                                max-width: 800px;
                                margin: 0 auto;
                                padding: 20px;
                            }
                            .ticket-header {
                                text-align: center;
                                margin-bottom: 20px;
                            }
                            .ticket-table {
                                width: 100%;
                                margin-bottom: 20px;
                            }
                            .ticket-table th,
                            .ticket-table td {
                                padding: 8px;
                            }
                            .text-end {
                                text-align: right;
                            }
                            .text-center {
                                text-align: center;
                            }
                        </style>
                    </head>
                    <body>
                        <div class="ticket">
                            <div class="ticket-header">
                                <h4>Sistema de Comandas</h4>
                                <p>Comanda #${comanda.id}</p>
                                <p>Mesa: ${comanda.mesa_nombre}</p>
                                <p>Fecha: ${new Date(comanda.fecha).toLocaleString()}</p>
                                <p>Estatus: ${comanda.estatus}</p>
                            </div>
                            
                            <table class="ticket-table">
                                <thead>
                                    <tr>
                                        <th>Producto</th>
                                        <th class="text-center">Cant.</th>
                                        <th class="text-end">P. Unit.</th>
                                        <th class="text-end">Total</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${comanda.detalles.map(detalle => `
                                        <tr>
                                            <td>${detalle.item_nombre}</td>
                                            <td class="text-center">${detalle.cantidad}</td>
                                            <td class="text-end">$${detalle.precio_unitario.toFixed(2)}</td>
                                            <td class="text-end">$${detalle.total.toFixed(2)}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                                <tfoot>
                                    <tr>
                                        <th colspan="3" class="text-end">Total:</th>
                                        <th class="text-end">$${comanda.total.toFixed(2)}</th>
                                    </tr>
                                </tfoot>
                            </table>
                        </div>
                        <div class="text-center mt-3 no-print">
                            <button onclick="window.print()" class="btn btn-primary">Imprimir</button>
                            <button onclick="window.close()" class="btn btn-secondary">Cerrar</button>
                        </div>
                    </body>
                </html>
            `);
            ventana.document.close();
        })
        .catch(error => {
            console.error('Error:', error);
            window.mostrarNotificacion('Error al generar la impresión', 'danger');
        });
};

window.imprimirComandaDetalle = function() {
    if (window.comandaActual) {
        window.imprimirComanda(window.comandaActual.id);
    } else {
        window.mostrarNotificacion('No hay comanda seleccionada', 'warning');
    }
};

window.imprimirListadoComandas = function() {
    const ventana = window.open('', '_blank');
    const tabla = document.getElementById('tabla-comandas').cloneNode(true);
    
    // Remover los botones de acciones
    const botonesAccion = tabla.querySelectorAll('td:last-child');
    botonesAccion.forEach(td => td.remove());
    
    ventana.document.write(`
        <html>
            <head>
                <title>Listado de Comandas</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
                <style>
                    @media print {
                        body { margin: 0; padding: 15px; }
                        .no-print { display: none; }
                    }
                    .ticket {
                        max-width: 800px;
                        margin: 0 auto;
                        padding: 20px;
                    }
                    .ticket-header {
                        text-align: center;
                        margin-bottom: 20px;
                    }
                </style>
            </head>
            <body>
                <div class="ticket">
                    <div class="ticket-header">
                        <h4>Sistema de Comandas</h4>
                        <p>Listado de Comandas</p>
                        <p>Fecha: ${new Date().toLocaleString()}</p>
                    </div>
                    ${tabla.outerHTML}
                </div>
                <div class="text-center mt-3 no-print">
                    <button onclick="window.print()" class="btn btn-primary">Imprimir</button>
                    <button onclick="window.close()" class="btn btn-secondary">Cerrar</button>
                </div>
            </body>
        </html>
    `);
    ventana.document.close();
};

// Función para filtrar comandas
window.filtrarComandas = function() {
    const filtroEstatus = document.getElementById('filtroEstatus').value.toLowerCase();
    const filtroMesa = document.getElementById('filtroMesa').value;
    const filtroUsuario = document.getElementById('filtroUsuario').value;
    const filtroFecha = document.getElementById('filtroFecha').value;

    const filas = document.querySelectorAll('#comandas-table-body tr');
    let comandasVisibles = 0;

    filas.forEach(fila => {
        const estatus = fila.getAttribute('data-estatus').toLowerCase();
        const mesa = fila.getAttribute('data-mesa');
        const usuario = fila.getAttribute('data-usuario');
        const fecha = fila.getAttribute('data-fecha');

        const cumpleEstatus = !filtroEstatus || estatus === filtroEstatus;
        const cumpleMesa = !filtroMesa || mesa === filtroMesa;
        const cumpleUsuario = !filtroUsuario || usuario === filtroUsuario;
        const cumpleFecha = !filtroFecha || fecha === filtroFecha;

        if (cumpleEstatus && cumpleMesa && cumpleUsuario && cumpleFecha) {
            fila.style.display = '';
            comandasVisibles++;
        } else {
            fila.style.display = 'none';
        }
    });

    // Mostrar mensaje si no hay resultados
    const mensajeNoResultados = document.getElementById('mensaje-no-resultados');
    if (comandasVisibles === 0) {
        if (!mensajeNoResultados) {
            const mensaje = document.createElement('tr');
            mensaje.id = 'mensaje-no-resultados';
            mensaje.innerHTML = `
                <td colspan="7" class="text-center py-3">
                    <div class="alert alert-info mb-0">
                        No se encontraron comandas con los filtros seleccionados
                    </div>
                </td>
            `;
            document.getElementById('comandas-table-body').appendChild(mensaje);
        }
    } else if (mensajeNoResultados) {
        mensajeNoResultados.remove();
    }
};

// Función para inicializar la sección de impresoras
window.inicializarImpresoras = function() {
    const modal = document.getElementById('impresoraModal');
    const form = document.getElementById('impresoraForm');
    const tipoSelect = document.getElementById('tipo');
    const redFields = document.querySelectorAll('.red-fields');
    const windowsPrinterFields = document.querySelector('.windows-printer-fields');
    const windowsPrinterSelect = document.getElementById('windowsPrinterSelect');
    const nombreInput = document.getElementById('nombre');
    
    // Función para actualizar la visibilidad de los campos
    function updateFieldVisibility() {
        const selectedType = tipoSelect.value;
        if (selectedType === 'red') {
            redFields.forEach(field => field.style.display = 'block');
            windowsPrinterFields.style.display = 'none';
            nombreInput.readOnly = false;
            windowsPrinterSelect.value = '';
        } else if (selectedType === 'windows') {
            redFields.forEach(field => field.style.display = 'none');
            windowsPrinterFields.style.display = 'block';
            nombreInput.readOnly = true;
            document.getElementById('ip').value = '';
            document.getElementById('puerto').value = '';
            if (windowsPrinterSelect.value) {
                nombreInput.value = windowsPrinterSelect.value;
            }
        } else {
            redFields.forEach(field => field.style.display = 'none');
            windowsPrinterFields.style.display = 'none';
            nombreInput.readOnly = false;
        }
    }

    // Cargar impresoras de Windows al abrir el modal
    modal.addEventListener('show.bs.modal', function() {
        form.reset();
        document.getElementById('impresoraId').value = '';
        document.querySelector('.modal-title').textContent = 'Nueva Impresora';

        tipoSelect.value = 'windows';
        updateFieldVisibility();

        fetch('/api/windows_printers')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(printers => {
                windowsPrinterSelect.innerHTML = '';
                if (printers.length > 0) {
                    printers.forEach(printer => {
                        const option = document.createElement('option');
                        option.value = printer;
                        option.textContent = printer;
                        windowsPrinterSelect.appendChild(option);
                    });
                    windowsPrinterSelect.value = printers[0];
                    nombreInput.value = printers[0];
                } else {
                    windowsPrinterSelect.innerHTML = '<option value="">No se encontraron impresoras de Windows</option>';
                    nombreInput.value = '';
                }
            })
            .catch(error => {
                console.error('Error al cargar impresoras de Windows:', error);
                windowsPrinterSelect.innerHTML = '<option value="">Error al cargar impresoras</option>';
                alert('Error al cargar impresoras de Windows. Por favor, revisa la consola para más detalles.');
            });
    });
    
    // Actualizar nombreInput al seleccionar impresora de Windows
    windowsPrinterSelect.addEventListener('change', function() {
        nombreInput.value = this.value;
    });

    // Mostrar/ocultar campos según tipo de impresora
    tipoSelect.addEventListener('change', updateFieldVisibility);
    
    // Editar impresora
    document.querySelectorAll('.editar-impresora').forEach(button => {
        button.addEventListener('click', function() {
            const id = this.dataset.id;
            const nombre = this.dataset.nombre;
            const tipo = this.dataset.tipo;
            const ip = this.dataset.ip;
            const puerto = this.dataset.puerto;
            const estatus = this.dataset.estatus;
            const grupos = this.dataset.grupos ? this.dataset.grupos.split(',') : [];
            
            document.getElementById('impresoraId').value = id;
            nombreInput.value = nombre;
            tipoSelect.value = tipo;
            document.getElementById('ip').value = ip;
            document.getElementById('puerto').value = puerto;
            document.getElementById('estatus').value = estatus;
            
            // Marcar grupos asignados
            document.querySelectorAll('input[name="grupos"]').forEach(checkbox => {
                checkbox.checked = grupos.includes(checkbox.value);
            });
            
            // Si es tipo 'windows', seleccionar la impresora en el dropdown
            if (tipo === 'windows') {
                windowsPrinterSelect.value = nombre;
                windowsPrinterSelect.dispatchEvent(new Event('change'));
            }

            updateFieldVisibility();
            document.querySelector('.modal-title').textContent = 'Editar Impresora';
            new bootstrap.Modal(modal).show();
        });
    });
    
    // Eliminar impresora
    document.querySelectorAll('.eliminar-impresora').forEach(button => {
        button.addEventListener('click', function() {
            if (confirm('¿Estás seguro de eliminar esta impresora?')) {
                const id = this.dataset.id;
                fetch(`/api/impresoras/${id}`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        location.reload();
                    } else {
                        alert(data.message);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error al eliminar la impresora');
                });
            }
        });
    });
    
    // Guardar impresora
    document.getElementById('guardarImpresora').addEventListener('click', function() {
        const id = document.getElementById('impresoraId').value;
        const tipo = tipoSelect.value;
        const ip = document.getElementById('ip').value;
        const puerto = document.getElementById('puerto').value;
        const estatus = document.getElementById('estatus').value;
        let nombre = nombreInput.value;

        // Para impresoras Windows, el nombre es el seleccionado del dropdown
        if (tipo === 'windows') {
            nombre = windowsPrinterSelect.value;
            if (!nombre) {
                alert('Debe seleccionar una impresora de Windows');
                return;
            }
        }

        // Validar campos según tipo
        if (tipo === 'red' && (!ip || !puerto)) {
            alert('IP y puerto son requeridos para impresoras de red');
            return;
        }
        
        // Obtener grupos seleccionados
        const grupos = Array.from(document.querySelectorAll('input[name="grupos"]:checked'))
            .map(checkbox => checkbox.value);
        
        const data = {
            nombre,
            tipo,
            ip: tipo === 'red' ? ip : null,
            puerto: tipo === 'red' ? puerto : null,
            estatus,
            grupos
        };
        
        const url = id ? `/api/impresoras/${id}` : '/api/impresoras';
        const method = id ? 'PUT' : 'POST';
        
        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert(data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error al guardar la impresora');
        });
    });
};

// Función para exportar reporte de ventas a PDF
window.exportarPDFVentas = function() {
    const fechaInicio = document.getElementById('fecha-inicio').value;
    const fechaFin = document.getElementById('fecha-fin').value;
    
    let url = `/api/exportar/reporte/ventas`;
    const params = new URLSearchParams();
    
    if (fechaInicio) params.append('fecha_inicio', fechaInicio);
    if (fechaFin) params.append('fecha_fin', fechaFin);
    
    if (params.toString()) {
        url += `?${params.toString()}`;
    }
    
    window.location.href = url;
}

// Función para exportar listado de comandas a PDF
window.exportarPDFComandas = function() {
    window.location.href = '/api/exportar/reporte/comandas';
}

// Función para cargar el formulario de producto en un modal
function cargarFormularioProducto(productoId = null) {
    // Convertir a número si es string y no es null
    const id = productoId ? parseInt(productoId) : null;
    const url = id ? `/formulario/inventario/producto?id=${id}` : '/formulario/inventario/producto';
    const titulo = id ? 'Editar Producto' : 'Nuevo Producto';
    
    // Mostrar indicador de carga
    $('#modalBody').html(`
        <div class="text-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Cargando...</span>
            </div>
            <p class="mt-2">Cargando formulario...</p>
        </div>
    `);
    
    $('#modalTitle').text(titulo);
    const modal = new bootstrap.Modal(document.getElementById('formModal'));
    modal.show();
    
    // Cargar el formulario
    fetch(url)
        .then(response => response.text())
        .then(html => {
            $('#modalBody').html(html);
        })
        .catch(error => {
            console.error('Error:', error);
            $('#modalBody').html(`
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i> Error al cargar el formulario
                </div>
            `);
        });
}

// Función para eliminar producto
function eliminarProducto(productoId) {
    // Convertir a número si es string
    const id = parseInt(productoId);
    
    Swal.fire({
        title: '¿Está seguro?',
        text: "Esta acción no se puede deshacer",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Sí, eliminar',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            $.ajax({
                url: `/api/inventario/productos/${id}`,
                method: 'DELETE',
                success: function(response) {
                    if (response.success) {
                        Swal.fire(
                            'Eliminado',
                            response.message,
                            'success'
                        ).then(() => {
                            // Recargar la sección de productos
                            cargarSeccion('inventario/productos');
                        });
                    } else {
                        Swal.fire(
                            'Error',
                            response.message,
                            'error'
                        );
                    }
                },
                error: function(xhr) {
                    let message = 'Error al eliminar el producto';
                    if (xhr.responseJSON && xhr.responseJSON.message) {
                        message = xhr.responseJSON.message;
                    } else if (xhr.responseText) {
                        try {
                            const resp = JSON.parse(xhr.responseText);
                            if (resp.message) message = resp.message;
                        } catch (e) {}
                    }
                    Swal.fire(
                        'Error',
                        message,
                        'error'
                    );
                }
            });
        }
    });
}

function mostrarAlerta(tipo, mensaje) {
    const alerta = document.createElement('div');
    alerta.className = `alert alert-${tipo} alert-dismissible fade show`;
    alerta.role = 'alert';
    alerta.innerHTML = `
        ${mensaje}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    const contenedor = document.getElementById('alert-container');
    contenedor.innerHTML = '';
    contenedor.appendChild(alerta);
    
    setTimeout(() => {
        alerta.classList.remove('show');
        setTimeout(() => alerta.remove(), 150);
    }, 5000);
}

function mostrarNotificacion(mensaje, tipo = 'success') {
    const notificacion = document.createElement('div');
    notificacion.className = `alert alert-${tipo} position-fixed top-0 end-0 m-3`;
    notificacion.style.zIndex = '1100';
    notificacion.innerHTML = `
        ${mensaje}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    document.body.appendChild(notificacion);
    
    // Auto-cerrar después de 5 segundos
    setTimeout(() => {
        notificacion.remove();
    }, 5000);
}

// Función para cargar el formulario de compra en un modal
function cargarFormularioCompra(compraId = null) {
    // Convertir a número si es string y no es null
    const id = compraId ? parseInt(compraId) : null;
    const url = id ? `/formulario/inventario/compra?id=${id}` : '/formulario/inventario/compra';
    const titulo = id ? 'Editar Compra' : 'Nueva Compra';
    
    // Mostrar indicador de carga
    $('#modalBody').html(`
        <div class="text-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Cargando...</span>
            </div>
            <p class="mt-2">Cargando formulario...</p>
        </div>
    `);
    
    $('#modalTitle').text(titulo);
    const modal = new bootstrap.Modal(document.getElementById('formModal'));
    modal.show();
    
    // Cargar el formulario
    fetch(url)
        .then(response => response.text())
        .then(html => {
            $('#modalBody').html(html);
        })
        .catch(error => {
            console.error('Error:', error);
            $('#modalBody').html(`
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i> Error al cargar el formulario
                </div>
            `);
        });
}

// Función para eliminar compra
function eliminarCompra(compraId) {
    // Convertir a número si es string
    const id = parseInt(compraId);
    
    Swal.fire({
        title: '¿Está seguro?',
        text: "Esta acción no se puede deshacer",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Sí, eliminar',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            $.ajax({
                url: `/api/inventario/compras/${id}`,
                method: 'DELETE',
                success: function(response) {
                    if (response.success) {
                        Swal.fire(
                            'Eliminado',
                            response.message,
                            'success'
                        ).then(() => {
                            // Recargar la sección de compras
                            cargarSeccion('inventario/compras');
                        });
                    } else {
                        Swal.fire(
                            'Error',
                            response.message,
                            'error'
                        );
                    }
                },
                error: function(xhr) {
                    const response = xhr.responseJSON;
                    Swal.fire(
                        'Error',
                        response ? response.message : 'Error al eliminar la compra',
                        'error'
                    );
                }
            });
        }
    });
}

function cargarFormularioReceta(recetaId = null) {
    // Convertir a número si es string y no es null
    const id = recetaId ? parseInt(recetaId) : null;
    const url = id ? `/formulario/inventario/receta?id=${id}` : '/formulario/inventario/receta';
    const titulo = id ? 'Editar Receta' : 'Nueva Receta';

    // Mostrar indicador de carga
    $('#modalBody').html(`
        <div class="text-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Cargando...</span>
            </div>
            <p class="mt-2">Cargando formulario...</p>
        </div>
    `);

    $('#modalTitle').text(titulo);
    const modal = new bootstrap.Modal(document.getElementById('formModal'));
    modal.show();

    // Cargar el formulario
    fetch(url)
        .then(response => response.text())
        .then(html => {
            $('#modalBody').html(html);
        })
        .catch(error => {
            console.error('Error:', error);
            $('#modalBody').html(`
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i> Error al cargar el formulario
                </div>
            `);
        });
}

function cargarFormularioProduccion(produccionId = null) {
    // Convertir a número si es string y no es null
    const id = produccionId ? parseInt(produccionId) : null;
    const url = id ? `/formulario/inventario/produccion?id=${id}` : '/formulario/inventario/produccion';
    const titulo = id ? 'Editar Producción' : 'Nueva Producción';

    // Mostrar indicador de carga
    $('#modalBody').html(`
        <div class="text-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Cargando...</span>
            </div>
            <p class="mt-2">Cargando formulario...</p>
        </div>
    `);

    $('#modalTitle').text(titulo);
    const modal = new bootstrap.Modal(document.getElementById('formModal'));
    modal.show();

    // Cargar el formulario
    fetch(url)
        .then(response => response.text())
        .then(html => {
            $('#modalBody').html(html);
        })
        .catch(error => {
            console.error('Error:', error);
            $('#modalBody').html(`
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i> Error al cargar el formulario
                </div>
            `);
        });
}