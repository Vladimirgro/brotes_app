        document.addEventListener('DOMContentLoaded', function () {
            const sidebar = document.getElementById('sidebar');
            const sidebarToggle = document.getElementById('sidebarToggle'); // Botón principal (desktop)
            const mobileMenuToggle = document.getElementById('mobileMenuToggle'); // Botón barras (mobile)


            // Toggle sidebar en desktop
            sidebarToggle.addEventListener('click', function () {
                sidebar.classList.toggle('expand');
                localStorage.setItem('sidebarExpanded', sidebar.classList.contains('expand'));
            });

            // Toggle sidebar en móvil
            mobileMenuToggle.addEventListener('click', function () {
                sidebar.classList.toggle('expand');
            });

            // Cargar estado del sidebar desde localStorage
            if (localStorage.getItem('sidebarExpanded') === 'true') {
                sidebar.classList.add('expand');
            }

            // Cerrar sidebar al hacer clic en el contenido en móvil
            document.querySelector('.content').addEventListener('click', function () {
                if (window.innerWidth <= 992 && sidebar.classList.contains('expand')) {
                    sidebar.classList.remove('expand');
                }
            });

            // Manejar cambios de tamaño de pantalla
            window.addEventListener('resize', function () {
                if (window.innerWidth > 992) {
                    sidebar.classList.remove('expand');
                }
            });
        });