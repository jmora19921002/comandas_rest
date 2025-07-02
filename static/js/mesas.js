// mesas.js - Funciones para la gestión de mesas y comandas
// Requiere Bootstrap 5 y fetch API

// Variables globales para pagos
let pagosAgregados = [];

// Esperar a que el DOM esté listo
window.addEventListener('DOMContentLoaded', function () {
    // Mostrar modal de selección de mesas si no hay mesa seleccionada
    if (document.getElementById('mesa-seleccionada').textContent === 'Ninguna') {
        const modalMesas = new bootstrap.Modal(document.getElementById('modalMesas'));
        modalMesas.show();
    }
    // Selección de mesa
    document.querySelectorAll('.mesa-card').forEach(function(card) {
        card.addEventListener('click', function() {
            seleccionarMesa(this);
        });
    });

    // Botón para limpiar cliente
    const btnLimpiarCliente = document.getElementById('btn-limpiar-cliente');
    if (btnLimpiarCliente) {
        btnLimpiarCliente.addEventListener('click', limpiarCliente);
    }

    // Búsqueda de cliente
    const busquedaCliente = document.getElementById('busqueda-cliente');
    if (busquedaCliente) {
        busquedaCliente.addEventListener('input', buscarClientes);
    }

    // Botón para nuevo cliente
    const btnNuevoCliente = document.getElementById('btn-nuevo-cliente');
    if (btnNuevoCliente) {
        btnNuevoCliente.addEventListener('click', function() {
            const modal = new bootstrap.Modal(document.getElementById('modalNuevoCliente'));
            modal.show();
        });
    }

    // Formulario de nuevo cliente
    const formNuevoCliente = document.getElementById('form-nuevo-cliente');
    if (formNuevoCliente) {
        formNuevoCliente.addEventListener('submit', crearNuevoCliente);
    }

    // Agregar producto desde modal
    document.querySelectorAll('.agregar-producto').forEach(function(btn) {
        btn.addEventListener('click', function() {
            agregarProducto(this.closest('.producto-card'));
        });
    });

    // Al hacer clic en 'Totalizar y Pagar', abrir el modal de medios de pago y poblar datos
    const btnTotalizar = document.getElementById('btn-totalizar');
    if (btnTotalizar) {
        btnTotalizar.addEventListener('click', async function(e) {
            if (!clienteObligatorio()) return;
            const comandaId = document.getElementById('comanda-id').value;
            let guardado = true;
            if (!comandaId) {
                // Si la comanda es nueva, guardar antes de abrir el modal de pago
                guardado = await guardarComanda(true);
            } else {
                // Si la comanda ya existe, actualizarla antes de abrir el modal de pago
                guardado = await guardarComanda(true); // guardarComanda detecta si es update o insert
            }
            if (guardado) {
                poblarModalPago();
                const modalPago = new bootstrap.Modal(document.getElementById('modalPago'));
                modalPago.show();
            }
        });
    }

    // Guardar comanda
    const btnGuardar = document.getElementById('btn-guardar');
    if (btnGuardar) {
        btnGuardar.addEventListener('click', function(e) {
            if (!clienteObligatorio()) return;
            guardarComanda();
        });
    }

    // Evento para agregar pago
    const btnAdicionarPago = document.querySelector('#modalPago button[onclick="adicionarPago()"]');
    if (btnAdicionarPago) {
        btnAdicionarPago.addEventListener('click', adicionarPago);
    }

    // Interceptar el click en 'Procesar Pago' para crédito
    const btnProcesarPago = document.getElementById('btn-procesar-pago');
    if (btnProcesarPago) {
        btnProcesarPago.addEventListener('click', function(e) {
            const esCredito = document.getElementById('es-credito').checked;
            if (esCredito) {
                e.preventDefault();
                // Mostrar modal de validación de admin
                const modalAdmin = new bootstrap.Modal(document.getElementById('modalValidacionAdmin'));
                document.getElementById('admin-username').value = '';
                document.getElementById('admin-password').value = '';
                modalAdmin.show();
            } else {
                procesarPago();
            }
        });
    }

    // Validar admin y procesar pago a crédito
    const btnValidarAdmin = document.getElementById('btn-validar-admin');
    if (btnValidarAdmin) {
        btnValidarAdmin.addEventListener('click', function() {
            const username = document.getElementById('admin-username').value.trim();
            const password = document.getElementById('admin-password').value.trim();
            if (!username || !password) {
                mostrarAlerta('Debe ingresar usuario y contraseña de admin.', 'danger');
                return;
            }
            fetch('/api/validar-admin', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    // Cerrar modal y procesar pago a crédito
                    const modalAdmin = bootstrap.Modal.getInstance(document.getElementById('modalValidacionAdmin'));
                    if (modalAdmin) modalAdmin.hide();
                    procesarPago();
                } else {
                    mostrarAlerta(data.error || 'Credenciales incorrectas.', 'danger');
                }
            })
            .catch(() => {
                mostrarAlerta('Error de conexión al validar admin.', 'danger');
            });
        });
    }

    // Botón para usar monto restante en el campo de monto
    const btnMontoRestante = document.getElementById('btn-monto-restante');
    if (btnMontoRestante) {
        btnMontoRestante.addEventListener('click', function() {
            const restante = document.getElementById('restante').textContent.replace('$','').replace(',','');
            document.getElementById('nuevo-monto').value = parseFloat(restante) || 0;
        });
    }

    // Imprimir comanda
    const btnImprimir = document.getElementById('btn-imprimir');
    if (btnImprimir) {
        btnImprimir.addEventListener('click', function(e) {
            if (!clienteObligatorio()) return;
            imprimirComanda();
        });
    }

    // Cierre del día
    const btnCierreDia = document.getElementById('btn-cierre-dia');
    if (btnCierreDia) {
        btnCierreDia.addEventListener('click', mostrarCierreDia);
    }

    // Mostrar mensaje especial si se selecciona Cachea
    const inputMedioPago = document.getElementById('nuevo-medio-pago');
    const inputMonto = document.getElementById('nuevo-monto');
    const infoCachea = document.createElement('div');
    infoCachea.id = 'info-cachea';
    infoCachea.className = 'form-text text-info';
    infoCachea.style.display = 'none';
    infoCachea.innerHTML = '<i class="bi bi-info-circle"></i> Ingrese el monto que paga el cliente con Cachea. El resto quedará como crédito.';
    inputMonto.parentNode.appendChild(infoCachea);

    function actualizarInfoCachea() {
        const medioPago = inputMedioPago.options[inputMedioPago.selectedIndex]?.textContent?.toLowerCase() || '';
        if (medioPago.includes('cachea') || medioPago.includes('cachéa')) {
            infoCachea.style.display = '';
        } else {
            infoCachea.style.display = 'none';
        }
    }
    inputMedioPago.addEventListener('change', actualizarInfoCachea);

    // Marcar crédito automáticamente si Cachea y monto < restante
    inputMonto.addEventListener('input', function() {
        const medioPago = inputMedioPago.options[inputMedioPago.selectedIndex]?.textContent?.toLowerCase() || '';
        const totalComanda = parseFloat(document.getElementById('total-comanda').textContent.replace('$',''));
        let totalPagado = 0;
        pagosAgregados.forEach(p => { totalPagado += p.monto; });
        const montoActual = parseFloat(inputMonto.value) || 0;
        const restante = Math.max(0, totalComanda - totalPagado);
        const checkCredito = document.getElementById('es-credito');
        if ((medioPago.includes('cachea') || medioPago.includes('cachéa')) && montoActual < restante) {
            checkCredito.checked = true;
            actualizarResumenPagos();
        } else if ((medioPago.includes('cachea') || medioPago.includes('cachéa')) && montoActual >= restante) {
            checkCredito.checked = false;
            actualizarResumenPagos();
        }
    });
});

