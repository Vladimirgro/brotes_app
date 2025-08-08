from flask import Blueprint, request, redirect, render_template, session, url_for, flash
from app.models import user_model
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash

from app.models.user_model import UserModel
from app.utils.security import encriptar_password


from app.middleware.auth_middleware import rol_requerido

auth_bp = Blueprint('auth_bp', __name__, url_prefix='/auth')


#End point para iniciar sesion
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('brotes_bp.formulario'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Buscar usuario por correo
        user = user_model.UserModel.find_by_email(email)                                    
        
        # Validación de usuario y contraseña        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Inicio de sesión exitoso.', 'login_success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('brotes_bp.formulario'))
        else:
            flash('Correo o contraseña incorrectos.', 'danger')
            return redirect(url_for('auth_bp.login'))

    return render_template('auth/login.html')


#End point para cerrar sesion
@auth_bp.route('/logout')
@login_required
def logout():
    session.pop('_flashes', None)
    logout_user()
    flash('Sesión cerrada correctamente.', 'logout_info')    
    return redirect(url_for('auth_bp.login'))


#Endpoint para registrar usuarios 
@auth_bp.route('/registro', methods=['GET', 'POST'])
@login_required
@rol_requerido('super_administrador')
def registrar_usuario():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        rol = request.form.get('rol', '')

        if not all([nombre, email, password, rol]):
            flash('Todos los campos son obligatorios', 'warning')
            return redirect(url_for('auth_bp.registrar_usuario'))

        try:
            user_model.UserModel.create_user(nombre, email, password, rol)
            flash('Usuario registrado exitosamente', 'success')
            return redirect(url_for('auth_bp.registrar_usuario'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('auth_bp.registrar_usuario'))

    return render_template('auth/registro.html')



#Endpoint para listar usuarios registrados con vista protegida
@auth_bp.route('/usuarios', methods=['GET'])
@login_required
@rol_requerido('super_administrador')
def lista_usuarios():
    usuarios = user_model.UserModel.obtener_todos()
    return render_template('auth/lista_usuarios.html', usuarios=usuarios)


#End point para editar usuarios registrados
@auth_bp.route('/editar/<int:id_usuario>', methods=['GET', 'POST'])
@login_required
@rol_requerido('super_administrador')
def editar_usuario(id_usuario):
    usuario = user_model.UserModel.obtener_por_id(id_usuario)
    if not usuario:
        flash("Usuario no encontrado", "danger")
        return redirect(url_for('auth_bp.lista_usuarios'))

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip().lower()
        rol = request.form.get('rol', '')
        if not all([nombre, email, rol]):
            flash("Todos los campos son obligatorios", "warning")
        else:
            user_model.UserModel.actualizar_usuario(id_usuario, nombre, email, rol)
            flash("Usuario actualizado correctamente", "success")
            return redirect(url_for('auth_bp.lista_usuarios'))

    return render_template('auth/editar_usuario.html', usuario=usuario)



#Endpoint para cambiar estado activo
@auth_bp.route('/estado/<int:id_usuario>/<int:estado>', methods=['POST'])
@login_required
@rol_requerido('super_administrador')
def cambiar_estado_usuario(id_usuario, estado):
    user_model.UserModel.cambiar_estado(id_usuario, estado)
    flash("Estado del usuario actualizado", "success")
    return redirect(url_for('auth_bp.lista_usuarios'))



#Endpoint para crear super usuario   EN PRODUCCION ELIMINAR ESTO
@auth_bp.route('/crear_superadmin', methods=['GET', 'POST'])
def crear_superadmin():
    if UserModel.total_usuarios() > 0:
        flash('Ya existe al menos un usuario. Acceso denegado.', 'danger')
        return redirect(url_for('auth_bp.login'))

    if request.method == 'POST':
        try:
            nombre = request.form.get('nombre')
            email = request.form.get('email')
            password = encriptar_password(request.form.get('password'))

            datos = {
                'nombre': nombre,
                'email': email,
                'password': password,
                'rol': 'super_administrador',
                'activo': 1
            }

            resultado = UserModel.crear_usuario(datos)
            if resultado:
                flash('Superusuario creado con éxito.', 'success')
            else:
                flash('Ocurrió un error al guardar el usuario.', 'danger')

        except Exception as e:
            flash(f'Error inesperado: {str(e)}', 'danger')

        return redirect(url_for('auth_bp.login'))

    return render_template('auth/crear_superadmin.html')