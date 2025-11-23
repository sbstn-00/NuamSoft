// Espera a que el contenido de la página cargue
document.addEventListener('DOMContentLoaded', function() {

    const form = document.getElementById('loginForm'); // Apunta al ID del formulario
    const alertBox = document.getElementById('alert');

    // Función para mostrar alertas
    function showAlert(message, type) {
        alertBox.textContent = message;
        alertBox.className = `alert alert-${type} show`;
        
        // Ocultar la alerta después de 5 segundos
        setTimeout(() => {
            alertBox.classList.remove('show');
        }, 5000);
    }

    // Función para calcular la edad
    function calculateAge(birthDate) {
        const today = new Date();
        const birth = new Date(birthDate);
        let age = today.getFullYear() - birth.getFullYear();
        const monthDiff = today.getMonth() - birth.getMonth();
        if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
            age--;
        }
        return age;
    }

    // Escuchar el envío del formulario
    form.addEventListener('submit', function(e) {
        e.preventDefault(); // Prevenir el envío real
        
        const nombre = document.getElementById('nombre').value;
        const email = document.getElementById('email').value;
        const pais = document.querySelector('input[name="pais"]:checked');
        const identificador = document.getElementById('identificador').value;
        const fechaNacimiento = document.getElementById('fecha_nacimiento').value;
        
        // Validar que se haya seleccionado un país
        if (!pais) {
            showAlert('Por favor seleccione su país', 'error');
            return;
        }
        
        // Validar edad
        const edad = calculateAge(fechaNacimiento);
        if (edad < 18) {
            showAlert('Debe ser mayor de 18 años para acceder', 'error');
            return;
        }
        
        // ¡Éxito!
        showAlert(`¡Bienvenido ${nombre}! Datos recibidos correctamente`, 'success');
        
        console.log({
            nombre,
            email,
            pais: pais.value,
            identificador,
            fechaNacimiento,
            edad
        });

        // Aquí podrías redirigir o limpiar el formulario
        // form.reset();
    });

});