// Seleccionar una mesa y actualizar el panel de comanda
function seleccionarMesa(card) {
    const mesaId = card.getAttribute('data-id');
    const mesaNombre = card.getAttribute('data-nombre');
    document.getElementById('mesa-seleccionada').textContent = mesaNombre;
    limpiarComanda();
    fetch(`/api/comanda?mesa_id=${mesaId}`)
        .then(res => res.json())
        .then(data => {
            if (data && data.comanda) {
                poblarComanda(data.detalles || []);
                poblarClienteComanda(data.comanda, data.comanda);
                document.getElementById('comanda-id').value = data.comanda.id || '';
            } else {
                document.getElementById('comanda-id').value = '';
            }
            habilitarBotonesComanda(true);
            const modalMesas = bootstrap.Modal.getInstance(document.getElementById('modalMesas'));
            if (modalMesas) modalMesas.hide();
        });
}

// Habilitar o deshabilitar los botones de acción de la comanda
function habilitarBotonesComanda(habilitar) {
    document.getElementById('btn-imprimir').disabled = !habilitar;
    document.getElementById('btn-guardar').disabled = !habilitar;
    document.getElementById('btn-totalizar').disabled = !habilitar;
    document.getElementById('btn-cerrar').disabled = !habilitar;
}

// Limpiar la tabla de productos y datos de cliente
function limpiarComanda() {
    document.getElementById('detalle-comanda').innerHTML = '';
    document.getElementById('total-comanda').textContent = '$0.00';
    limpiarCliente();
    habilitarBotonesComanda(false);
}

// Poblar la tabla de productos de la comanda
function poblarComanda(detalles) {
    let tbody = document.getElementById('detalle-comanda');
    tbody.innerHTML = '';
    detalles.forEach(detalle => {
        let tr = document.createElement('tr');
        tr.setAttribute('data-id', detalle.producto_id);
        tr.setAttribute('data-stock', detalle.stock);
        tr.innerHTML = `
            <td>${detalle.nombre}${detalle.nota ? '<br><small>' + detalle.nota + '</small>' : ''}</td>
            <td><input type="number" class="form-control form-control-sm cantidad-input" value="${detalle.cantidad}" min="1" max="${detalle.stock}" style="width:60px"></td>
            <td>$${detalle.precio_unitario.toFixed(2)}</td>
            <td class="total-cell">$${detalle.total.toFixed(2)}</td>
            <td><button class="btn btn-danger btn-sm eliminar-item">X</button></td>
        `;
        tbody.appendChild(tr);
        // Evento para eliminar el item
        tr.querySelector('.eliminar-item').addEventListener('click', function() {
            tr.remove();
            actualizarTotalComanda();
        });
        // Evento para cambiar cantidad
        const cantidadInput = tr.querySelector('.cantidad-input');
        cantidadInput.addEventListener('input', function() {
            let cantidad = parseInt(this.value) || 1;
            const stockFila = parseFloat(tr.getAttribute('data-stock'));
            this.max = stockFila; // <-- Asegura que el max sea el stock real
            if (cantidad < 1) { this.value = 1; cantidad = 1; }
            if (cantidad > stockFila) {
                mostrarAlerta(`No hay suficiente stock para "${detalle.nombre}". Disponible: ${stockFila}`, 'danger', 3000);
                this.value = stockFila;
                cantidad = stockFila;
            }
            let totalCell = tr.querySelector('.total-cell');
            totalCell.textContent = '$' + (cantidad * detalle.precio_unitario).toFixed(2);
            actualizarTotalComanda();
        });
    });
    actualizarTotalComanda();
}

// Poblar los datos del cliente de la comanda
function poblarClienteComanda(comanda, comandaObj) {
    // Si hay cliente asociado
    if (comanda && comanda.cliente_id) {
        document.getElementById('cliente-id').value = comanda.cliente_id;
        let nombre = comanda.cliente_nombre || '';
        let cedula = comanda.cliente_cedula_rif || '';
        let telefono = comanda.cliente_telefono || '';
        document.getElementById('busqueda-cliente').value = `${nombre} (${cedula})`;
        document.getElementById('cliente-seleccionado-info').textContent = `${nombre} - ${telefono}`;
        document.getElementById('btn-limpiar-cliente').style.display = 'inline-block';
    } else {
        limpiarCliente();
    }
}

// Limpiar la selección de cliente
function limpiarCliente() {
    document.getElementById('cliente-id').value = '';
    document.getElementById('busqueda-cliente').value = '';
    document.getElementById('cliente-seleccionado-info').textContent = '';
    document.getElementById('btn-limpiar-cliente').style.display = 'none';
}

