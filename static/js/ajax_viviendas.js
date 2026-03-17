// static/js/ajax_viviendas.js
// Script para cargar viviendas dinámicamente cuando se selecciona un edificio

document.addEventListener('DOMContentLoaded', function() {
    console.log('Script ajax_viviendas.js cargado');
    
    // ✅ FUNCIÓN PRINCIPAL: Cargar viviendas por edificio
    function setupViviendaLoader() {
        const edificioSelect = document.getElementById('id_edificio');
        const viviendaSelect = document.getElementById('id_vivienda');
        
        if (edificioSelect && viviendaSelect) {
            console.log('Elementos encontrados, configurando listeners');
            
            edificioSelect.addEventListener('change', function() {
                const edificioId = this.value;
                console.log('Edificio seleccionado:', edificioId);
                
                // Limpiar opciones de vivienda
                viviendaSelect.innerHTML = '<option value="">---------</option>';
                
                if (edificioId) {
                    // Mostrar indicador de carga
                    viviendaSelect.innerHTML = '<option value="">Cargando...</option>';
                    viviendaSelect.disabled = true;
                    
                    // Hacer petición AJAX
                    fetch(`/usuarios/ajax/cargar-viviendas/?edificio_id=${edificioId}`)
                        .then(response => {
                            if (!response.ok) {
                                throw new Error(`HTTP error! status: ${response.status}`);
                            }
                            return response.json();
                        })
                        .then(data => {
                            console.log('Viviendas recibidas:', data);
                            
                            viviendaSelect.innerHTML = '<option value="">---------</option>';
                            
                            if (Array.isArray(data) && data.length > 0) {
                                data.forEach(vivienda => {
                                    const option = document.createElement('option');
                                    option.value = vivienda.id;
                                    option.textContent = vivienda.nombre;
                                    viviendaSelect.appendChild(option);
                                });
                            } else {
                                const option = document.createElement('option');
                                option.value = '';
                                option.textContent = 'No hay viviendas disponibles';
                                viviendaSelect.appendChild(option);
                            }
                            
                            viviendaSelect.disabled = false;
                        })
                        .catch(error => {
                            console.error('Error al cargar viviendas:', error);
                            viviendaSelect.innerHTML = '<option value="">Error al cargar viviendas</option>';
                            viviendaSelect.disabled = false;
                            
                            // Mostrar mensaje de error al usuario
                            showErrorMessage('Error al cargar las viviendas. Por favor, recarga la página.');
                        });
                } else {
                    viviendaSelect.disabled = false;
                }
            });
            
            // ✅ MANTENER SELECCIÓN SI YA HAY DATOS
            // Útil cuando hay errores de validación y se regresa al formulario
            const initialEdificio = edificioSelect.value;
            if (initialEdificio) {
                console.log('Edificio pre-seleccionado encontrado:', initialEdificio);
                // Trigger change event to load viviendas
                edificioSelect.dispatchEvent(new Event('change'));
            }
        } else {
            console.log('Elementos no encontrados:', {
                edificio: !!edificioSelect,
                vivienda: !!viviendaSelect
            });
        }
    }
    
    // ✅ FUNCIÓN: Manejar formularios de residente
    function setupResidenteForm() {
        const form = document.querySelector('form');
        if (form) {
            // Hacer que el campo password no sea requerido en edición
            const usernameField = document.querySelector('input[name="username"]');
            if (usernameField && usernameField.value !== '') {
                console.log('Modo edición detectado, haciendo contraseñas opcionales');
                
                const password1 = document.getElementById('id_password1');
                const password2 = document.getElementById('id_password2');
                
                if (password1) {
                    password1.required = false;
                    password1.placeholder = 'Déjalo vacío para mantener la contraseña actual';
                }
                if (password2) {
                    password2.required = false;
                    password2.placeholder = 'Déjalo vacío para mantener la contraseña actual';
                }
                
                // Agregar texto de ayuda
                const helpText = document.createElement('small');
                helpText.className = 'form-text text-muted';
                helpText.textContent = 'Deja estos campos vacíos si no deseas cambiar la contraseña';
                
                if (password1 && !password1.parentNode.querySelector('.form-text')) {
                    password1.parentNode.appendChild(helpText);
                }
            }
            
            // ✅ VALIDACIÓN DE CONTRASEÑAS EN TIEMPO REAL
            const password1 = document.getElementById('id_password1');
            const password2 = document.getElementById('id_password2');
            
            if (password1 && password2) {
                function validatePasswords() {
                    const pass1 = password1.value;
                    const pass2 = password2.value;
                    
                    // Solo validar si ambas tienen contenido
                    if (pass1 || pass2) {
                        if (pass1 !== pass2) {
                            password2.setCustomValidity('Las contraseñas no coinciden');
                            password2.classList.add('is-invalid');
                        } else {
                            password2.setCustomValidity('');
                            password2.classList.remove('is-invalid');
                        }
                    } else {
                        password2.setCustomValidity('');
                        password2.classList.remove('is-invalid');
                    }
                }
                
                password1.addEventListener('input', validatePasswords);
                password2.addEventListener('input', validatePasswords);
            }
        }
    }
    
    // ✅ FUNCIÓN: Mostrar mensajes de error
    function showErrorMessage(message) {
        // Buscar contenedor de mensajes existente
        let messageContainer = document.querySelector('.alert-container');
        
        if (!messageContainer) {
            // Crear contenedor de mensajes si no existe
            messageContainer = document.createElement('div');
            messageContainer.className = 'alert-container';
            document.body.insertBefore(messageContainer, document.body.firstChild);
        }
        
        // Crear el mensaje de error
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show';
        alert.role = 'alert';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        messageContainer.appendChild(alert);
        
        // Auto-remover después de 5 segundos
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    }
    
    // ✅ FUNCIÓN: Filtros financieros dinámicos
    function setupFinancialFilters() {
        const edificioFilter = document.querySelector('select[name="edificio"]');
        const viviendaFilter = document.querySelector('select[name="vivienda"]');
        
        if (edificioFilter && viviendaFilter) {
            edificioFilter.addEventListener('change', function() {
                const edificioId = this.value;
                
                if (edificioId) {
                    // Cargar viviendas del edificio seleccionado
                    fetch(`/viviendas/api/edificio/${edificioId}/viviendas/`)
                        .then(response => response.json())
                        .then(viviendas => {
                            viviendaFilter.innerHTML = '<option value="">Todas las viviendas</option>';
                            
                            viviendas.forEach(vivienda => {
                                const option = document.createElement('option');
                                option.value = vivienda.id;
                                option.textContent = `${vivienda.numero} - Piso ${vivienda.piso}`;
                                viviendaFilter.appendChild(option);
                            });
                        })
                        .catch(error => {
                            console.error('Error al cargar viviendas:', error);
                        });
                } else {
                    viviendaFilter.innerHTML = '<option value="">Todas las viviendas</option>';
                }
            });
        }
    }
    
    // ✅ EJECUTAR TODAS LAS CONFIGURACIONES
    setupViviendaLoader();
    setupResidenteForm();
    setupFinancialFilters();
    
    console.log('Todas las configuraciones de AJAX completadas');
});

// ✅ FUNCIÓN GLOBAL: Para uso en templates si es necesario
window.reloadViviendas = function(edificioId, targetSelectId = 'id_vivienda') {
    const viviendaSelect = document.getElementById(targetSelectId);
    if (!viviendaSelect) return;
    
    viviendaSelect.innerHTML = '<option value="">Cargando...</option>';
    
    fetch(`/usuarios/ajax/cargar-viviendas/?edificio_id=${edificioId}`)
        .then(response => response.json())
        .then(data => {
            viviendaSelect.innerHTML = '<option value="">---------</option>';
            data.forEach(vivienda => {
                const option = document.createElement('option');
                option.value = vivienda.id;
                option.textContent = vivienda.nombre;
                viviendaSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error:', error);
            viviendaSelect.innerHTML = '<option value="">Error al cargar</option>';
        });
};