// Buscar clientes por nombre, cédula o RIF
function buscarClientes() {
    const query = this.value.trim();
    const resultados = document.getElementById('resultados-clientes');
    if (query.length < 2) {
        resultados.style.display = 'none';
        resultados.innerHTML = '';
        return;
    }
    fetch(`/api/clientes/buscar?q=${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(data => {
            resultados.innerHTML = '';
            if (data.length > 0) {
                data.forEach(cliente => {
                    const item = document.createElement('button');
                    item.type = 'button';
                    item.className = 'list-group-item list-group-item-action';
                    item.textContent = `${cliente.nombre} (${cliente.cedula_rif})`;
                    item.onclick = function() {
                        seleccionarCliente(cliente);
                    };
                    resultados.appendChild(item);
                });
                resultados.style.display = 'block';
            } else {
                resultados.style.display = 'none';
            }
        });
}

// Seleccionar un cliente de la lista
function seleccionarCliente(cliente) {
    document.getElementById('cliente-id').value = cliente.id;
    document.getElementById('busqueda-cliente').value = `${cliente.nombre} (${cliente.cedula_rif})`;
    document.getElementById('cliente-seleccionado-info').textContent = `${cliente.nombre} - ${cliente.telefono || ''}`;
    document.getElementById('btn-limpiar-cliente').style.display = 'inline-block';
    document.getElementById('resultados-clientes').style.display = 'none';
}

// Crear un nuevo cliente desde el formulario modal
function crearNuevoCliente(e) {
    e.preventDefault();
    const form = e.target;
    const data = {
        nombre: form['nombre'].value,
        cedula_rif: form['cedula_rif'].value,
        telefono: form['telefono'].value,
        direccion: form['direccion'].value,
        correo: form['correo'].value
    };
    fetch('/api/clientes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(res => res.json())
    .then(resp => {
        if (resp.success) {
            // Seleccionar el nuevo cliente automáticamente
            seleccionarCliente({
                id: resp.cliente_id,
                nombre: data.nombre,
                cedula_rif: data.cedula_rif,
                telefono: data.telefono
            });
            bootstrap.Modal.getInstance(document.getElementById('modalNuevoCliente')).hide();
        } else {
            alert('Error al crear cliente: ' + (resp.message || resp.error));
        }
    });
}

// Agregar un producto a la comanda
function agregarProducto(card) {
    const productoId = card.getAttribute('data-id');
    const nombre = card.getAttribute('data-name');
    const precio = parseFloat(card.getAttribute('data-precio'));
    const nota = card.querySelector('.producto-nota').value;
    const stock = parseFloat(card.getAttribute('data-stock'));

    // Verificar stock antes de agregar
    let tbody = document.getElementById('detalle-comanda');
    let filaExistente = tbody.querySelector(`tr[data-id='${productoId}']`);
    let cantidadActual = 0;
    if (filaExistente) {
        cantidadActual = parseInt(filaExistente.querySelector('.cantidad-input').value) || 0;
    }
    if (cantidadActual + 1 > stock) {
        mostrarAlerta(`No hay suficiente stock para "${nombre}". Disponible: ${stock}`, 'danger', 3000);
        return;
    }
    if (filaExistente) {
        // Si ya existe, aumenta la cantidad
        let cantidadInput = filaExistente.querySelector('.cantidad-input');
        cantidadInput.value = parseInt(cantidadInput.value) + 1;
        // Actualiza el total de la fila
        let totalCell = filaExistente.querySelector('.total-cell');
        totalCell.textContent = '$' + (parseInt(cantidadInput.value) * precio).toFixed(2);
    } else {
        // Si no existe, crea una nueva fila
        let tr = document.createElement('tr');
        tr.setAttribute('data-id', productoId);
        tr.setAttribute('data-stock', stock);
        tr.innerHTML = `
            <td>${nombre}${nota ? '<br><small>' + nota + '</small>' : ''}</td>
            <td><input type="number" class="form-control form-control-sm cantidad-input" value="1" min="1" max="${stock}" style="width:60px"></td>
            <td>$${precio.toFixed(2)}</td>
            <td class="total-cell">$${precio.toFixed(2)}</td>
            <td><button class="btn btn-danger btn-sm eliminar-item">X</button></td>
        `;
        tbody.appendChild(tr);

        // Evento para eliminar el item
        tr.querySelector('.eliminar-item').addEventListener('click', function() {
            tr.remove();
            actualizarTotalComanda();
        });
        // Evento para cambiar cantidad
        tr.querySelector('.cantidad-input').addEventListener('input', function() {
            let cantidad = parseInt(this.value) || 1;
            const stockFila = parseFloat(tr.getAttribute('data-stock'));
            this.max = stockFila; // <-- Asegura que el max sea el stock real
            if (cantidad < 1) { this.value = 1; cantidad = 1; }
            if (cantidad > stockFila) {
                mostrarAlerta(`No hay suficiente stock para "${nombre}". Disponible: ${stockFila}`, 'danger', 3000);
                this.value = stockFila;
                cantidad = stockFila;
            }
            let totalCell = tr.querySelector('.total-cell');
            totalCell.textContent = '$' + (cantidad * precio).toFixed(2);
            actualizarTotalComanda();
        });
    }
    actualizarTotalComanda();
    // Habilitar botones de acción
    habilitarBotonesComanda(true);
    // Cerrar el modal del grupo de productos
    let modal = card.closest('.modal');
    if (modal) {
        let modalInstance = bootstrap.Modal.getInstance(modal);
        if (modalInstance) modalInstance.hide();
    }
}

// Actualiza el total general de la comanda
function actualizarTotalComanda() {
    let total = 0;
    let tbody = document.getElementById('detalle-comanda');
    tbody.querySelectorAll('tr').forEach(function(tr) {
        let cantidad = parseInt(tr.querySelector('.cantidad-input').value) || 1;
        let precio = parseFloat(tr.querySelector('td:nth-child(3)').textContent.replace('$',''));
        total += cantidad * precio;
    });
    document.getElementById('total-comanda').textContent = '$' + total.toFixed(2);
}

// Guardar comanda
async function guardarComanda(silencioso = false) {
    // Obtener mesa seleccionada
    const mesaNombre = document.getElementById('mesa-seleccionada').textContent;
    if (!mesaNombre || mesaNombre === 'Ninguna') {
        if (!silencioso) mostrarAlerta('Debe seleccionar una mesa antes de guardar.', 'danger');
        return false;
    }
    // Buscar el id de la mesa seleccionada
    let mesaId = null;
    document.querySelectorAll('.mesa-card').forEach(function(card) {
        if (card.getAttribute('data-nombre') === mesaNombre) {
            mesaId = card.getAttribute('data-id');
        }
    });
    if (!mesaId) {
        if (!silencioso) mostrarAlerta('No se pudo identificar la mesa seleccionada.', 'danger');
        return false;
    }
    // Obtener cliente
    const clienteId = document.getElementById('cliente-id').value || null;
    if (!clienteId) {
        if (!silencioso) mostrarAlerta('Debe seleccionar un cliente antes de guardar.', 'danger');
        return false;
    }
    // Obtener tipo de servicio
    const servicio = document.getElementById('servicio-tipo').value || 'local';
    // Obtener productos
    const items = [];
    document.querySelectorAll('#detalle-comanda tr').forEach(function(tr) {
        const productoId = tr.getAttribute('data-id');
        const nombre = tr.querySelector('td').innerText.split('\n')[0];
        const cantidad = parseInt(tr.querySelector('.cantidad-input').value) || 1;
        const precio = parseFloat(tr.querySelector('td:nth-child(3)').textContent.replace('$',''));
        const notaElem = tr.querySelector('td small');
        const nota = notaElem ? notaElem.textContent : '';
        items.push({ producto_id: productoId, cantidad, precio, nota });
    });
    if (items.length === 0) {
        if (!silencioso) mostrarAlerta('Debe agregar al menos un producto.', 'danger');
        return false;
    }
    // Construir payload
    const comandaId = document.getElementById('comanda-id').value;
    const payload = {
        mesa_id: mesaId,
        cliente_id: clienteId,
        servicio: servicio,
        items: items
    };
    if (comandaId) payload.comanda_id = comandaId;
    // Enviar al backend
    try {
        const res = await fetch('/api/comanda', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const resp = await res.json();
        if (resp.success) {
            // Si es silencioso (totalizar), solo actualizar comanda-id y retornar true
            if (silencioso) {
                if (resp.comanda_id) {
                    document.getElementById('comanda-id').value = resp.comanda_id;
                }
                return true;
            }
            mostrarAlerta('Comanda guardada exitosamente.', 'success', 1000);
            setTimeout(() => {
                limpiarComanda();
                document.getElementById('mesa-seleccionada').textContent = 'Ninguna';
                const modalMesas = new bootstrap.Modal(document.getElementById('modalMesas'));
                modalMesas.show();
            }, 1000);
            return true;
        } else {
            if (!silencioso) mostrarAlerta(resp.message || 'Error al guardar la comanda.', 'danger');
            return false;
        }
    } catch (e) {
        if (!silencioso) mostrarAlerta('Error de conexión al guardar la comanda.', 'danger');
        return false;
    }
}

// Mostrar alerta flotante que se cierra sola
function mostrarAlerta(mensaje, tipo = 'success', duracion = 2000) {
    try {
        // Crear el elemento de alerta
        const alerta = document.createElement('div');
        alerta.className = `alert alert-${tipo} alert-dismissible fade show position-fixed`;
        alerta.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alerta.innerHTML = `
            ${mensaje}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Agregar al body si existe
        if (document.body) {
            document.body.appendChild(alerta);
            
            // Auto-remover después del tiempo especificado
            setTimeout(() => {
                if (document.body.contains(alerta)) {
                    document.body.removeChild(alerta);
                }
            }, duracion);
        }
    } catch (error) {
        console.error('Error al mostrar alerta:', error);
        // Fallback: usar alert nativo
        alert(mensaje);
    }
}

function poblarModalPago() {
    // Limpiar pagos agregados
    pagosAgregados = [];
    actualizarResumenPagos();
    // Poblar datos de la comanda
    const mesaNombre = document.getElementById('mesa-seleccionada').textContent;
    document.getElementById('pago-mesa-nombre').textContent = mesaNombre;
    document.getElementById('pago-cliente-nombre').textContent = document.getElementById('busqueda-cliente').value;
    document.getElementById('pago-total').textContent = document.getElementById('total-comanda').textContent;
    // Limpiar campos de nuevo pago
    document.getElementById('nuevo-medio-pago').value = '';
    document.getElementById('nuevo-monto').value = '';
    document.getElementById('nuevo-referencia').value = '';
    document.getElementById('nuevo-banco').value = '';
    document.getElementById('nuevo-observaciones').value = '';
    document.getElementById('es-credito').checked = false;
    // Cargar medios de pago
    fetch('/api/medios-pago')
        .then(res => res.json())
        .then(data => {
            const select = document.getElementById('nuevo-medio-pago');
            select.innerHTML = '<option value="">Seleccionar...</option>';
            if (data.success && data.medios_pago) {
                data.medios_pago.forEach(m => {
                    const opt = document.createElement('option');
                    opt.value = m.id;
                    opt.textContent = m.nombre;
                    select.appendChild(opt);
                });
            }
        });
    // Deshabilitar procesar pago
    document.getElementById('btn-procesar-pago').disabled = true;
}

function adicionarPago() {
    const medioPagoId = document.getElementById('nuevo-medio-pago').value;
    const medioPagoNombre = document.getElementById('nuevo-medio-pago').selectedOptions[0]?.textContent || '';
    const monto = parseFloat(document.getElementById('nuevo-monto').value);
    const referencia = document.getElementById('nuevo-referencia').value;
    const banco = document.getElementById('nuevo-banco').value;
    const observaciones = document.getElementById('nuevo-observaciones').value;
    if (!medioPagoId || isNaN(monto) || monto <= 0) {
        mostrarAlerta('Debe seleccionar un medio de pago y monto válido.', 'danger');
        return;
    }
    pagosAgregados.push({ medio_pago_id: medioPagoId, medio_pago_nombre: medioPagoNombre, monto, referencia, banco, observaciones });
    actualizarResumenPagos();
    // Limpiar campos
    document.getElementById('nuevo-medio-pago').value = '';
    document.getElementById('nuevo-monto').value = '';
    document.getElementById('nuevo-referencia').value = '';
    document.getElementById('nuevo-banco').value = '';
    document.getElementById('nuevo-observaciones').value = '';
}

function actualizarResumenPagos() {
    // Mostrar pagos agregados
    const treeview = document.getElementById('treeview-pagos');
    treeview.innerHTML = '';
    let totalPagado = 0;
    if (pagosAgregados.length === 0) {
        treeview.innerHTML = `<div class="text-muted text-center py-4">
            <i class="bi bi-list-ul fs-1"></i>
            <p class="mt-2">No hay pagos agregados</p>
            <small>Agregue medios de pago desde el panel izquierdo</small>
        </div>`;
    } else {
        pagosAgregados.forEach((pago, idx) => {
            totalPagado += pago.monto;
            const div = document.createElement('div');
            div.className = 'pago-item-tree d-flex align-items-center justify-content-between mb-2 p-2';
            div.innerHTML = `
                <span><b>${pago.medio_pago_nombre}</b> - $${pago.monto.toFixed(2)}${pago.referencia ? ' <span class="badge bg-info">Ref: ' + pago.referencia + '</span>' : ''}${pago.banco ? ' <span class="badge bg-secondary">Banco: ' + pago.banco + '</span>' : ''}${pago.observaciones ? ' <span class="small">' + pago.observaciones + '</span>' : ''}</span>
                <button class="btn btn-outline-danger btn-sm" onclick="eliminarPago(${idx})"><i class="bi bi-trash"></i></button>
            `;
            treeview.appendChild(div);
        });
    }
    // Actualizar totales
    const totalComanda = parseFloat(document.getElementById('total-comanda').textContent.replace('$',''));
    document.getElementById('total-pagado').textContent = '$' + totalPagado.toFixed(2);
    const restante = Math.max(0, totalComanda - totalPagado);
    document.getElementById('restante').textContent = '$' + restante.toFixed(2);
    // Habilitar procesar pago si corresponde
    const esCredito = document.getElementById('es-credito').checked;
    document.getElementById('btn-procesar-pago').disabled = (!esCredito && (totalPagado < totalComanda || pagosAgregados.length === 0));
}

function eliminarPago(idx) {
    pagosAgregados.splice(idx, 1);
    actualizarResumenPagos();
}

// Actualizar resumen si se marca crédito
if (document.getElementById('es-credito')) {
    document.getElementById('es-credito').addEventListener('change', actualizarResumenPagos);
}

function procesarPago() {
    // Obtener mesa seleccionada
    const mesaNombre = document.getElementById('mesa-seleccionada').textContent;
    let mesaId = null;
    document.querySelectorAll('.mesa-card').forEach(function(card) {
        if (card.getAttribute('data-nombre') === mesaNombre) {
            mesaId = card.getAttribute('data-id');
        }
    });
    if (!mesaId) {
        mostrarAlerta('No se pudo identificar la mesa para el pago.', 'danger');
        return;
    }
    // Obtener comanda activa para la mesa
    fetch(`/api/comanda?mesa_id=${mesaId}`)
        .then(res => res.json())
        .then(data => {
            if (!data.comanda || !data.comanda.id) {
                mostrarAlerta('No se encontró la comanda para procesar el pago.', 'danger');
                return;
            }
            const comandaId = data.comanda.id;
            // Preparar payload
            const estatus_pago = document.getElementById('es-credito').checked ? 'credito' : 'pagado';
            fetch(`/api/comandas/${comandaId}/pagar`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pagos: pagosAgregados, estatus_pago })
            })
            .then(res => res.json())
            .then(resp => {
                if (resp.success) {
                    mostrarAlerta('Pago procesado exitosamente.', 'success', 1200);
                    setTimeout(() => {
                        // Limpiar pantalla y mostrar modal de mesas
                        limpiarComanda();
                        document.getElementById('mesa-seleccionada').textContent = 'Ninguna';
                        const modalPago = bootstrap.Modal.getInstance(document.getElementById('modalPago'));
                        if (modalPago) modalPago.hide();
                        const modalMesas = new bootstrap.Modal(document.getElementById('modalMesas'));
                        modalMesas.show();
                    }, 1200);
                } else {
                    mostrarAlerta(resp.error || 'Error al procesar el pago.', 'danger');
                }
            })
            .catch(() => {
                mostrarAlerta('Error de conexión al procesar el pago.', 'danger');
            });
        });
}

// Validación de cliente obligatorio
function clienteObligatorio() {
    const clienteId = document.getElementById('cliente-id').value;
    if (!clienteId) {
        mostrarAlerta('Debe seleccionar un cliente antes de continuar.', 'danger');
        return false;
    }
    return true;
}

// Imprimir comanda
function imprimirComanda() {
    if (!clienteObligatorio()) return;
    // Implementa la lógica para imprimir la comanda
    console.log('Imprimir comanda');
}

// Función para mostrar el cierre del día
function mostrarCierreDia() {
    const fecha = document.getElementById('fecha-cierre-dia').value || new Date().toISOString().split('T')[0];
    
    fetch(`/api/facturas/reporte-dia?fecha=${fecha}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            mostrarModalCierreDia(data.facturas, data.fecha);
        } else {
            mostrarAlerta(data.error || 'Error al obtener reporte', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        mostrarAlerta('Error al obtener reporte', 'danger');
    });
}

// Función para mostrar el modal de cierre diario
function mostrarModalCierreDia(facturas, fecha) {
    console.log('Mostrando modal de cierre diario con Bootstrap...');
    
    // Calcular resumen por medio de pago
    const resumenMedios = {};
    facturas.forEach(f => {
        if (f.pagos && f.pagos.length > 0) {
            f.pagos.forEach(p => {
                const medio = p.medio_pago_nombre || 'Otro';
                const monto = p.monto;
                if (resumenMedios[medio]) {
                    resumenMedios[medio] += monto;
                } else {
                    resumenMedios[medio] = monto;
                }
            });
        } else {
            // Si no hay pagos detallados, usar el método de pago general
            const medio = f.metodo_pago;
            const monto = f.total;
            if (resumenMedios[medio]) {
                resumenMedios[medio] += monto;
            } else {
                resumenMedios[medio] = monto;
            }
        }
    });

    // Generar HTML del resumen por medio de pago
    let resumenHTML = '';
    if (Object.keys(resumenMedios).length > 0) {
        resumenHTML = `
            <div class="row mb-3">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header bg-info text-white">
                            <h6 class="mb-0"><i class="fa fa-chart-pie me-2"></i>Resumen por Medio de Pago</h6>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                ${Object.entries(resumenMedios)
                                    .sort(([,a], [,b]) => b - a)
                                    .map(([medio, total]) => `
                                        <div class="col-md-3 col-sm-6 mb-2">
                                            <div class="d-flex justify-content-between align-items-center p-2 border rounded">
                                                <span class="fw-bold">${medio}</span>
                                                <span class="text-success fw-bold">$${total.toFixed(2)}</span>
                                            </div>
                                        </div>
                                    `).join('')}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    let html = `
        <div class="text-center mb-3">
            <h4 class="text-primary">Cierre Diario de Pagos</h4>
            <h6 class="text-muted">${fecha}</h6>
        </div>
        
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="card bg-light">
                    <div class="card-body text-center">
                        <h5 class="card-title text-success">Total Facturas</h5>
                        <h3 class="text-success">${facturas.length}</h3>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card bg-light">
                    <div class="card-body text-center">
                        <h5 class="card-title text-primary">Total General</h5>
                        <h3 class="text-primary">$${facturas.reduce((sum, f) => sum + f.total, 0).toFixed(2)}</h3>
                    </div>
                </div>
            </div>
        </div>
        
        ${resumenHTML}
        
        <div class="table-responsive">
        <table class="table table-bordered table-sm table-hover">
            <thead class="table-dark">
                <tr>
                    <th>N° Factura</th>
                    <th>Cliente</th>
                    <th>Fecha</th>
                    <th>Total</th>
                    <th>Medios de Pago</th>
                    <th>Estatus</th>
                </tr>
            </thead>
            <tbody>`;
    
    let total = 0;
    facturas.forEach(f => {
        // Formatear información del cliente
        let clienteInfo = f.cliente_nombre || 'Cliente General';
        if (f.cliente_cedula) {
            clienteInfo += `<br><small class="text-muted">${f.cliente_cedula}</small>`;
        }
        
        // Formatear medios de pago con detalles
        let pagosInfo = '';
        if (f.pagos && f.pagos.length > 0) {
            pagosInfo = f.pagos.map(p => {
                let detalle = `<strong>${p.medio_pago_nombre || 'Otro'}:</strong> $${p.monto.toFixed(2)}`;
                if (p.referencia) detalle += `<br><small class="text-info">Ref: ${p.referencia}</small>`;
                if (p.banco) detalle += `<br><small class="text-secondary">Banco: ${p.banco}</small>`;
                if (p.observaciones) detalle += `<br><small class="text-warning">${p.observaciones}</small>`;
                return detalle;
            }).join('<hr class="my-1">');
        } else {
            pagosInfo = `<strong>${f.metodo_pago}</strong>`;
        }
        
        // Determinar el color del estatus
        let estatusClass = 'bg-secondary';
        if (f.estatus === 'emitida') estatusClass = 'bg-success';
        else if (f.estatus === 'anulada') estatusClass = 'bg-danger';
        else if (f.estatus === 'pagada') estatusClass = 'bg-primary';
        
        html += `<tr>
            <td><span class="badge bg-dark">#${f.numero_factura}</span></td>
            <td>${clienteInfo}</td>
            <td><small>${f.fecha_emision}</small></td>
            <td><strong class="text-success">$${f.total.toFixed(2)}</strong></td>
            <td><small>${pagosInfo}</small></td>
            <td><span class="badge ${estatusClass}">${f.estatus.toUpperCase()}</span></td>
        </tr>`;
        total += f.total;
    });
    
    html += `</tbody>
        <tfoot class="table-dark">
            <tr>
                <td colspan="3" class="text-end"><strong>TOTAL GENERAL</strong></td>
                <td><strong class="text-warning">$${total.toFixed(2)}</strong></td>
                <td colspan="2"></td>
            </tr>
        </tfoot>
        </table>
        </div>
        
        <div class="d-flex justify-content-between align-items-center mt-3">
            <div class="text-muted">
                <small>Reporte generado el ${new Date().toLocaleString()}</small>
            </div>
            <div>
                <a href="/api/facturas/reporte-dia?fecha=${fecha}&pdf=1" target="_blank" class="btn btn-success btn-sm">
                    <i class="fa fa-file-pdf"></i> Descargar PDF
                </a>
                <a href="/api/facturas/resumen-medios-pago?fecha=${fecha}&pdf=1" target="_blank" class="btn btn-info btn-sm ms-2">
                    <i class="fa fa-chart-pie"></i> Resumen Medios
                </a>
                <button onclick="mostrarReporteMediosPagoCompleto('${fecha}')" class="btn btn-primary btn-sm ms-2">
                    <i class="fa fa-list-alt"></i> Reporte Completo
                </button>
                <button onclick="window.print()" class="btn btn-warning btn-sm ms-2">
                    <i class="fa fa-print"></i> Imprimir
                </button>
            </div>
        </div>
    `;
    
    // Crear modal de Bootstrap simple
    crearModalBootstrapSimple(html, fecha);
}

// Función para crear un modal de Bootstrap simple y confiable
function crearModalBootstrapSimple(html, fecha) {
    console.log('Creando modal Bootstrap simple...');
    
    // Remover modal anterior si existe
    const modalAnterior = document.getElementById('modalCierreDiaSimple');
    if (modalAnterior && modalAnterior.parentNode) {
        modalAnterior.parentNode.removeChild(modalAnterior);
    }
    
    // Crear el modal
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'modalCierreDiaSimple';
    modal.setAttribute('tabindex', '-1');
    modal.setAttribute('aria-labelledby', 'modalCierreDiaLabel');
    modal.setAttribute('aria-hidden', 'true');
    
    modal.innerHTML = `
        <div class="modal-dialog modal-xl modal-dialog-scrollable">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="modalCierreDiaLabel">
                        <i class="fa fa-file-invoice me-2"></i>Cierre Diario de Pagos - ${fecha}
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    ${html}
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                        <i class="fa fa-times me-1"></i>Cerrar
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // Agregar al body
    document.body.appendChild(modal);
    
    // Mostrar el modal
    const bsModal = new bootstrap.Modal(modal, {
        backdrop: true,
        keyboard: true,
        focus: true
    });
    
    bsModal.show();
    
    // Event listener para cuando se cierre el modal
    modal.addEventListener('hidden.bs.modal', function() {
        console.log('Modal de cierre diario cerrado');
        // Remover el modal del DOM
        if (modal.parentNode) {
            modal.parentNode.removeChild(modal);
        }
    });
    
    console.log('Modal Bootstrap simple creado y mostrado');
}

// Event listener global para manejar la tecla Escape
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        // Cerrar modal de cierre diario si está abierto
        const modalCierreDia = document.getElementById('modalCierreDiaSimple');
        if (modalCierreDia) {
            const bsModal = bootstrap.Modal.getInstance(modalCierreDia);
            if (bsModal) {
                bsModal.hide();
            }
        }
        
        // Cerrar modal de reporte completo si está abierto
        const modalReporteCompleto = document.getElementById('modalReporteCompleto');
        if (modalReporteCompleto) {
            const bsModal = bootstrap.Modal.getInstance(modalReporteCompleto);
            if (bsModal) {
                bsModal.hide();
            }
        }
    }
});

// Event listener para limpiar backdrops cuando se hace clic fuera del modal
document.addEventListener('click', function(event) {
    // Solo manejar clics en backdrops de modales específicos
    if (event.target.classList.contains('modal-backdrop')) {
        const modalCierreDia = document.getElementById('modalCierreDiaSimple');
        if (modalCierreDia) {
            const bsModal = bootstrap.Modal.getInstance(modalCierreDia);
            if (bsModal) {
                bsModal.hide();
            }
        }
        
        const modalReporteCompleto = document.getElementById('modalReporteCompleto');
        if (modalReporteCompleto) {
            const bsModal = bootstrap.Modal.getInstance(modalReporteCompleto);
            if (bsModal) {
                bsModal.hide();
            }
        }
    }
});

// Event listener para manejar problemas de Bootstrap específicamente
document.addEventListener('DOMContentLoaded', function() {
    // Interceptar errores de Bootstrap
    const originalAddEventListener = EventTarget.prototype.addEventListener;
    EventTarget.prototype.addEventListener = function(type, listener, options) {
        if (type === 'click' && listener && listener.toString().includes('clearMenus')) {
            // Wrapper para el listener de clearMenus de Bootstrap
            const wrappedListener = function(event) {
                try {
                    return listener.call(this, event);
                } catch (error) {
                    console.warn('Error en clearMenus de Bootstrap, ignorando:', error);
                    return false;
                }
            };
            return originalAddEventListener.call(this, type, wrappedListener, options);
        }
        return originalAddEventListener.call(this, type, listener, options);
    };
    
    console.log('Event listeners de Bootstrap protegidos');
});

// Función adicional para forzar recarga si es necesario
window.forzarRecarga = function() {
    console.log('🔄 Forzando recarga de la página...');
    location.reload();
};

// Función para corregir pantalla en blanco inmediatamente
window.corregirPantallaBlanca = function() {
    console.log('🔧 Corrigiendo pantalla en blanco...');
    limpiarTodosLosModales();
    
    // Forzar la visualización del contenido
    setTimeout(() => {
        const contenido = document.querySelector('.row, .container, main');
        if (contenido) {
            contenido.style.display = '';
            contenido.style.visibility = 'visible';
        }
        
        // Restaurar scroll
        if (document.body) {
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
        }
        
        console.log('✅ Pantalla corregida');
    }, 100);
};

// Función para mostrar información de debug
window.debugModales = function() {
    console.log('🔍 DEBUG DE MODALES:');
    console.log('- SweetAlert2 visible:', typeof Swal !== 'undefined' && Swal.isVisible());
    console.log('- Modales Bootstrap:', document.querySelectorAll('.modal').length);
    console.log('- Backdrops:', document.querySelectorAll('.modal-backdrop').length);
    console.log('- Body overflow:', document.body ? document.body.style.overflow : 'N/A');
    console.log('- Body classes:', document.body ? document.body.className : 'N/A');
};

// Función para cerrar el modal de cierre diario
function cerrarModalCierreDia() {
    console.log('Cerrando modal de cierre diario...');
    
    // Enfoque simple y directo
    try {
        // 1. Cerrar SweetAlert2
        if (typeof Swal !== 'undefined' && Swal.isVisible()) {
            Swal.close();
        }
        
        // 2. Limpiar manualmente sin usar Bootstrap
        setTimeout(() => {
            // Eliminar elementos de SweetAlert2
            const swalElements = document.querySelectorAll('.swal2-container, .swal2-backdrop-show, .swal2-shown');
            swalElements.forEach(el => {
                if (el && el.parentNode) {
                    el.parentNode.removeChild(el);
                }
            });
            
            // Eliminar backdrops de Bootstrap
            const backdropElements = document.querySelectorAll('.modal-backdrop');
            backdropElements.forEach(el => {
                if (el && el.parentNode) {
                    el.parentNode.removeChild(el);
                }
            });
            
            // Restaurar estilos del body
            if (document.body) {
                document.body.style.overflow = '';
                document.body.style.paddingRight = '';
                document.body.classList.remove('swal2-shown', 'swal2-height-auto', 'modal-open');
            }
            
            // Limpiar foco
            if (document.activeElement && document.activeElement.blur) {
                document.activeElement.blur();
            }
            
            console.log('Modal cerrado exitosamente');
        }, 100);
        
    } catch (error) {
        console.error('Error al cerrar modal:', error);
        // Si todo falla, recargar la página
        if (confirm('¿Recargar la página para solucionar el problema?')) {
            location.reload();
        }
    }
}

// Función para limpiar el backdrop de SweetAlert2
function limpiarBackdropSweetAlert() {
    console.log('Limpiando backdrop de SweetAlert2...');
    
    try {
        // Eliminar elementos de SweetAlert2 de forma directa
        const swalElements = document.querySelectorAll('.swal2-container, .swal2-backdrop-show, .swal2-shown');
        swalElements.forEach(el => {
            if (el && el.parentNode) {
                el.parentNode.removeChild(el);
            }
        });
        
        // Restaurar estilos del body
        if (document.body) {
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
            document.body.classList.remove('swal2-shown', 'swal2-height-auto', 'modal-open');
        }
        
        console.log('Backdrop limpiado completamente');
    } catch (error) {
        console.error('Error al limpiar backdrop:', error);
    }
}

// Función específica para limpiar TODOS los modales y resolver la pantalla en blanco
function limpiarTodosLosModales() {
    console.log('🧹 LIMPIANDO TODOS LOS MODALES...');
    
    try {
        // 1. Cerrar SweetAlert2
        if (typeof Swal !== 'undefined' && Swal.isVisible()) {
            Swal.close();
        }
        
        // 2. Cerrar todos los modales de Bootstrap
        const todosLosModales = document.querySelectorAll('.modal');
        todosLosModales.forEach(modal => {
            try {
                // Intentar cerrar con Bootstrap
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) {
                    bsModal.hide();
                }
            } catch (error) {
                console.log('Error al cerrar modal con Bootstrap, removiendo manualmente');
            }
            
            // Remover manualmente si es necesario
            if (modal.parentNode) {
                modal.parentNode.removeChild(modal);
            }
        });
        
        // 3. Eliminar TODOS los backdrops y overlays
        setTimeout(() => {
            // Eliminar elementos de SweetAlert2
            const swalElements = document.querySelectorAll('.swal2-container, .swal2-backdrop-show, .swal2-shown, [class*="swal2"]');
            swalElements.forEach(el => {
                if (el && el.parentNode) {
                    el.parentNode.removeChild(el);
                }
            });
            
            // Eliminar backdrops de Bootstrap
            const backdropElements = document.querySelectorAll('.modal-backdrop');
            backdropElements.forEach(el => {
                if (el && el.parentNode) {
                    el.parentNode.removeChild(el);
                }
            });
            
            // 4. Restaurar completamente el body
            if (document.body) {
                document.body.style.overflow = '';
                document.body.style.paddingRight = '';
                document.body.classList.remove('swal2-shown', 'swal2-height-auto', 'modal-open');
            }
            
            if (document.documentElement) {
                document.documentElement.classList.remove('swal2-shown', 'swal2-height-auto');
            }
            
            // 5. Limpiar foco y restaurar
            if (document.activeElement && document.activeElement.blur) {
                document.activeElement.blur();
            }
            
            // 6. Forzar un reflow completo
            if (document.body) {
                document.body.offsetHeight;
            }
            
            // 7. Restaurar el foco al body
            setTimeout(() => {
                if (document.body && document.body.focus) {
                    document.body.focus();
                }
            }, 50);
            
            console.log('✅ TODOS los modales limpiados exitosamente');
            
        }, 200);
        
    } catch (error) {
        console.error('❌ Error al limpiar modales:', error);
        // Último recurso
        location.reload();
    }
}

// Función de emergencia mejorada
window.limpiarTodoModal = function() {
    console.log('🚨 LIMPIEZA DE EMERGENCIA COMPLETA 🚨');
    limpiarTodosLosModales();
    
    // Ocultar botón de emergencia
    setTimeout(() => {
        const emergencyDiv = document.getElementById('emergency-cleanup');
        if (emergencyDiv) {
            emergencyDiv.style.display = 'none';
        }
    }, 500);
};

// Función para detectar modales atascados
function detectarModalAtascado() {
    // Ya no necesitamos esta función con el nuevo enfoque
    return false;
}

// Función para detectar pantalla en blanco y corregirla
function detectarPantallaEnBlanco() {
    // Ya no necesitamos esta función con el nuevo enfoque
    return false;
}

// Verificar cada 2 segundos si hay un modal atascado (solo si el DOM está listo)
function iniciarDeteccionModales() {
    // Ya no necesitamos esta función con el nuevo enfoque
    console.log('Detección automática deshabilitada - usando modal Bootstrap simple');
}

// Función simple para mostrar botón de emergencia si es necesario
function mostrarEmergenciaSiNecesario() {
    const modalCierreDia = document.getElementById('modalCierreDiaSimple');
    const modalReporteCompleto = document.getElementById('modalReporteCompleto');
    
    if ((modalCierreDia && modalCierreDia.classList.contains('show')) || 
        (modalReporteCompleto && modalReporteCompleto.classList.contains('show'))) {
        const emergencyDiv = document.getElementById('emergency-cleanup');
        if (emergencyDiv) {
            emergencyDiv.style.display = 'block';
        }
    }
}

// Función para cerrar manualmente el modal del reporte completo
function cerrarModalReporteCompleto() {
    console.log('Cerrando modal de reporte completo manualmente...');
    
    const modalReporteCompleto = document.getElementById('modalReporteCompleto');
    if (modalReporteCompleto) {
        const bsModal = bootstrap.Modal.getInstance(modalReporteCompleto);
        if (bsModal) {
            bsModal.hide();
        }
    }
    
    // Limpiar backdrops residuales
    limpiarBackdropsResiduales();
}

// Función simple para recargar la página
window.recargarPagina = function() {
    console.log('🔄 Recargando página...');
    location.reload();
};

// Función para mostrar el reporte completo de medios de pago
function mostrarReporteMediosPagoCompleto(fecha) {
    console.log('Mostrando reporte completo de medios de pago...');
    
    fetch(`/api/facturas/reporte-medios-pago-completo?fecha=${fecha}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            mostrarModalReporteMediosPagoCompleto(data, fecha);
        } else {
            mostrarAlerta(data.error || 'Error al obtener reporte', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        mostrarAlerta('Error al obtener reporte', 'danger');
    });
}

// Función para mostrar el modal de reporte de medios de pago completo
function mostrarModalReporteMediosPagoCompleto(data, fecha) {
    console.log('Mostrando modal de reporte de medios de pago completo...');
    
    // Generar HTML del resumen por medio de pago
    let resumenHTML = '';
    if (Object.keys(data.resumen_medios).length > 0) {
        resumenHTML = `
            <div class="row mb-3">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header bg-info text-white">
                            <h6 class="mb-0"><i class="fa fa-chart-pie me-2"></i>Resumen por Medio de Pago</h6>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                ${Object.entries(data.resumen_medios)
                                    .sort(([,a], [,b]) => b - a)
                                    .map(([medio, total]) => `
                                        <div class="col-md-3 col-sm-6 mb-2">
                                            <div class="d-flex justify-content-between align-items-center p-2 border rounded">
                                                <span class="fw-bold">${medio}</span>
                                                <span class="text-success fw-bold">$${total.toFixed(2)}</span>
                                            </div>
                                        </div>
                                    `).join('')}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    let html = `
        <div class="text-center mb-3">
            <h4 class="text-primary">Reporte Completo de Medios de Pago</h4>
            <h6 class="text-muted">${fecha}</h6>
        </div>
        
        <div class="row mb-3">
            <div class="col-md-4">
                <div class="card bg-light">
                    <div class="card-body text-center">
                        <h5 class="card-title text-success">Total Facturas</h5>
                        <h3 class="text-success">${data.total_facturas}</h3>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card bg-light">
                    <div class="card-body text-center">
                        <h5 class="card-title text-primary">Total Transacciones</h5>
                        <h3 class="text-primary">${data.total_transacciones}</h3>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card bg-light">
                    <div class="card-body text-center">
                        <h5 class="card-title text-warning">Total General</h5>
                        <h3 class="text-warning">$${data.total_general.toFixed(2)}</h3>
                    </div>
                </div>
            </div>
        </div>
        
        ${resumenHTML}
        
        <div class="table-responsive">
        <table class="table table-bordered table-sm table-hover">
            <thead class="table-dark">
                <tr>
                    <th>N° Factura</th>
                    <th>Cliente</th>
                    <th>Cédula/RIF</th>
                    <th>Medio de Pago</th>
                    <th>Monto</th>
                    <th>Referencia</th>
                    <th>Banco</th>
                    <th>Observaciones</th>
                    <th>Fecha</th>
                </tr>
            </thead>
            <tbody>`;
    
    data.detalles_completos.forEach(detalle => {
        // Formatear información del cliente
        let clienteInfo = detalle.cliente_nombre;
        if (detalle.cliente_cedula) {
            clienteInfo += `<br><small class="text-muted">${detalle.cliente_cedula}</small>`;
        }
        
        // Formatear referencia
        let referenciaInfo = detalle.referencia || '-';
        if (detalle.referencia) {
            referenciaInfo = `<span class="badge bg-info">${detalle.referencia}</span>`;
        }
        
        // Formatear banco
        let bancoInfo = detalle.banco || '-';
        if (detalle.banco) {
            bancoInfo = `<span class="badge bg-secondary">${detalle.banco}</span>`;
        }
        
        // Formatear observaciones
        let obsInfo = detalle.observaciones || '-';
        if (detalle.observaciones) {
            obsInfo = `<small class="text-warning">${detalle.observaciones}</small>`;
        }
        
        // Determinar el color del medio de pago
        let medioPagoClass = 'bg-primary';
        if (detalle.medio_pago.toLowerCase().includes('efectivo')) medioPagoClass = 'bg-success';
        else if (detalle.medio_pago.toLowerCase().includes('tarjeta')) medioPagoClass = 'bg-info';
        else if (detalle.medio_pago.toLowerCase().includes('transferencia')) medioPagoClass = 'bg-warning';
        else if (detalle.medio_pago.toLowerCase().includes('pago móvil')) medioPagoClass = 'bg-danger';
        
        html += `<tr>
            <td><span class="badge bg-dark">#${detalle.numero_factura}</span></td>
            <td>${clienteInfo}</td>
            <td>${detalle.cliente_cedula || '-'}</td>
            <td><span class="badge ${medioPagoClass}">${detalle.medio_pago}</span></td>
            <td><strong class="text-success">$${detalle.monto.toFixed(2)}</strong></td>
            <td>${referenciaInfo}</td>
            <td>${bancoInfo}</td>
            <td>${obsInfo}</td>
            <td><small>${detalle.fecha_emision}</small></td>
        </tr>`;
    });
    
    html += `</tbody>
        <tfoot class="table-dark">
            <tr>
                <td colspan="3" class="text-end"><strong>TOTAL GENERAL</strong></td>
                <td><strong class="text-warning">$${data.total_general.toFixed(2)}</strong></td>
                <td colspan="4"></td>
            </tr>
        </tfoot>
        </table>
        </div>
        
        <div class="d-flex justify-content-between align-items-center mt-3">
            <div class="text-muted">
                <small>Reporte generado el ${new Date().toLocaleString()}</small>
            </div>
            <div>
                <a href="/api/facturas/reporte-medios-pago-completo?fecha=${fecha}&pdf=1" target="_blank" class="btn btn-danger btn-sm">
                    <i class="fa fa-file-pdf"></i> Descargar PDF
                </a>
                <button onclick="exportarReporteMediosPagoCompleto('${fecha}')" class="btn btn-success btn-sm ms-2">
                    <i class="fa fa-file-excel"></i> Exportar Excel
                </button>
                <button onclick="window.print()" class="btn btn-warning btn-sm ms-2">
                    <i class="fa fa-print"></i> Imprimir
                </button>
            </div>
        </div>
    `;
    
    // Crear modal específico para reporte completo
    crearModalReporteCompleto(html, fecha);
}

// Función para crear modal específico del reporte completo
function crearModalReporteCompleto(html, fecha) {
    console.log('Creando modal específico para reporte completo...');
    
    // Remover modal anterior si existe
    const modalAnterior = document.getElementById('modalReporteCompleto');
    if (modalAnterior && modalAnterior.parentNode) {
        modalAnterior.parentNode.removeChild(modalAnterior);
    }
    
    // Crear el modal
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'modalReporteCompleto';
    modal.setAttribute('tabindex', '-1');
    modal.setAttribute('aria-labelledby', 'modalReporteCompletoLabel');
    modal.setAttribute('aria-hidden', 'true');
    
    modal.innerHTML = `
        <div class="modal-dialog modal-xl modal-dialog-scrollable">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="modalReporteCompletoLabel">
                        <i class="fa fa-list-alt me-2"></i>Reporte Completo de Medios de Pago - ${fecha}
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    ${html}
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                        <i class="fa fa-times me-1"></i>Cerrar
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // Agregar al body
    document.body.appendChild(modal);
    
    // Mostrar el modal
    const bsModal = new bootstrap.Modal(modal, {
        backdrop: true,
        keyboard: true,
        focus: true
    });
    
    bsModal.show();
    
    // Event listener para cuando se cierre el modal
    modal.addEventListener('hidden.bs.modal', function() {
        console.log('Modal de reporte completo cerrado');
        // Remover el modal del DOM
        if (modal.parentNode) {
            modal.parentNode.removeChild(modal);
        }
        // Limpiar cualquier backdrop residual
        limpiarBackdropsResiduales();
    });
    
    console.log('Modal de reporte completo creado y mostrado');
}

// Función para limpiar backdrops residuales
function limpiarBackdropsResiduales() {
    console.log('Limpiando backdrops residuales...');
    
    // Eliminar backdrops de Bootstrap
    const backdropElements = document.querySelectorAll('.modal-backdrop');
    backdropElements.forEach(el => {
        if (el && el.parentNode) {
            el.parentNode.removeChild(el);
        }
    });
    
    // Restaurar estilos del body
    if (document.body) {
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
        document.body.classList.remove('modal-open');
    }
    
    console.log('Backdrops residuales limpiados');
}

// Función para exportar el reporte a Excel
function exportarReporteMediosPagoCompleto(fecha) {
    console.log('Exportando reporte completo de medios de pago...');
    
    fetch(`/api/facturas/reporte-medios-pago-completo?fecha=${fecha}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Crear contenido CSV
            let csvContent = "data:text/csv;charset=utf-8,";
            csvContent += "N° Factura,Cliente,Cédula/RIF,Medio de Pago,Monto,Referencia,Banco,Observaciones,Fecha\n";
            
            data.detalles_completos.forEach(detalle => {
                const row = [
                    detalle.numero_factura,
                    detalle.cliente_nombre,
                    detalle.cliente_cedula || '',
                    detalle.medio_pago,
                    detalle.monto.toFixed(2),
                    detalle.referencia || '',
                    detalle.banco || '',
                    detalle.observaciones || '',
                    detalle.fecha_emision
                ].map(field => `"${field}"`).join(',');
                csvContent += row + '\n';
            });
            
            // Agregar total
            csvContent += `"TOTAL","","","","${data.total_general.toFixed(2)}","","","",""\n`;
            
            // Descargar archivo
            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", `reporte_medios_pago_${fecha}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            mostrarAlerta('Reporte exportado correctamente', 'success');
        } else {
            mostrarAlerta(data.error || 'Error al exportar reporte', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        mostrarAlerta('Error al exportar reporte', 'danger');
    });
} 