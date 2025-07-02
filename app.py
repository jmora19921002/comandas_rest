from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_file
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
from decimal import Decimal
from functools import wraps
from datetime import timedelta, datetime
import tempfile
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
import subprocess
import platform
import uuid
from config import config

def create_app(config_name=None):
    """Factory function para crear la aplicación Flask"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'production')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    return app

app = create_app()

# Configuración de sesión
app.permanent_session_lifetime = timedelta(hours=1)

# Asegurar que SECRET_KEY esté configurada para las sesiones
if not app.config.get('SECRET_KEY'):
    app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui_123456'
    print("🔑 SECRET_KEY configurada para sesiones")

print(f"🔧 Configuración de la aplicación:")
print(f"   - SECRET_KEY: {'Configurada' if app.config.get('SECRET_KEY') else 'No configurada'}")
print(f"   - Session lifetime: {app.permanent_session_lifetime}")

def get_db_connection():
    """Establece conexión con la base de datos MySQL local"""
    try:
        conn_params = {
            'host': app.config['MYSQL_HOST'],
            'port': app.config['MYSQL_PORT'],
            'user': app.config['MYSQL_USER'],
            'password': app.config['MYSQL_PASSWORD'],
            'database': app.config['MYSQL_DB'],
        }
        
        # Para MySQL local, no usar SSL
        if app.config['MYSQL_SSL_CA']:
            # Si hay configuración SSL (para producción), usarla
            if os.path.exists(app.config['MYSQL_SSL_CA']):
                conn_params.update({
                    'ssl_disabled': False,
                    'ssl_ca': app.config['MYSQL_SSL_CA']
                })
            else:
                # Para Render, usar SSL sin verificación de certificado
                conn_params.update({
                    'ssl_disabled': False,
                    'ssl_verify_cert': False
                })
        else:
            # Para MySQL local, deshabilitar SSL completamente
            conn_params.update({
                'ssl_disabled': True
            })
        
        conn = mysql.connector.connect(**conn_params)
        return conn
    except Error as e:
        print(f'Error al conectar a la base de datos: {str(e)}')
        flash(f'Error al conectar a la base de datos: {str(e)}', 'danger')
        return None

def login_required(f):
    """Decorador para verificar sesión activa"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(f"🔍 Login required check - Session: {dict(session)}")  # Debug
        if 'usuario' not in session:
            print("❌ No hay usuario en sesión")  # Debug
            flash('Debes iniciar sesión para acceder a esta página', 'warning')
            return redirect(url_for('login'))
        print("✅ Usuario encontrado en sesión")  # Debug
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorador para verificar rol de administrador"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'rol' not in session or session['rol'] != 'admin':
            flash('Acceso restringido: se requieren privilegios de administrador', 'danger')
            return redirect(url_for('mesas'))
        return f(*args, **kwargs)
    return decorated_function

def soporte_required(f):
    """Decorador para verificar rol de soporte"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'rol' not in session or session['rol'] != 'soporte':
            flash('Acceso restringido: se requieren privilegios de soporte', 'danger')
            return redirect(url_for('mesas'))
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    """Decorador para verificar rol de super administrador"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(f"🔍 Super admin required check - Session: {dict(session)}")  # Debug
        if 'tipo_usuario' not in session or session['tipo_usuario'] != 'super_admin':
            print(f"❌ No es super admin - tipo_usuario: {session.get('tipo_usuario', 'No definido')}")  # Debug
            flash('Acceso restringido: se requieren privilegios de super administrador', 'danger')
            return redirect(url_for('login'))
        print("✅ Super admin verificado")  # Debug
        return f(*args, **kwargs)
    return decorated_function

def generate_empresa_code():
    """Genera un código único para la empresa"""
    return f"EMP{str(uuid.uuid4())[:8].upper()}"

@app.route('/')
@app.route('/index')
def index():
    """Redirige al usuario según su estado de autenticación"""
    if 'usuario' in session:
        if session.get('tipo_usuario') == 'super_admin':
            return redirect(url_for('super_admin_dashboard'))
        elif session.get('rol') == 'admin':
            return redirect(url_for('manager'))
        return redirect(url_for('mesas'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Obtener datos de la empresa (para mostrar logo en login público)
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM empresa WHERE estatus = 'activo' LIMIT 1")
            empresa = cursor.fetchone()
            cursor.close()
            conn.close()
        else:
            empresa = None
    except Exception as e:
        print(f"Error al obtener datos de la empresa: {str(e)}")
        empresa = None

    if request.method == 'POST':
        user = request.form.get('user')
        password = request.form.get('password')
        
        print(f"Intento de login - Usuario: {user}")  # Debug log
        
        if not user or not password:
            flash('Por favor ingrese usuario y contraseña', 'warning')
            return render_template('login.html', empresa=empresa)
        
        try:
            print(f"Intentando conectar a la base de datos...")  # Debug log
            conn = get_db_connection()
            if not conn:
                print("No se pudo establecer conexión con la base de datos")  # Debug log
                flash('Error de conexión a la base de datos', 'danger')
                return render_template('login.html', empresa=empresa)
            
            # Primero verificar si es un super administrador
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM super_admin WHERE user = %s', (user,))
            super_admin_data = cursor.fetchone()
            
            if super_admin_data:
                print(f"Super admin encontrado: {super_admin_data['user']}")  # Debug log
                
                # Verificar la contraseña
                if super_admin_data['password'] == password:
                    print("Contraseña de super admin correcta")  # Debug log
                    session['usuario'] = {
                        'id': super_admin_data['id'],
                        'nombre_completo': super_admin_data['nombre_completo'],
                        'usuario': super_admin_data['user']
                    }
                    session['tipo_usuario'] = 'super_admin'
                    session.permanent = True
                    
                    # Debug: verificar que la sesión se guardó
                    print(f"Session después del login: {dict(session)}")
                    print(f"Session ID: {session.sid if hasattr(session, 'sid') else 'No disponible'}")
                    
                    flash('Bienvenido al panel de super administración', 'success')
                    return redirect(url_for('super_admin_dashboard'))
                else:
                    print("Contraseña de super admin incorrecta")  # Debug log
                    flash('Usuario o contraseña incorrectos', 'danger')
            else:
                # Verificar si es un usuario normal
                print(f"Buscando usuario normal: {user}")  # Debug log
                cursor.execute('SELECT u.*, e.nombre_empresa, e.estatus as empresa_estatus FROM usuario u LEFT JOIN empresa e ON u.empresa_id = e.id WHERE u.user = %s', (user,))
                user_data = cursor.fetchone()
                
                if user_data:
                    print(f"Usuario encontrado: {user_data['user']}")  # Debug log
                    
                    # Verificar si la empresa está activa
                    if user_data['empresa_estatus'] != 'activo':
                        flash('Su empresa no está activa. Contacte al administrador del sistema.', 'warning')
                        return render_template('login.html', empresa=empresa)
                    
                    # Verificar la contraseña directamente (texto plano)
                    if user_data['password'] == password:
                        print("Contraseña correcta")  # Debug log
                        session['usuario'] = {
                            'id': user_data['id'],
                            'nombre_completo': user_data['nombre_completo'],
                            'usuario': user_data['user'],
                            'empresa_id': user_data['empresa_id'],
                            'empresa_nombre': user_data['nombre_empresa']
                        }
                        session['rol'] = user_data['rol']
                        session['empresa_id'] = user_data['empresa_id']
                        session.permanent = True
                        
                        # Redirigir según el rol
                        if user_data['rol'] == 'soporte':
                            flash('Bienvenido al sistema de soporte', 'success')
                            return redirect(url_for('manager'))
                        elif user_data['rol'] == 'admin':
                            flash('Bienvenido al sistema de administración', 'success')
                            return redirect(url_for('manager'))
                        else:
                            flash('Bienvenido al sistema', 'success')
                            return redirect(url_for('mesas'))
                    else:
                        print("Contraseña incorrecta")  # Debug log
                        flash('Usuario o contraseña incorrectos', 'danger')
                else:
                    print("Usuario no encontrado")  # Debug log
                    flash('Usuario o contraseña incorrectos', 'danger')
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"Error en login: {str(e)}")  # Debug log
            flash(f'Error al intentar iniciar sesión: {str(e)}', 'danger')
            return render_template('login.html', empresa=empresa)
            
    return render_template('login.html', empresa=empresa)

@app.route('/registro/empresa')
def registro_empresa():
    """Página de registro de empresa"""
    return render_template('registro_empresa.html')

@app.route('/api/registro/empresa', methods=['POST'])
def api_registro_empresa():
    """API para registrar nueva empresa y usuario administrador"""
    try:
        # Obtener datos del formulario
        nombre_empresa = request.form.get('nombre_empresa')
        email = request.form.get('email')
        telefono = request.form.get('telefono')
        rif = request.form.get('rif')
        direccion = request.form.get('direccion')
        
        # Datos de WhatsApp
        whatsapp_api_key = request.form.get('whatsapp_api_key')
        whatsapp_api_url = request.form.get('whatsapp_api_url')
        whatsapp_phone_number = request.form.get('whatsapp_phone_number')
        
        # Datos del usuario administrador
        admin_nombre = request.form.get('admin_nombre')
        admin_user = request.form.get('admin_user')
        admin_password = request.form.get('admin_password')
        
        # Validaciones básicas
        if not all([nombre_empresa, email, telefono, rif, direccion, admin_nombre, admin_user, admin_password]):
            return jsonify({'success': False, 'message': 'Todos los campos requeridos deben estar completos'}), 400
        
        # Manejo del archivo de logo
        logo = request.files.get('logo')
        logo_data = None
        
        if logo and logo.filename:
            # Validar tipo de archivo
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
            if logo.content_type not in allowed_types:
                return jsonify({'success': False, 'message': 'Solo se permiten archivos de imagen (JPEG, PNG, GIF)'}), 400
            
            # Validar tamaño del archivo (máximo 5MB)
            max_size = 5 * 1024 * 1024  # 5MB
            if logo.content_length and logo.content_length > max_size:
                return jsonify({'success': False, 'message': 'El archivo es demasiado grande. Máximo 5MB'}), 400
            
            try:
                logo_data = logo.read()
            except Exception as e:
                return jsonify({'success': False, 'message': f'Error al procesar el archivo: {str(e)}'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
        
        cursor = conn.cursor()
        
        try:
            # Verificar si el RIF ya existe
            cursor.execute('SELECT id FROM empresa WHERE rif = %s', (rif,))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'El RIF ya está registrado en el sistema'}), 400
            
            # Verificar si el email ya existe
            cursor.execute('SELECT id FROM empresa WHERE email = %s', (email,))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'El email ya está registrado en el sistema'}), 400
            
            # Verificar si el usuario ya existe
            cursor.execute('SELECT id FROM usuario WHERE user = %s', (admin_user,))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'El nombre de usuario ya está en uso'}), 400
            
            # Generar código único para la empresa
            codigo_empresa = generate_empresa_code()
            
            # Insertar empresa
            if logo_data:
                cursor.execute("""
                    INSERT INTO empresa (codigo_empresa, nombre_empresa, email, telefono, rif, direccion, logo,
                                       whatsapp_api_key, whatsapp_api_url, whatsapp_phone_number, estatus)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'en_espera')
                """, (codigo_empresa, nombre_empresa, email, telefono, rif, direccion, logo_data,
                      whatsapp_api_key, whatsapp_api_url, whatsapp_phone_number))
            else:
                cursor.execute("""
                    INSERT INTO empresa (codigo_empresa, nombre_empresa, email, telefono, rif, direccion,
                                       whatsapp_api_key, whatsapp_api_url, whatsapp_phone_number, estatus)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'en_espera')
                """, (codigo_empresa, nombre_empresa, email, telefono, rif, direccion,
                      whatsapp_api_key, whatsapp_api_url, whatsapp_phone_number))
            
            empresa_id = cursor.lastrowid
            
            # Insertar usuario administrador
            cursor.execute("""
                INSERT INTO usuario (empresa_id, user, password, nombre_completo, rol, estatus)
                VALUES (%s, %s, %s, %s, 'admin', 'activo')
            """, (empresa_id, admin_user, admin_password, admin_nombre))
            
            usuario_id = cursor.lastrowid
            
            # Crear solicitud de registro
            cursor.execute("""
                INSERT INTO solicitudes_registro (empresa_id, usuario_id, estatus)
                VALUES (%s, %s, 'pendiente')
            """, (empresa_id, usuario_id))
            
            conn.commit()
            
            return jsonify({
                'success': True, 
                'message': 'Solicitud de registro enviada exitosamente. Recibirá una notificación cuando sea aprobada.'
            })
            
        except Exception as e:
            conn.rollback()
            print(f"Error en registro de empresa: {str(e)}")
            return jsonify({'success': False, 'message': f'Error al registrar la empresa: {str(e)}'}), 500
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f"Error general en registro: {str(e)}")
        return jsonify({'success': False, 'message': f'Error inesperado: {str(e)}'}), 500

@app.route('/super-admin/dashboard')
@login_required
@super_admin_required
def super_admin_dashboard():
    """Panel de control para super administradores"""
    return render_template('super_admin_dashboard.html', usuario=session['usuario'])

@app.route('/super-admin/empresas')
@login_required
@super_admin_required
def super_admin_empresas():
    """Gestión de empresas para super administradores"""
    try:
        print("🔍 Cargando empresas para super admin...")  # Debug
        conn = get_db_connection()
        if not conn:
            print("❌ No se pudo conectar a la base de datos")  # Debug
            return render_template('partials/super_admin_empresas.html', empresas=[])
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT e.*, 
                   COALESCE(u_count.total_usuarios, 0) as total_usuarios,
                   sr.estatus as solicitud_estatus,
                   sr.fecha_solicitud
            FROM empresa e
            LEFT JOIN (
                SELECT empresa_id, COUNT(*) as total_usuarios 
                FROM usuario 
                GROUP BY empresa_id
            ) u_count ON e.id = u_count.empresa_id
            LEFT JOIN solicitudes_registro sr ON e.id = sr.empresa_id
            ORDER BY e.fecha_registro DESC
        """)
        empresas = cursor.fetchall()
        
        return render_template('partials/super_admin_empresas.html', empresas=empresas)
        
    except Error as e:
        flash(f'Error al cargar empresas: {str(e)}', 'danger')
        return render_template('partials/super_admin_empresas.html', empresas=[])
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/super-admin/empresas/<int:empresa_id>/aprobar', methods=['PUT'])
@login_required
@super_admin_required
def aprobar_empresa(empresa_id):
    """API para aprobar una empresa"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
        
        cursor = conn.cursor()
        
        # Actualizar estatus de la empresa
        cursor.execute("""
            UPDATE empresa 
            SET estatus = 'activo', 
                fecha_aprobacion = NOW(), 
                aprobado_por = %s 
            WHERE id = %s
        """, (session['usuario']['id'], empresa_id))
        
        # Actualizar estatus de la solicitud
        cursor.execute("""
            UPDATE solicitudes_registro 
            SET estatus = 'aprobada', 
                fecha_revision = NOW(), 
                revisado_por = %s 
            WHERE empresa_id = %s
        """, (session['usuario']['id'], empresa_id))
        
        conn.commit()
        
        return jsonify({'success': True, 'message': 'Empresa aprobada exitosamente'})
        
    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        return jsonify({'success': False, 'message': f'Error al aprobar empresa: {str(e)}'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/super-admin/empresas/<int:empresa_id>/rechazar', methods=['PUT'])
@login_required
@super_admin_required
def rechazar_empresa(empresa_id):
    """API para rechazar una empresa"""
    try:
        comentarios = request.json.get('comentarios', '')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
        
        cursor = conn.cursor()
        
        # Actualizar estatus de la empresa
        cursor.execute("""
            UPDATE empresa 
            SET estatus = 'inactivo' 
            WHERE id = %s
        """, (empresa_id,))
        
        # Actualizar estatus de la solicitud
        cursor.execute("""
            UPDATE solicitudes_registro 
            SET estatus = 'rechazada', 
                fecha_revision = NOW(), 
                revisado_por = %s,
                comentarios = %s
            WHERE empresa_id = %s
        """, (session['usuario']['id'], comentarios, empresa_id))
        
        conn.commit()
        
        return jsonify({'success': True, 'message': 'Empresa rechazada exitosamente'})
        
    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        return jsonify({'success': False, 'message': f'Error al rechazar empresa: {str(e)}'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/super-admin/stats')
@login_required
@super_admin_required
def super_admin_stats():
    """API para obtener estadísticas del super admin"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Total de empresas
        cursor.execute("SELECT COUNT(*) as total FROM empresa")
        total_empresas = cursor.fetchone()['total']
        
        # Empresas pendientes
        cursor.execute("SELECT COUNT(*) as total FROM empresa WHERE estatus = 'en_espera'")
        empresas_pendientes = cursor.fetchone()['total']
        
        # Empresas activas
        cursor.execute("SELECT COUNT(*) as total FROM empresa WHERE estatus = 'activo'")
        empresas_activas = cursor.fetchone()['total']
        
        # Empresas inactivas
        cursor.execute("SELECT COUNT(*) as total FROM empresa WHERE estatus = 'inactivo'")
        empresas_inactivas = cursor.fetchone()['total']
        
        # Total de usuarios
        cursor.execute("SELECT COUNT(*) as total FROM usuario")
        total_usuarios = cursor.fetchone()['total']
        
        stats = {
            'total_empresas': total_empresas,
            'empresas_pendientes': empresas_pendientes,
            'empresas_activas': empresas_activas,
            'empresas_inactivas': empresas_inactivas,
            'total_usuarios': total_usuarios
        }
        
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener estadísticas: {str(e)}'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/super-admin/solicitudes/recientes')
@login_required
@super_admin_required
def solicitudes_recientes():
    """API para obtener solicitudes recientes"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT sr.*, e.nombre_empresa, e.codigo_empresa
            FROM solicitudes_registro sr
            JOIN empresa e ON sr.empresa_id = e.id
            ORDER BY sr.fecha_solicitud DESC
            LIMIT 10
        """)
        
        solicitudes = cursor.fetchall()
        
        # Formatear las fechas
        for solicitud in solicitudes:
            if solicitud['fecha_solicitud']:
                solicitud['fecha_solicitud'] = solicitud['fecha_solicitud'].strftime('%d/%m/%Y %H:%M')
            if solicitud['fecha_revision']:
                solicitud['fecha_revision'] = solicitud['fecha_revision'].strftime('%d/%m/%Y %H:%M')
        
        return jsonify({'success': True, 'solicitudes': solicitudes})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener solicitudes: {str(e)}'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/super-admin/solicitudes')
@login_required
@super_admin_required
def super_admin_solicitudes():
    """Página de gestión de solicitudes para super administradores"""
    return render_template('partials/super_admin_solicitudes.html')

@app.route('/api/super-admin/solicitudes')
@login_required
@super_admin_required
def obtener_solicitudes():
    """API para obtener todas las solicitudes con filtros"""
    try:
        estatus = request.args.get('estatus', 'todas')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Construir la consulta base
        query = """
            SELECT sr.*, e.nombre_empresa, e.codigo_empresa, e.email, e.rif, e.telefono, e.direccion,
                   sa.nombre_completo as revisor_nombre
            FROM solicitudes_registro sr
            JOIN empresa e ON sr.empresa_id = e.id
            LEFT JOIN super_admin sa ON sr.revisado_por = sa.id
        """
        
        # Agregar filtro de estatus si es necesario
        if estatus != 'todas':
            if estatus == 'pendientes':
                query += " WHERE sr.estatus = 'pendiente'"
            elif estatus == 'aprobadas':
                query += " WHERE sr.estatus = 'aprobada'"
            elif estatus == 'rechazadas':
                query += " WHERE sr.estatus = 'rechazada'"
        
        query += " ORDER BY sr.fecha_solicitud DESC"
        
        cursor.execute(query)
        solicitudes = cursor.fetchall()
        
        # Formatear las fechas
        for solicitud in solicitudes:
            if solicitud['fecha_solicitud']:
                solicitud['fecha_solicitud'] = solicitud['fecha_solicitud'].strftime('%d/%m/%Y %H:%M')
            if solicitud['fecha_revision']:
                solicitud['fecha_revision'] = solicitud['fecha_revision'].strftime('%d/%m/%Y %H:%M')
        
        return jsonify({'success': True, 'solicitudes': solicitudes})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener solicitudes: {str(e)}'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/super-admin/solicitudes/stats')
@login_required
@super_admin_required
def solicitudes_stats():
    """API para obtener estadísticas de solicitudes"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Total de solicitudes
        cursor.execute("SELECT COUNT(*) as total FROM solicitudes_registro")
        total_solicitudes = cursor.fetchone()['total']
        
        # Solicitudes pendientes
        cursor.execute("SELECT COUNT(*) as total FROM solicitudes_registro WHERE estatus = 'pendiente'")
        solicitudes_pendientes = cursor.fetchone()['total']
        
        # Solicitudes aprobadas
        cursor.execute("SELECT COUNT(*) as total FROM solicitudes_registro WHERE estatus = 'aprobada'")
        solicitudes_aprobadas = cursor.fetchone()['total']
        
        # Solicitudes rechazadas
        cursor.execute("SELECT COUNT(*) as total FROM solicitudes_registro WHERE estatus = 'rechazada'")
        solicitudes_rechazadas = cursor.fetchone()['total']
        
        stats = {
            'total_solicitudes': total_solicitudes,
            'solicitudes_pendientes': solicitudes_pendientes,
            'solicitudes_aprobadas': solicitudes_aprobadas,
            'solicitudes_rechazadas': solicitudes_rechazadas
        }
        
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener estadísticas: {str(e)}'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/super-admin/solicitudes/<int:solicitud_id>/detalles')
@login_required
@super_admin_required
def detalles_solicitud(solicitud_id):
    """API para obtener detalles completos de una solicitud"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Obtener información de la solicitud y empresa
        cursor.execute("""
            SELECT sr.*, e.*, sa.nombre_completo as revisor_nombre
            FROM solicitudes_registro sr
            JOIN empresa e ON sr.empresa_id = e.id
            LEFT JOIN super_admin sa ON sr.revisado_por = sa.id
            WHERE sr.id = %s
        """, (solicitud_id,))
        
        solicitud = cursor.fetchone()
        if not solicitud:
            return jsonify({'success': False, 'message': 'Solicitud no encontrada'}), 404
        
        # Formatear fechas
        if solicitud['fecha_solicitud']:
            solicitud['fecha_solicitud'] = solicitud['fecha_solicitud'].strftime('%d/%m/%Y %H:%M')
        if solicitud['fecha_revision']:
            solicitud['fecha_revision'] = solicitud['fecha_revision'].strftime('%d/%m/%Y %H:%M')
        if solicitud['fecha_registro']:
            solicitud['fecha_registro'] = solicitud['fecha_registro'].strftime('%d/%m/%Y %H:%M')
        if solicitud['fecha_aprobacion']:
            solicitud['fecha_aprobacion'] = solicitud['fecha_aprobacion'].strftime('%d/%m/%Y %H:%M')
        
        return jsonify({'success': True, 'solicitud': solicitud})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener detalles: {str(e)}'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/super-admin/solicitudes/<int:solicitud_id>/aprobar', methods=['PUT'])
@login_required
@super_admin_required
def aprobar_solicitud(solicitud_id):
    """API para aprobar una solicitud"""
    try:
        comentarios = request.json.get('comentarios', '')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
        
        cursor = conn.cursor()
        
        # Obtener el ID de la empresa de la solicitud
        cursor.execute("SELECT empresa_id FROM solicitudes_registro WHERE id = %s", (solicitud_id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({'success': False, 'message': 'Solicitud no encontrada'}), 404
        
        empresa_id = result[0]
        
        # Actualizar estatus de la solicitud
        cursor.execute("""
            UPDATE solicitudes_registro 
            SET estatus = 'aprobada', 
                fecha_revision = NOW(), 
                revisado_por = %s,
                comentarios = %s
            WHERE id = %s
        """, (session['usuario']['id'], comentarios, solicitud_id))
        
        # Actualizar estatus de la empresa
        cursor.execute("""
            UPDATE empresa 
            SET estatus = 'activo', 
                fecha_aprobacion = NOW(), 
                aprobado_por = %s 
            WHERE id = %s
        """, (session['usuario']['id'], empresa_id))
        
        conn.commit()
        
        return jsonify({'success': True, 'message': 'Solicitud aprobada exitosamente'})
        
    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        return jsonify({'success': False, 'message': f'Error al aprobar solicitud: {str(e)}'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/super-admin/solicitudes/<int:solicitud_id>/rechazar', methods=['PUT'])
@login_required
@super_admin_required
def rechazar_solicitud(solicitud_id):
    """API para rechazar una solicitud"""
    try:
        comentarios = request.json.get('comentarios', '')
        
        if not comentarios:
            return jsonify({'success': False, 'message': 'Los comentarios son obligatorios para rechazar una solicitud'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
        
        cursor = conn.cursor()
        
        # Obtener el ID de la empresa de la solicitud
        cursor.execute("SELECT empresa_id FROM solicitudes_registro WHERE id = %s", (solicitud_id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({'success': False, 'message': 'Solicitud no encontrada'}), 404
        
        empresa_id = result[0]
        
        # Actualizar estatus de la solicitud
        cursor.execute("""
            UPDATE solicitudes_registro 
            SET estatus = 'rechazada', 
                fecha_revision = NOW(), 
                revisado_por = %s,
                comentarios = %s
            WHERE id = %s
        """, (session['usuario']['id'], comentarios, solicitud_id))
        
        # Actualizar estatus de la empresa
        cursor.execute("""
            UPDATE empresa 
            SET estatus = 'inactivo'
            WHERE id = %s
        """, (empresa_id,))
        
        conn.commit()
        
        return jsonify({'success': True, 'message': 'Solicitud rechazada exitosamente'})
        
    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        return jsonify({'success': False, 'message': f'Error al rechazar solicitud: {str(e)}'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/super-admin/empresas/<int:empresa_id>/detalles')
@login_required
@super_admin_required
def detalles_empresa(empresa_id):
    """API para obtener detalles completos de una empresa"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Obtener información de la empresa
        cursor.execute("""
            SELECT e.*, COUNT(u.id) as total_usuarios
            FROM empresa e
            LEFT JOIN usuario u ON e.id = u.empresa_id
            WHERE e.id = %s
            GROUP BY e.id
        """, (empresa_id,))
        
        empresa = cursor.fetchone()
        if not empresa:
            return jsonify({'success': False, 'message': 'Empresa no encontrada'}), 404
        
        # Obtener información de la solicitud
        cursor.execute("""
            SELECT sr.*, sa.nombre_completo as revisor_nombre
            FROM solicitudes_registro sr
            LEFT JOIN super_admin sa ON sr.revisado_por = sa.id
            WHERE sr.empresa_id = %s
        """, (empresa_id,))
        
        solicitud = cursor.fetchone()
        
        # Formatear fechas
        if empresa['fecha_registro']:
            empresa['fecha_registro'] = empresa['fecha_registro'].strftime('%d/%m/%Y %H:%M')
        if empresa['fecha_aprobacion']:
            empresa['fecha_aprobacion'] = empresa['fecha_aprobacion'].strftime('%d/%m/%Y %H:%M')
        
        if solicitud:
            if solicitud['fecha_solicitud']:
                solicitud['fecha_solicitud'] = solicitud['fecha_solicitud'].strftime('%d/%m/%Y %H:%M')
            if solicitud['fecha_revision']:
                solicitud['fecha_revision'] = solicitud['fecha_revision'].strftime('%d/%m/%Y %H:%M')
        
        return jsonify({
            'success': True, 
            'empresa': empresa, 
            'solicitud': solicitud
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener detalles: {str(e)}'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/super-admin/empresas/<int:empresa_id>/toggle-status', methods=['PUT'])
@login_required
@super_admin_required
def toggle_empresa_status(empresa_id):
    """API para cambiar el estatus de una empresa"""
    try:
        nuevo_estatus = request.json.get('estatus')
        if nuevo_estatus not in ['activo', 'inactivo']:
            return jsonify({'success': False, 'message': 'Estatus inválido'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
        
        cursor = conn.cursor()
        
        # Actualizar estatus de la empresa
        cursor.execute("""
            UPDATE empresa 
            SET estatus = %s,
                fecha_aprobacion = CASE 
                    WHEN %s = 'activo' THEN NOW()
                    ELSE fecha_aprobacion
                END,
                aprobado_por = CASE 
                    WHEN %s = 'activo' THEN %s
                    ELSE aprobado_por
                END
            WHERE id = %s
        """, (nuevo_estatus, nuevo_estatus, nuevo_estatus, session['usuario']['id'], empresa_id))
        
        # Actualizar estatus de la solicitud si existe
        if nuevo_estatus == 'activo':
            cursor.execute("""
                UPDATE solicitudes_registro 
                SET estatus = 'aprobada', 
                    fecha_revision = NOW(), 
                    revisado_por = %s 
                WHERE empresa_id = %s
            """, (session['usuario']['id'], empresa_id))
        elif nuevo_estatus == 'inactivo':
            cursor.execute("""
                UPDATE solicitudes_registro 
                SET estatus = 'rechazada', 
                    fecha_revision = NOW(), 
                    revisado_por = %s 
                WHERE empresa_id = %s
            """, (session['usuario']['id'], empresa_id))
        
        conn.commit()
        
        return jsonify({'success': True, 'message': f'Empresa {nuevo_estatus} exitosamente'})
        
    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        return jsonify({'success': False, 'message': f'Error al cambiar estatus: {str(e)}'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/logout')
@login_required
def logout():
    """Cierra la sesión del usuario"""
    session.clear()
    flash('Has cerrado sesión correctamente', 'success')
    return redirect(url_for('login'))

@app.route('/manager')
@app.route('/manager/index')
@login_required
def manager():
    """Panel de control para administradores y soporte"""
    # Obtener información de la empresa
    empresa = None
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, nombre_empresa, email, rif, telefono, estatus
                FROM empresa 
                WHERE id = %s
            """, (session.get('empresa_id'),))
            empresa = cursor.fetchone()
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"Error al obtener empresa: {e}")
    
    return render_template('manager.html', usuario=session['usuario'], empresa=empresa)

@app.route('/manager/usuarios')
@login_required
@admin_required
def manager_usuarios():
    """Gestión de usuarios (solo admin)"""
    try:
        conn = get_db_connection()
        if not conn:
            return render_template('partials/usuarios.html', usuarios=[])
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, user, nombre_completo, rol, estatus 
            FROM usuario 
            WHERE empresa_id = %s
        """, (session.get('empresa_id'),))
        usuarios = cursor.fetchall()
        return render_template('partials/usuarios.html', usuarios=usuarios)
        
    except Error as e:
        flash(f'Error al cargar usuarios: {str(e)}', 'danger')
        return render_template('partials/usuarios.html', usuarios=[])
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/formulario/usuarios')
@login_required
@admin_required
def formulario_usuario():
    usuario_id = request.args.get('id')
    usuario = None
    
    if usuario_id:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM usuario 
                WHERE id = %s AND empresa_id = %s
            """, (usuario_id, session.get('empresa_id')))
            usuario = cursor.fetchone()
            cursor.close()
            conn.close()
    
    return render_template('partials/form_usuario.html', usuario=usuario)

@app.route('/api/usuarios', methods=['GET', 'POST'])
@login_required
@admin_required
def api_usuarios():
    if request.method == 'GET':
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT id, user, nombre_completo, estatus, rol 
                FROM usuario 
                WHERE empresa_id = %s
            """, (session.get('empresa_id'),))
            usuarios = cur.fetchall()
            return jsonify(usuarios)
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 400
        finally:
            cur.close()
            conn.close()
    
    elif request.method == 'POST':
        data = request.get_json()
        print(f"Datos recibidos para crear usuario: {data}")  # Debug
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            # Guardar contraseña en texto plano (sin encriptar)
            print(f"Contraseña en texto plano: {data['password']}")  # Debug
            cur.execute("""
                INSERT INTO usuario (empresa_id, user, password, nombre_completo, estatus, rol)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (session.get('empresa_id'), data['user'], data['password'], data['nombre_completo'], data['estatus'], data['rol']))
            conn.commit()
            print("Usuario creado exitosamente")  # Debug
            return jsonify({'success': True, 'message': 'Usuario creado correctamente'})
        except Exception as e:
            print(f"Error al crear usuario: {str(e)}")  # Debug
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400
        finally:
            cur.close()
            conn.close()

@app.route('/api/usuarios/<int:user_id>', methods=['PUT', 'DELETE'])
@login_required
@admin_required
def api_usuario(user_id):
    if request.method == 'PUT':
        data = request.get_json()
        print(f"Datos recibidos para actualizar usuario {user_id}: {data}")  # Debug
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            if 'password' in data and data['password']:
                # Guardar contraseña en texto plano (sin encriptar)
                print(f"Contraseña en texto plano para actualización: {data['password']}")  # Debug
                cur.execute("""
                    UPDATE usuario 
                    SET user=%s, password=%s, nombre_completo=%s, estatus=%s, rol=%s
                    WHERE id=%s AND empresa_id=%s
                """, (data['user'], data['password'], data['nombre_completo'], data['estatus'], data['rol'], user_id, session.get('empresa_id')))
            else:
                print("Actualizando usuario sin cambiar contraseña")  # Debug
                cur.execute("""
                    UPDATE usuario 
                    SET user=%s, nombre_completo=%s, estatus=%s, rol=%s 
                    WHERE id=%s AND empresa_id=%s
                """, (data['user'], data['nombre_completo'], data['estatus'], data['rol'], user_id, session.get('empresa_id')))
                
            conn.commit()
            print("Usuario actualizado exitosamente")  # Debug
            return jsonify({'success': True, 'message': 'Usuario actualizado correctamente'})
        except Exception as e:
            print(f"Error al actualizar usuario: {str(e)}")  # Debug
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400
        finally:
            cur.close()
            conn.close()
    
    elif request.method == 'DELETE':
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                DELETE FROM usuario 
                WHERE id = %s AND empresa_id = %s
            """, (user_id, session.get('empresa_id')))
            conn.commit()
            return jsonify({'success': True, 'message': 'Usuario eliminado correctamente'})
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400
        finally:
            cur.close()
            conn.close()

@app.route('/manager/items')
@login_required
@admin_required
def manager_items():
    """Gestión de items del menú (solo admin)"""
    try:
        conn = get_db_connection()
        if not conn:
            return render_template('partials/items.html', items=[], grupos=[])
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT i.id, i.nombre, i.precio, i.existencia, i.estatus, g.nombre as grupo 
            FROM item i 
            JOIN grupos g ON i.grupo_codigo = g.id
            WHERE i.empresa_id = %s
            ORDER BY i.nombre
        """, (session.get('empresa_id'),))
        items = cursor.fetchall()
        
        # Convertir Decimal a float para JSON
        for item in items:
            item['precio'] = float(item['precio'])
        
        cursor.execute("""
            SELECT id, nombre 
            FROM grupos 
            WHERE empresa_id = %s AND estatus = 'activo'
            ORDER BY nombre
        """, (session.get('empresa_id'),))
        grupos = cursor.fetchall()
        
        return render_template('partials/items.html', items=items, grupos=grupos)
        
    except Error as e:
        flash(f'Error al cargar items: {str(e)}', 'danger')
        return render_template('partials/items.html', items=[], grupos=[])
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/formulario/items')
@login_required
@admin_required
def formulario_items():
    """Formulario para crear/editar items"""
    item_id = request.args.get('id')
    item = None
    
    try:
        conn = get_db_connection()
        if not conn:
            return render_template('partials/form_item.html', item=None, grupos=[])
            
        cursor = conn.cursor(dictionary=True)
        
        # Obtener grupos para el select
        cursor.execute("""
            SELECT id, nombre 
            FROM grupos 
            WHERE empresa_id = %s AND estatus = 'activo' 
            ORDER BY nombre
        """, (session.get('empresa_id'),))
        grupos = cursor.fetchall()
        
        # Si hay ID, obtener el item
        if item_id:
            cursor.execute("""
                SELECT i.*, g.nombre as grupo_nombre 
                FROM item i 
                JOIN grupos g ON i.grupo_codigo = g.id 
                WHERE i.id = %s AND i.empresa_id = %s
            """, (item_id, session.get('empresa_id')))
            item = cursor.fetchone()
            
            if item:
                # Convertir Decimal a float para el formulario
                item['precio'] = float(item['precio'])
        
        return render_template('partials/form_item.html', item=item, grupos=grupos)
        
    except Error as e:
        flash(f'Error al cargar formulario: {str(e)}', 'danger')
        return render_template('partials/form_item.html', item=None, grupos=[])
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/mesas')
@login_required
def mesas():
    """Vista principal de mesas para usuarios regulares"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Error de conexión a la base de datos', 'danger')
            return render_template('mesas.html', mesas=[], productos=[], grupos=[])
        
        with conn.cursor(dictionary=True) as cursor:
            # Obtener mesas
            cursor.execute("""
                SELECT Id as id, nombre, estatus 
                FROM mesas 
                WHERE empresa_id = %s
                ORDER BY nombre
            """, (session.get('empresa_id'),))
            mesas = cursor.fetchall()

            # Obtener grupos de productos
            cursor.execute("""
                SELECT id, nombre, estatus 
                FROM grupos 
                WHERE empresa_id = %s AND estatus = 'activo' 
                ORDER BY id
            """, (session.get('empresa_id'),))
            grupos = cursor.fetchall()
            
            # Obtener productos disponibles
            cursor.execute("""
                SELECT p.id, p.nombre, p.precio_venta, p.grupo_id, g.nombre as grupo_nombre 
                FROM productos p
                LEFT JOIN grupos g ON p.grupo_id = g.id
                WHERE p.empresa_id = %s AND p.estatus = 'activo' AND p.cantidad_disponible > 0
                ORDER BY g.nombre, p.nombre
            """, (session.get('empresa_id'),))
            productos = cursor.fetchall()
            
            # Convertir precios Decimal a float
            for producto in productos:
                producto['precio_venta'] = float(producto['precio_venta'])
            
            return render_template('mesas.html', 
                                mesas=mesas, 
                                productos=productos, 
                                grupos=grupos,
                                usuario=session.get('usuario'))
                                
    except Exception as e:
        flash(f'Error al cargar mesas: {str(e)}', 'danger')
        return render_template('mesas.html', mesas=[], productos=[], grupos=[])
    finally:
        if 'conn' in locals(): conn.close()

@app.route('/formulario/mesas')
@login_required
@admin_required
def formulario_mesas():
    """Formulario para crear/editar mesas"""
    mesa_id = request.args.get('id')
    mesa = None
    
    if mesa_id:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM mesas 
                WHERE Id = %s AND empresa_id = %s
            """, (mesa_id, session.get('empresa_id')))
            mesa = cursor.fetchone()
            cursor.close()
            conn.close()
    
    return render_template('partials/form_mesas.html', mesa=mesa)

@app.route('/api/mesas', methods=['GET'])
@login_required
def obtener_mesas():
    """API para obtener todas las mesas"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT Id as id, nombre, estatus 
            FROM mesas 
            WHERE empresa_id = %s
            ORDER BY nombre
        """, (session.get('empresa_id'),))
        mesas = cursor.fetchall()
        
        return jsonify(mesas)
        
    except Exception as e:
        print("Error al obtener mesas:", str(e))
        return jsonify({'success': False, 'message': f'Error al obtener mesas: {str(e)}'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/mesas', methods=['POST'])
@login_required
@admin_required
def crear_mesa():
    """API para crear nueva mesa"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        data = request.get_json()
        print("Datos recibidos para crear mesa:", data)  # Debug
        
        # Validaciones
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
            
        if not data.get('nombre'):
            return jsonify({'success': False, 'message': 'El nombre es requerido'}), 400
            
        if not data.get('estatus'):
            return jsonify({'success': False, 'message': 'El estatus es requerido'}), 400

        # Insertar nueva mesa
        cursor.execute('''
            INSERT INTO mesas (empresa_id, nombre, estatus) 
            VALUES (%s, %s, %s)
        ''', (session.get('empresa_id'), data['nombre'], data['estatus']))
        conn.commit()
        return jsonify({'success': True, 'message': 'Mesa creada correctamente'})
    except Exception as e:
        print("Error al crear mesa:", str(e))  # Debug
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error al crear la mesa: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/mesas/<int:mesa_id>', methods=['PUT', 'DELETE'])
@login_required
@admin_required
def gestion_mesa(mesa_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if request.method == 'PUT':
            data = request.get_json()
            print("Datos recibidos para actualizar mesa:", data)  # Debug
            
            # Validaciones
            if not data:
                return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
                
            if not data.get('nombre'):
                return jsonify({'success': False, 'message': 'El nombre es requerido'}), 400
                
            if not data.get('estatus'):
                return jsonify({'success': False, 'message': 'El estatus es requerido'}), 400

            # Verificar si la mesa existe
            cursor.execute('SELECT Id FROM mesas WHERE Id = %s AND empresa_id = %s', (mesa_id, session.get('empresa_id')))
            if not cursor.fetchone():
                return jsonify({'success': False, 'message': 'La mesa no existe'}), 404

            # Actualizar mesa
            cursor.execute('''
                UPDATE mesas 
                SET nombre = %s, estatus = %s 
                WHERE Id = %s
            ''', (data['nombre'], data['estatus'], mesa_id))
            conn.commit()
            return jsonify({'success': True, 'message': 'Mesa actualizada correctamente'})

        elif request.method == 'DELETE':
            # Verificar si la mesa existe
            cursor.execute('SELECT Id FROM mesas WHERE Id = %s', (mesa_id,))
            if not cursor.fetchone():
                return jsonify({'success': False, 'message': 'La mesa no existe'}), 404

            # Verificar si la mesa está en uso
            cursor.execute('''
                SELECT COUNT(*) FROM comandas 
                WHERE mesa_id = %s AND estatus = 'pendiente'
            ''', (mesa_id,))
            if cursor.fetchone()[0] > 0:
                return jsonify({'success': False, 'message': 'No se puede eliminar, la mesa tiene comandas pendientes'}), 400

            cursor.execute('DELETE FROM mesas WHERE Id = %s', (mesa_id,))
            conn.commit()
            return jsonify({'success': True, 'message': 'Mesa eliminada correctamente'})

    except Exception as e:
        print("Error en gestión de mesa:", str(e))  # Debug
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error en la operación: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

# ======================
# RUTAS PARA ITEMS
# ======================
@app.route('/api/items', methods=['POST'])
@login_required
@admin_required
def crear_item():
    """API para crear nuevo item"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        data = request.get_json()
        print("Datos recibidos para crear item:", data)  # Debug
        
        # Validaciones
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
            
        if not data.get('nombre'):
            return jsonify({'success': False, 'message': 'El nombre es requerido'}), 400
            
        if not data.get('grupo_codigo'):
            return jsonify({'success': False, 'message': 'El grupo es requerido'}), 400
            
        if data.get('precio') is None or float(data.get('precio', 0)) <= 0:
            return jsonify({'success': False, 'message': 'El precio debe ser mayor a 0'}), 400
            
        if data.get('existencia') is None or int(data.get('existencia', -1)) < 0:
            return jsonify({'success': False, 'message': 'La existencia no puede ser negativa'}), 400

        # Insertar nuevo item
        cursor.execute('''
            INSERT INTO item (nombre, precio, existencia, grupo_codigo, estatus) 
            VALUES (%s, %s, %s, %s, %s)
        ''', (data['nombre'], data['precio'], data['existencia'], data['grupo_codigo'], data.get('estatus', 'activo')))
        conn.commit()
        return jsonify({'success': True, 'message': 'Item creado correctamente'})
    except Exception as e:
        print("Error al crear item:", str(e))  # Debug
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error al crear el item: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/items/<int:item_id>', methods=['PUT', 'DELETE'])
@login_required
@admin_required
def gestion_item(item_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if request.method == 'PUT':
            data = request.get_json()
            print("Datos recibidos para actualizar item:", data)  # Debug
            
            # Validaciones
            if not data:
                return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
                
            if not data.get('nombre'):
                return jsonify({'success': False, 'message': 'El nombre es requerido'}), 400
                
            if not data.get('grupo_codigo'):
                return jsonify({'success': False, 'message': 'El grupo es requerido'}), 400
                
            if data.get('precio') is None or float(data.get('precio', 0)) <= 0:
                return jsonify({'success': False, 'message': 'El precio debe ser mayor a 0'}), 400
                
            if data.get('existencia') is None or int(data.get('existencia', -1)) < 0:
                return jsonify({'success': False, 'message': 'La existencia no puede ser negativa'}), 400

            # Verificar si el item existe
            cursor.execute('SELECT id FROM item WHERE id = %s', (item_id,))
            if not cursor.fetchone():
                return jsonify({'success': False, 'message': 'El item no existe'}), 404

            # Actualizar item
            cursor.execute('''
                UPDATE item 
                SET nombre = %s, precio = %s, existencia = %s, grupo_codigo = %s, estatus = %s 
                WHERE id = %s
            ''', (data['nombre'], data['precio'], data['existencia'], data['grupo_codigo'], data.get('estatus', 'activo'), item_id))
            conn.commit()
            return jsonify({'success': True, 'message': 'Item actualizado correctamente'})

        elif request.method == 'DELETE':
            # Verificar si el item existe
            cursor.execute('SELECT id FROM item WHERE id = %s', (item_id,))
            if not cursor.fetchone():
                return jsonify({'success': False, 'message': 'El item no existe'}), 404

            # Verificar si el item está en uso
            cursor.execute('''
                SELECT COUNT(*) FROM comanda_detalle 
                WHERE item_id = %s
            ''', (item_id,))
            if cursor.fetchone()[0] > 0:
                return jsonify({'success': False, 'message': 'No se puede eliminar, el item tiene comandas asociadas'}), 400

            cursor.execute('DELETE FROM item WHERE id = %s', (item_id,))
            conn.commit()
            return jsonify({'success': True, 'message': 'Item eliminado correctamente'})

    except Exception as e:
        print("Error en gestión de item:", str(e))  # Debug
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error en la operación: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

# ======================
# RUTAS PARA USUARIOS
# ======================

@app.route('/manager/mesas')
@login_required
@admin_required
def manager_mesas():
    """Gestión de mesas (solo admin)"""
    try:
        conn = get_db_connection()
        if not conn:
            return render_template('partials/mesas.html', mesas=[])
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT Id, nombre, estatus FROM mesas ORDER BY nombre")
        mesas = cursor.fetchall()
        
        return render_template('partials/mesas.html', mesas=mesas)
        
    except Error as e:
        flash(f'Error al cargar mesas: {str(e)}', 'danger')
        return render_template('partials/mesas.html', mesas=[])
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/manager/ventas')
@login_required
@admin_required
def manager_ventas():
    """Reporte de ventas (solo admin)"""
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        print(f"=== DIAGNÓSTICO VENTAS ===")  # Debug
        print(f"Fechas recibidas: inicio={fecha_inicio}, fin={fecha_fin}")  # Debug
        
        conn = get_db_connection()
        if not conn:
            print("Error: No se pudo establecer conexión con la base de datos")
            return render_template('partials/ventas.html', ventas_items=[], total_ventas=0)
            
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Primero verificar si hay datos en las tablas
            cursor.execute("SELECT COUNT(*) as total FROM comandas")
            total_comandas = cursor.fetchone()['total']
            print(f"Total de comandas en BD: {total_comandas}")  # Debug
            
            cursor.execute("SELECT COUNT(*) as total FROM comanda_detalle")
            total_detalles = cursor.fetchone()['total']
            print(f"Total de detalles en BD: {total_detalles}")  # Debug
            
            cursor.execute("SELECT COUNT(*) as total FROM productos")
            total_items = cursor.fetchone()['total']
            print(f"Total de items en BD: {total_items}")  # Debug
            
            cursor.execute("SELECT estatus, COUNT(*) as cantidad FROM comandas GROUP BY estatus")
            estatus_comandas = cursor.fetchall()
            print(f"Estatus de comandas: {estatus_comandas}")  # Debug
            
            query = """
                SELECT p.nombre as item, SUM(d.cantidad) as cantidad, SUM(d.total) as total
                FROM comanda_detalle d
                JOIN productos p ON d.producto_id = p.id
                JOIN comandas c ON d.comanda_id = c.id
                WHERE c.estatus = 'pagada'
            """
            
            params = []
            
            if fecha_inicio and fecha_fin:
                query += " AND c.fecha BETWEEN %s AND %s"
                params.extend([fecha_inicio, fecha_fin + " 23:59:59"])
            elif fecha_inicio:
                query += " AND c.fecha >= %s"
                params.append(fecha_inicio)
            elif fecha_fin:
                query += " AND c.fecha <= %s"
                params.append(fecha_fin + " 23:59:59")
                
            query += " GROUP BY p.nombre ORDER BY total DESC"
            
            print(f"Query final: {query}")  # Debug
            print(f"Params: {params}")  # Debug
            
            cursor.execute(query, params)
            ventas_items = cursor.fetchall()
            
            print(f"Resultados obtenidos: {len(ventas_items)} registros")  # Debug
            print(f"Ventas items: {ventas_items}")  # Debug
            
            # Calcular total general
            total_ventas = sum(float(item['total']) for item in ventas_items)
            print(f"Total de ventas calculado: {total_ventas}")  # Debug
            
            return render_template('partials/ventas.html', 
                                ventas_items=ventas_items, 
                                total_ventas=total_ventas)
            
        except Error as err:
            print(f"Error en la consulta SQL: {str(err)}")  # Debug
            flash(f'Error al generar reporte: {str(err)}', 'danger')
            return render_template('partials/ventas.html', ventas_items=[], total_ventas=0)
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"Error general en manager_ventas: {str(e)}")  # Debug
        return render_template('partials/ventas.html', ventas_items=[], total_ventas=0)

@app.route('/manager/comandas')
@login_required
def manager_comandas():
    """Listado de comandas"""
    try:
        conn = get_db_connection()
        if not conn:
            print("Error: No se pudo establecer conexión con la base de datos")
            return render_template('partials/comandas_list.html', comandas=[])
            
        cursor = conn.cursor(dictionary=True)
        
        try:
            query = """
                SELECT c.id, m.nombre as mesa_nombre, c.fecha, c.total, c.estatus, 
                       u.nombre_completo as usuario_nombre
                FROM comandas c
                JOIN mesas m ON c.mesa_id = m.Id
                LEFT JOIN usuario u ON c.usuario_id = u.id
                ORDER BY c.fecha DESC
            """
            
            print(f"Query: {query}")  # Debug
            
            cursor.execute(query)
            comandas = cursor.fetchall()
            
            print(f"Comandas encontradas: {len(comandas)}")  # Debug
            
            # Convertir Decimal a float para la plantilla
            for comanda in comandas:
                comanda['total'] = float(comanda['total'])
            
            return render_template('partials/comandas_list.html', comandas=comandas)
            
        except Error as e:
            print(f"Error en la consulta SQL: {str(e)}")  # Debug
            flash(f'Error al cargar comandas: {str(e)}', 'danger')
            return render_template('partials/comandas_list.html', comandas=[])
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"Error general en manager_comandas: {str(e)}")  # Debug
        return render_template('partials/comandas_list.html', comandas=[])

@app.route('/api/comandas/<int:comanda_id>')
@login_required
def obtener_comanda(comanda_id):
    """Obtener detalles de una comanda específica"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a BD'}), 500
        
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT c.id, m.nombre as mesa_nombre, c.fecha, c.total, c.estatus
            FROM comandas c
            JOIN mesas m ON c.mesa_id = m.Id
            WHERE c.id = %s
        """, (comanda_id,))
        comanda = cursor.fetchone()
        
        if not comanda:
            return jsonify({'error': 'Comanda no encontrada'}), 404
            
        cursor.execute("""
            SELECT p.nombre as item_nombre, d.cantidad, d.precio_unitario, d.total
            FROM comanda_detalle d
            JOIN productos p ON d.producto_id = p.id
            WHERE d.comanda_id = %s
        """, (comanda_id,))
        detalles = cursor.fetchall()
        
        # Convertir Decimal a float para JSON
        comanda['total'] = float(comanda['total'])
        for detalle in detalles:
            detalle['precio_unitario'] = float(detalle['precio_unitario'])
            detalle['total'] = float(detalle['total'])
        
        return jsonify({
            'id': comanda['id'],
            'mesa_nombre': comanda['mesa_nombre'],
            'fecha': comanda['fecha'].strftime('%Y-%m-%d %H:%M:%S'),
            'total': comanda['total'],
            'estatus': comanda['estatus'],
            'detalles': detalles
        })
        
    except Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/comandas/<int:comanda_id>/pagar', methods=['POST'])
@login_required
def procesar_pago_comanda(comanda_id):
    """Procesar pago de una comanda y facturar automáticamente si corresponde"""
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        print(f"🔍 Procesando pago para comanda {comanda_id}")
        print(f"📊 Datos recibidos: {data}")
        # Verificar que la comanda existe y pertenece a la empresa
        cursor.execute("""
            SELECT id, total, estatus_pago 
            FROM comandas 
            WHERE id = %s AND empresa_id = %s
        """, (comanda_id, session.get('empresa_id')))
        comanda = cursor.fetchone()
        if not comanda:
            return jsonify({'success': False, 'error': 'Comanda no encontrada'}), 404
        print(f"📋 Comanda encontrada: ID={comanda[0]}, Total={comanda[1]} (tipo: {type(comanda[1])}), Estatus={comanda[2]}")
        if comanda[2] == 'pagado':
            return jsonify({'success': False, 'error': 'La comanda ya está pagada'}), 400
        pagos = data.get('pagos', [])
        estatus_pago = data.get('estatus_pago', 'pagado')
        print(f"💳 Pagos a procesar: {pagos}")
        print(f"🏷️ Estatus de pago: {estatus_pago}")
        # Calcular total de pagos
        total_pagado = sum(pago.get('monto', 0) for pago in pagos)
        print(f"💰 Total pagado: {total_pagado} (tipo: {type(total_pagado)})")
        total_comanda = float(comanda[1]) if comanda[1] is not None else 0.0
        print(f"📊 Total comanda convertido: {total_comanda} (tipo: {type(total_comanda)})")
        if estatus_pago == 'pagado':
            diferencia = abs(total_pagado - total_comanda)
            print(f"🔍 Diferencia: {diferencia}")
            if diferencia > 0.01:
                return jsonify({'success': False, 'error': f'El total pagado (${total_pagado:.2f}) no coincide con el total de la comanda (${total_comanda:.2f})'}), 400
        print("✅ Validaciones pasadas, procediendo a crear factura...")

        # === CONTROL DE INVENTARIO ===
        empresa_id = session.get('empresa_id')
        # Obtener los productos reales y cantidades de la comanda
        cursor.execute('''
            SELECT d.producto_id, d.cantidad
            FROM comanda_detalle d
            JOIN productos p ON d.producto_id = p.id
            WHERE d.comanda_id = %s
        ''', (comanda_id,))
        productos_comanda = cursor.fetchall()
        productos_sin_stock = []
        for det in productos_comanda:
            producto_id = det[0]
            cantidad_necesaria = float(det[1])
            cursor.execute("SELECT cantidad_disponible, nombre FROM productos WHERE id = %s AND empresa_id = %s", (producto_id, empresa_id))
            prod = cursor.fetchone()
            if not prod or float(prod[0]) < cantidad_necesaria:
                productos_sin_stock.append(prod[1] if prod else f'ID {producto_id}')
        if productos_sin_stock:
            return jsonify({'success': False, 'error': f"Stock insuficiente para: {', '.join(productos_sin_stock)}"}), 400
        # Descontar stock
        for det in productos_comanda:
            producto_id = det[0]
            cantidad_necesaria = float(det[1])
            cursor.execute("UPDATE productos SET cantidad_disponible = cantidad_disponible - %s WHERE id = %s AND empresa_id = %s", (cantidad_necesaria, producto_id, empresa_id))

        cursor.execute("SELECT id FROM facturas WHERE comanda_id = %s AND empresa_id = %s", (comanda_id, session.get('empresa_id')))
        factura_id = None
        if not cursor.fetchone():
            # Usar un cursor tipo diccionario para la facturación
            cursor_dict = conn.cursor(dictionary=True)
            # Obtener datos de la comanda para facturar
            cursor_dict.execute("SELECT * FROM comandas WHERE id = %s", (comanda_id,))
            comanda_data = cursor_dict.fetchone()
            # Generar número de factura correlativo
            cursor_dict.execute("SELECT COALESCE(MAX(numero_factura), 0) + 1 as next_num FROM facturas WHERE empresa_id = %s", (session.get('empresa_id'),))
            numero_factura = cursor_dict.fetchone()['next_num']
            # Insertar factura
            cursor_dict.execute("""
                INSERT INTO facturas (comanda_id, numero_factura, cliente_id, total, metodo_pago, estatus, usuario_id, empresa_id)
                VALUES (%s, %s, %s, %s, %s, 'emitida', %s, %s)
            """, (
                comanda_id,
                numero_factura,
                comanda_data.get('cliente_id'),
                comanda_data['total'],
                comanda_data['estatus_pago'],
                session['usuario']['id'],
                session.get('empresa_id')
            ))
            factura_id = cursor_dict.lastrowid
            # Insertar detalles de factura
            cursor_dict.execute("SELECT * FROM comanda_detalle WHERE comanda_id = %s", (comanda_id,))
            detalles = cursor_dict.fetchall()
            for det in detalles:
                cursor_dict.execute("""
                    INSERT INTO factura_detalle (factura_id, producto_id, cantidad, precio_unitario, total, nota, empresa_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    factura_id,
                    det['producto_id'],
                    det['cantidad'],
                    det['precio_unitario'],
                    det['total'],
                    det.get('nota', ''),
                    session.get('empresa_id')
                ))
            cursor_dict.close()
        else:
            # Si ya existe factura, obtener su ID
            cursor.execute("SELECT id FROM facturas WHERE comanda_id = %s AND empresa_id = %s", (comanda_id, session.get('empresa_id')))
            factura_id = cursor.fetchone()[0]
        
        print(f"✅ Factura creada/obtenida con ID: {factura_id}")
        
        # Determinar estatus de pago real
        if abs(total_pagado - total_comanda) < 0.01:
            estatus_pago_real = 'pagado'
            factura_estatus = 'pagada'
        else:
            estatus_pago_real = 'credito'
            factura_estatus = 'emitida'

        # Insertar pagos usando el factura_id correcto
        medios_pago_nombres = []
        for pago in pagos:
            print(f"💾 Insertando pago: {pago}")
            cursor.execute("""
                INSERT INTO pagos_factura 
                (factura_id, medio_pago_id, monto, referencia, banco, observaciones, usuario_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                factura_id,  # ← Corregido: usar factura_id en lugar de comanda_id
                pago.get('medio_pago_id'),
                pago.get('monto'),
                pago.get('referencia', ''),
                pago.get('banco', ''),
                pago.get('observaciones', ''),
                session['usuario']['id']
            ))
            # Obtener nombre del medio de pago
            cursor.execute("SELECT nombre FROM medios_pago WHERE id = %s", (pago.get('medio_pago_id'),))
            medio = cursor.fetchone()
            if medio:
                medios_pago_nombres.append(medio[0])
        # Actualizar metodo_pago de la factura según los pagos
        if medios_pago_nombres:
            metodo_pago_final = ', '.join(medios_pago_nombres)
            cursor.execute("UPDATE facturas SET metodo_pago = %s WHERE id = %s", (metodo_pago_final, factura_id))

        print("✅ Pagos insertados, actualizando estatus de comanda y factura...")
        # Actualizar estatus de la comanda
        cursor.execute("""
            UPDATE comandas 
            SET estatus_pago = %s, estatus = 'pagada'
            WHERE id = %s
        """, (estatus_pago_real, comanda_id))
        # Actualizar estatus de la factura
        cursor.execute("""
            UPDATE facturas
            SET estatus = %s
            WHERE id = %s
        """, (factura_estatus, factura_id))
        
        # Si es pagado, liberar la mesa
        if estatus_pago_real == 'pagado':
            print("🆓 Liberando mesa...")
            cursor.execute("SELECT mesa_id FROM comandas WHERE id = %s", (comanda_id,))
            mesa_row = cursor.fetchone()
            if mesa_row and mesa_row[0]:
                cursor.execute("UPDATE mesas SET estatus = 'libre' WHERE id = %s", (mesa_row[0],))
        conn.commit()
        print("✅ Transacción completada exitosamente")
        return jsonify({
            'success': True,
            'message': f'Pago procesado exitosamente. Estatus: {estatus_pago_real}',
            'factura_id': factura_id
        })
    except Exception as e:
        conn.rollback()
        print(f"❌ Error en procesar_pago_comanda: {str(e)}")
        print(f"🔍 Tipo de error: {type(e)}")
        import traceback
        print(f"📋 Traceback completo: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/formulario/grupos')
@login_required
@admin_required
def formulario_grupos():
    grupo = None
    if request.args.get('id'):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM grupos WHERE id = %s', (request.args.get('id'),))
            grupo = cursor.fetchone()
        finally:
            cursor.close()
            conn.close()
    return render_template('partials/form_grupo.html', grupo=grupo)

@app.route('/api/ventas-item/comandas')
@login_required
def obtener_comandas_item():
    """Obtener comandas de un ítem específico"""
    item_nombre = request.args.get('item')
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    
    if not item_nombre:
        return jsonify({'error': 'Se requiere el nombre del ítem'}), 400
        
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a BD'}), 500
        
    cursor = conn.cursor(dictionary=True)
    
    try:
        query = """
            SELECT c.id, m.nombre as mesa_nombre, c.fecha, d.cantidad, d.total
            FROM comandas c
            JOIN mesas m ON c.mesa_id = m.Id
            JOIN comanda_detalle d ON c.id = d.comanda_id
            JOIN productos p ON d.producto_id = p.id
            WHERE p.nombre = %s AND c.estatus = 'pagada'
        """
        params = [item_nombre]
        
        if fecha_inicio and fecha_fin:
            query += " AND c.fecha BETWEEN %s AND %s"
            params.extend([fecha_inicio, fecha_fin + " 23:59:59"])
        elif fecha_inicio:
            query += " AND c.fecha >= %s"
            params.append(fecha_inicio)
        elif fecha_fin:
            query += " AND c.fecha <= %s"
            params.append(fecha_fin + " 23:59:59")
            
        query += " ORDER BY c.fecha DESC"
        
        cursor.execute(query, params)
        comandas = cursor.fetchall()
        
        # Convertir Decimal a float para JSON
        for comanda in comandas:
            comanda['total'] = float(comanda['total'])
        
        return jsonify({
            'success': True,
            'comandas': comandas
        })
        
    except Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/manager/impresoras')
@login_required
@admin_required
def manager_impresoras():
    """Gestión de impresoras (solo admin)"""
    try:
        conn = get_db_connection()
        if not conn:
            return render_template('partials/impresoras.html', impresoras=[], grupos=[])
            
        cursor = conn.cursor(dictionary=True)
        
        # Obtener impresoras con sus grupos asignados
        cursor.execute("""
            SELECT i.*, GROUP_CONCAT(ig.grupo_id) as grupos_ids
            FROM impresoras i
            LEFT JOIN impresora_grupos ig ON i.id = ig.impresora_id
            GROUP BY i.id
            ORDER BY i.nombre
        """)
        impresoras = cursor.fetchall()
        
        # Obtener grupos para el select
        cursor.execute("SELECT id, nombre FROM grupos WHERE estatus = 'activo' ORDER BY nombre")
        grupos = cursor.fetchall()
        
        return render_template('partials/impresoras.html', impresoras=impresoras, grupos=grupos)
        
    except Error as e:
        flash(f'Error al cargar impresoras: {str(e)}', 'danger')
        return render_template('partials/impresoras.html', impresoras=[], grupos=[])
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/impresoras', methods=['POST'])
@login_required
@admin_required
def crear_impresora():
    """API para crear nueva impresora"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        data = request.get_json()
        print("Datos recibidos para crear impresora:", data)  # Debug
        
        # Validaciones
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
            
        if not data.get('nombre'):
            return jsonify({'success': False, 'message': 'El nombre es requerido'}), 400
            
        if not data.get('tipo'):
            return jsonify({'success': False, 'message': 'El tipo es requerido'}), 400
            
        if data.get('tipo') == 'red' and (not data.get('ip') or not data.get('puerto')):
            return jsonify({'success': False, 'message': 'IP y puerto son requeridos para impresoras de red'}), 400

        # Insertar nueva impresora
        cursor.execute('''
            INSERT INTO impresoras (nombre, tipo, ip, puerto, estatus) 
            VALUES (%s, %s, %s, %s, %s)
        ''', (data['nombre'], data['tipo'], data.get('ip'), data.get('puerto'), data.get('estatus', 'activa')))
        impresora_id = cursor.lastrowid
        
        # Asignar grupos si se proporcionaron
        if data.get('grupos'):
            grupos_values = [(impresora_id, grupo_id) for grupo_id in data['grupos']]
            cursor.executemany('''
                INSERT INTO impresora_grupos (impresora_id, grupo_id) 
                VALUES (%s, %s)
            ''', grupos_values)
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Impresora creada correctamente'})
    except Exception as e:
        print("Error al crear impresora:", str(e))  # Debug
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error al crear la impresora: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/impresoras/<int:impresora_id>', methods=['PUT', 'DELETE'])
@login_required
@admin_required
def gestion_impresora(impresora_id):
    """API para actualizar o eliminar una impresora"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Error de conexión a BD'}), 500
    
    cursor = conn.cursor()
    try:
        if request.method == 'DELETE':
            # Primero eliminar las asignaciones de grupos
            cursor.execute('DELETE FROM impresora_grupos WHERE impresora_id = %s', (impresora_id,))
            
            # Luego eliminar la impresora
            cursor.execute('DELETE FROM impresoras WHERE id = %s', (impresora_id,))
            conn.commit()
            return jsonify({'success': True, 'message': 'Impresora eliminada correctamente'})
            
        elif request.method == 'PUT':
            data = request.get_json()
            
            # Validaciones
            if not data:
                return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
                
            if not data.get('nombre'):
                return jsonify({'success': False, 'message': 'El nombre es requerido'}), 400
                
            if not data.get('tipo'):
                return jsonify({'success': False, 'message': 'El tipo es requerido'}), 400
                
            if data.get('tipo') == 'red' and (not data.get('ip') or not data.get('puerto')):
                return jsonify({'success': False, 'message': 'IP y puerto son requeridos para impresoras de red'}), 400

            # Actualizar impresora
            cursor.execute('''
                UPDATE impresoras 
                SET nombre = %s, tipo = %s, ip = %s, puerto = %s, estatus = %s 
                WHERE id = %s
            ''', (data['nombre'], data['tipo'], data.get('ip'), data.get('puerto'), 
                  data.get('estatus', 'activa'), impresora_id))
            
            # Actualizar grupos asignados
            cursor.execute('DELETE FROM impresora_grupos WHERE impresora_id = %s', (impresora_id,))
            if data.get('grupos'):
                grupos_values = [(impresora_id, grupo_id) for grupo_id in data['grupos']]
                cursor.executemany('''
                    INSERT INTO impresora_grupos (impresora_id, grupo_id) 
                    VALUES (%s, %s)
                ''', grupos_values)
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Impresora actualizada correctamente'})
            
    except Exception as e:
        print("Error en gestión de impresora:", str(e))  # Debug
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/windows_printers')
@login_required
def get_windows_printers():
    """API para obtener la lista de impresoras de Windows"""
    try:
        if platform.system() == 'Windows':
            import win32print
            printers = []
            for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS):
                printers.append(printer[2])  # printer[2] contiene el nombre de la impresora
            return jsonify(printers)
        else:
            # En Linux, devolver lista vacía o usar CUPS
            return jsonify([])
    except Exception as e:
        print("Error al obtener impresoras:", str(e))  # Debug
        return jsonify({'error': str(e)}), 500

@app.route('/api/printer_mappings')
@login_required
def api_printer_mappings():
    """API para obtener las asignaciones de impresoras a grupos."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a BD'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 
                ig.grupo_id,
                g.nombre as grupo_nombre,
                i.id as impresora_id,
                i.nombre as impresora_nombre,
                i.tipo as impresora_tipo,
                i.ip as impresora_ip,
                i.puerto as impresora_puerto
            FROM impresora_grupos ig
            JOIN impresoras i ON ig.impresora_id = i.id
            JOIN grupos g ON ig.grupo_id = g.id
            WHERE i.estatus = 'activa'
        """)
        mappings = cursor.fetchall()

        # Reestructurar los datos para facilitar el uso en el frontend
        formatted_mappings = []
        for row in mappings:
            formatted_mappings.append({
                'grupo_id': row['grupo_id'],
                'grupo_nombre': row['grupo_nombre'],
                'impresora': {
                    'id': row['impresora_id'],
                    'nombre': row['impresora_nombre'],
                    'tipo': row['impresora_tipo'],
                    'ip': row['impresora_ip'],
                    'puerto': row['impresora_puerto']
                }
            })
        
        return jsonify(formatted_mappings)
    except Error as err:
        print(f"Error al obtener asignaciones de impresoras: {str(err)}")
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

def generar_ticket_comanda(mesa_nombre, items, grupo_nombre=None, es_totalizacion=False, servicio='local', usuario_nombre=None):
    # Obtener la fecha y hora actual
    fecha_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    # Inicializar el contenido del ticket
    contenido = []
    
    # Agregar caracteres de inicialización ESC/POS
    contenido.append('\x1B\x40')  # Inicializar impresora
    contenido.append('\x1B\x61\x01')  # Centrar texto
    
    # Encabezado
    contenido.append('SISTEMA DE COMANDAS')
    contenido.append('=' * 48)
    contenido.append(f'Mesa: {mesa_nombre}')
    contenido.append(f'Fecha: {fecha_hora}')
    contenido.append(f'Servicio: {servicio.upper()}')
    if usuario_nombre:
        contenido.append(f'Usuario: {usuario_nombre}')
    if grupo_nombre:
        # Si hay múltiples grupos, mostrarlos en líneas separadas
        if ',' in grupo_nombre:
            grupos = [g.strip() for g in grupo_nombre.split(',')]
            contenido.append(f'Grupos: {grupos[0]}')
            for grupo in grupos[1:]:
                contenido.append(f'        {grupo}')
        else:
            contenido.append(f'Grupo: {grupo_nombre}')
    contenido.append('-' * 48)
    
    # Detalles de la comanda
    contenido.append('\x1B\x61\x00')  # Alinear a la izquierda
    contenido.append('PRODUCTO'.ljust(30) + 'CANT'.rjust(4) + 'PRECIO'.rjust(14))
    contenido.append('-' * 48)
    
    total = 0
    for item in items:
        nombre = item['nombre']
        cantidad = item['cantidad']
        precio = float(item['precio'])
        item_total = cantidad * precio
        total += item_total
        
        # Formatear el nombre para que no exceda 30 caracteres
        if len(nombre) > 30:
            nombre = nombre[:27] + '...'
        
        # Formatear la línea del item
        linea = nombre.ljust(30) + str(cantidad).rjust(4) + f'${precio:.2f}'.rjust(14)
        contenido.append(linea)
        
        # Agregar nota si existe
        if item.get('nota'):
            contenido.append('  Nota: ' + item['nota'])
    
    # Línea separadora
    contenido.append('-' * 48)
    
    # Total
    contenido.append('TOTAL:'.ljust(34) + f'${total:.2f}'.rjust(14))
    
    # Pie del ticket
    contenido.append('=' * 48)
    contenido.append('\x1B\x61\x01')  # Centrar texto
    if es_totalizacion:
        contenido.append('TICKET DE PAGO')
    else:
        contenido.append('TICKET DE COMANDA')
    contenido.append('=' * 48)
    
    # Agregar espacio para el corte
    contenido.append('\n\n')
    
    # Comando de corte de papel (corte completo)
    contenido.append('\x1D\x56\x00')
    
    # Unir todo el contenido con saltos de línea
    return '\n'.join(contenido)

def enviar_a_impresora(texto, ip, puerto):
    """Envía texto a una impresora de red"""
    try:
        import socket
        print(f"DEBUG: Enviando a impresora de red ({ip}:{puerto}):\n{texto}") # Debug
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, int(puerto)))
        s.send(texto.encode('utf-8'))
        s.close()
        return True
    except Exception as e:
        print(f"Error al enviar a impresora de red: {str(e)}")
        return False

def imprimir_en_windows(printer_name, text_content):
    """Envía contenido de texto a una impresora de Windows."""
    try:
        if platform.system() == 'Windows':
            import win32print
            print(f"DEBUG: Enviando a impresora de Windows ({printer_name}):\n{text_content}") # Debug
            hPrinter = win32print.OpenPrinter(printer_name)
            try:
                # Start a print job
                job = win32print.StartDocPrinter(hPrinter, 1, ("Comanda", None, "RAW"))
                win32print.StartPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, text_content.encode('utf-8'))
                win32print.EndPagePrinter(hPrinter)
                win32print.EndDocPrinter(hPrinter)
                print(f"Impresión enviada a {printer_name} exitosamente.")
                return True
            finally:
                win32print.ClosePrinter(hPrinter)
        else:
            # En Linux, usar CUPS o simplemente log
            print(f"DEBUG: Enviando a impresora en Linux ({printer_name}):\n{text_content}")
            # Aquí podrías implementar impresión con CUPS si es necesario
            return True
    except Exception as e:
        print(f"Error al imprimir en impresora {printer_name}: {e}")
        return False

def actualizar_estado_impresion(comanda_id, items_impresos):
    """Actualiza el estado de impresión de los items en la base de datos"""
    try:
        conn = get_db_connection()
        if not conn:
            print("Error: No se pudo conectar a la base de datos")
            return False
            
        cursor = conn.cursor()
        
        # Actualizar cada item impreso
        for item in items_impresos:
            item_id = item.get('item_id')
            cantidad = item.get('cantidad')
            cantidad_impresa = item.get('cantidad_impresa', 0)
            
            # Calcular la nueva cantidad impresa
            nueva_cantidad_impresa = cantidad_impresa + cantidad
            
            # Actualizar el registro en la base de datos
            cursor.execute('''
                UPDATE comanda_detalle 
                SET impreso = NOW(), 
                    estatus = 'impreso',
                    cantidad_impresa = %s
                WHERE comanda_id = %s AND item_id = %s
            ''', (nueva_cantidad_impresa, comanda_id, item_id))
            
        conn.commit()
        return True
        
    except Error as e:
        print(f"Error al actualizar estado de impresión: {str(e)}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/print_ticket', methods=['POST'])
@login_required
def print_ticket():
    try:
        data = request.json
        text_content = data.get('text_content')
        printer_type = data.get('printer_type')
        printer_name = data.get('printer_name')
        ip = data.get('ip')
        puerto = data.get('puerto')
        comanda_id = request.args.get('comanda_id')
        items_impresos = data.get('items_impresos', [])  # Lista de items que se imprimieron
        
        if not text_content:
            return jsonify({
                'success': False,
                'message': 'No se proporcionó contenido para imprimir'
            }), 400
            
        success = False
        if printer_type == 'windows':
            if not printer_name:
                return jsonify({
                    'success': False,
                    'message': 'No se proporcionó nombre de impresora'
                }), 400
            success = imprimir_en_windows(printer_name, text_content)
        elif printer_type == 'red':
            if not ip or not puerto:
                return jsonify({
                    'success': False,
                    'message': 'No se proporcionaron IP o puerto de impresora'
                }), 400
            success = enviar_a_impresora(text_content, ip, puerto)
        else:
            return jsonify({
                'success': False,
                'message': 'Tipo de impresora no válido'
            }), 400
            
        if success:
            # Actualizar el estado de impresión en la base de datos
            if comanda_id and items_impresos:
                if actualizar_estado_impresion(comanda_id, items_impresos):
                    return jsonify({
                        'success': True,
                        'message': 'Ticket impreso y estado actualizado correctamente'
                    })
            else:
                return jsonify({
                    'success': True,
                    'message': 'Ticket impreso correctamente'
                })
        else:
            return jsonify({
                'success': False,
                'message': 'Error al imprimir el ticket'
            }), 500
            
    except Exception as e:
        print("Error en print_ticket:", str(e))
        return jsonify({
            'success': False,
            'message': f'Error al imprimir: {str(e)}'
        }), 500

@app.route('/api/generar_ticket_plain_text', methods=['POST'])
@login_required
def generar_ticket_plain_text_api():
    try:
        data = request.get_json()
        print("Datos recibidos para ticket:", data)  # Debug
        
        mesa_nombre = data.get('mesa_nombre', '')
        items = data.get('items', [])
        grupo_nombre = data.get('grupo_nombre', '')
        es_totalizacion = data.get('es_totalizacion', False)
        servicio = data.get('servicio', 'local')  # Nuevo campo servicio
        
        # Usar el usuario actual de la sesión en lugar del que se pasa desde el frontend
        usuario_nombre = session.get('usuario', {}).get('nombre_completo', 'Usuario no identificado')
        
        # Validar datos
        if not mesa_nombre or not items:
            return jsonify({
                'success': False,
                'message': 'Datos incompletos para generar el ticket'
            }), 400
            
        # Generar el contenido del ticket
        ticket_content = generar_ticket_comanda(
            mesa_nombre=mesa_nombre,
            items=items,
            grupo_nombre=grupo_nombre,
            es_totalizacion=es_totalizacion,
            servicio=servicio,
            usuario_nombre=usuario_nombre
        )
        
        return jsonify({
            'success': True,
            'ticket_content': ticket_content
        })
        
    except Exception as e:
        print("Error generando ticket:", str(e))  # Debug
        return jsonify({
            'success': False,
            'message': f'Error al generar el ticket: {str(e)}'
        }), 500

@app.route('/api/exportar/reporte/<tipo>')
@login_required
def exportar_reporte(tipo):
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        estatus = request.args.get('estatus')
        mesa = request.args.get('mesa')
        usuario = request.args.get('usuario')
        fecha = request.args.get('fecha')
        
        print(f"Filtros recibidos: estatus={estatus}, mesa={mesa}, usuario={usuario}, fecha={fecha}")  # Debug
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500
            
        cursor = conn.cursor(dictionary=True)
        
        try:
            if tipo == 'ventas':
                query = """
                    SELECT p.nombre as item, SUM(d.cantidad) as cantidad, SUM(d.total) as total
                    FROM comanda_detalle d
                    JOIN productos p ON d.producto_id = p.id
                    JOIN comandas c ON d.comanda_id = c.id
                    WHERE c.estatus = 'pagada'
                """
                
                params = []
                if fecha_inicio and fecha_fin:
                    query += " AND c.fecha BETWEEN %s AND %s"
                    params.extend([fecha_inicio, fecha_fin + " 23:59:59"])
                elif fecha_inicio:
                    query += " AND c.fecha >= %s"
                    params.append(fecha_inicio)
                elif fecha_fin:
                    query += " AND c.fecha <= %s"
                    params.append(fecha_fin + " 23:59:59")
                    
                query += " GROUP BY p.nombre ORDER BY total DESC"
                
                print(f"Query ventas: {query}")  # Debug
                print(f"Params ventas: {params}")  # Debug
                
                cursor.execute(query, params)
                items = cursor.fetchall()
                
                # Crear PDF
                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=letter)
                elements = []
                
                # Estilos
                styles = getSampleStyleSheet()
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=16,
                    spaceAfter=30
                )
                
                # Título
                elements.append(Paragraph("Reporte de Ventas por Ítem", title_style))
                elements.append(Paragraph(f"Período: {fecha_inicio or 'Todo'} al {fecha_fin or 'Todo'}", styles['Normal']))
                elements.append(Spacer(1, 20))
                
                # Tabla
                data = [['Ítem', 'Cantidad', 'Total']]
                total_general = 0
                for item in items:
                    data.append([
                        item['item'],
                        str(item['cantidad']),
                        f"${float(item['total']):.2f}"
                    ])
                    total_general += float(item['total'])
                
                data.append(['', 'Total General:', f"${total_general:.2f}"])
                
                table = Table(data, colWidths=[300, 100, 100])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.grey),
                    ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                elements.append(table)
                doc.build(elements)
                
                buffer.seek(0)
                return send_file(
                    buffer,
                    as_attachment=True,
                    download_name=f'reporte_ventas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
                    mimetype='application/pdf'
                )
                
            elif tipo == 'comandas':
                query = """
                    SELECT c.id, m.nombre as mesa_nombre, c.fecha, c.total, c.estatus, 
                           u.nombre_completo as usuario_nombre
                    FROM comandas c
                    JOIN mesas m ON c.mesa_id = m.Id
                    LEFT JOIN usuario u ON c.usuario_id = u.id
                """
                
                where_conditions = []
                params = []
                
                if estatus:
                    where_conditions.append("c.estatus = %s")
                    params.append(estatus)
                if mesa:
                    where_conditions.append("m.nombre = %s")
                    params.append(mesa)
                if usuario:
                    where_conditions.append("u.nombre_completo = %s")
                    params.append(usuario)
                if fecha:
                    where_conditions.append("DATE(c.fecha) = %s")
                    params.append(fecha)
                
                if where_conditions:
                    query += " WHERE " + " AND ".join(where_conditions)
                
                query += " ORDER BY c.fecha DESC"
                
                print(f"Query comandas: {query}")  # Debug
                print(f"Params comandas: {params}")  # Debug
                
                cursor.execute(query, params)
                comandas = cursor.fetchall()
                
                # Crear PDF
                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=letter)
                elements = []
                
                # Estilos
                styles = getSampleStyleSheet()
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=16,
                    spaceAfter=30
                )
                
                # Título
                elements.append(Paragraph("Listado de Comandas", title_style))
                
                # Agregar información de filtros
                filtros = []
                if estatus: filtros.append(f"Estatus: {estatus}")
                if mesa: filtros.append(f"Mesa: {mesa}")
                if usuario: filtros.append(f"Usuario: {usuario}")
                if fecha: filtros.append(f"Fecha: {fecha}")
                
                if filtros:
                    elements.append(Paragraph("Filtros aplicados:", styles['Normal']))
                    for filtro in filtros:
                        elements.append(Paragraph(f"- {filtro}", styles['Normal']))
                
                elements.append(Spacer(1, 20))
                
                # Tabla
                data = [['ID', 'Mesa', 'Fecha', 'Total', 'Estatus', 'Usuario']]
                for comanda in comandas:
                    data.append([
                        str(comanda['id']),
                        comanda['mesa_nombre'],
                        comanda['fecha'].strftime('%Y-%m-%d %H:%M'),
                        f"${float(comanda['total']):.2f}",
                        comanda['estatus'],
                        comanda['usuario_nombre'] or 'N/A'
                    ])
                
                table = Table(data, colWidths=[50, 100, 120, 80, 80, 150])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                elements.append(table)
                doc.build(elements)
                
                buffer.seek(0)
                return send_file(
                    buffer,
                    as_attachment=True,
                    download_name=f'listado_comandas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
                    mimetype='application/pdf'
                )
                
        except Error as e:
            print(f"Error en la consulta SQL: {str(e)}")
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f"Error general en exportar_reporte: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/manager/empresa')
@login_required
def manager_empresa():
    """Gestión de datos de la empresa (admin y soporte)"""
    print(f"=== INICIO manager_empresa ===")  # Debug
    print(f"Session data: {dict(session)}")  # Debug
    print(f"User role: {session.get('rol')}")  # Debug
    
    if session.get('rol') not in ['admin', 'soporte']:
        print(f"Error: Usuario sin permisos - rol: {session.get('rol')}")  # Debug
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect(url_for('manager'))
        
    try:
        print("Conectando a la base de datos...")  # Debug
        conn = get_db_connection()
        if not conn:
            print("Error: No se pudo conectar a la base de datos")  # Debug
            return render_template('partials/empresa.html', empresa=None)
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM empresa LIMIT 1")
        empresa = cursor.fetchone()
        
        print(f"Empresa obtenida: {empresa is not None}")  # Debug
        
        return render_template('partials/empresa.html', empresa=empresa)
        
    except Exception as e:
        print(f"Error en manager_empresa: {str(e)}")  # Debug
        flash(f'Error al cargar datos de la empresa: {str(e)}', 'danger')
        return render_template('partials/empresa.html', empresa=None)
    finally:
        if 'cursor' in locals(): 
            cursor.close()
        if 'conn' in locals(): 
            conn.close()

@app.route('/manager/dashboard')
@login_required
def manager_dashboard():
    """Panel de control para administradores y soporte"""
    print(f"=== INICIO manager_dashboard ===")  # Debug
    print(f"Session data: {dict(session)}")  # Debug
    print(f"User role: {session.get('rol')}")  # Debug
    
    if session.get('rol') not in ['admin', 'soporte']:
        print(f"Error: Usuario sin permisos - rol: {session.get('rol')}")  # Debug
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect(url_for('manager'))
        
    try:
        print("Conectando a la base de datos...")  # Debug
        conn = get_db_connection()
        if not conn:
            print("Error: No se pudo conectar a la base de datos")  # Debug
            return render_template('partials/dashboard.html', 
                                 total_ventas_hoy=0, 
                                 total_ventas_mes=0, 
                                 top_items=[], 
                                 ventas_diarias=[],
                                 total_comandas=0,
                                 comandas_activas=0,
                                 total_items=0,
                                 total_mesas=0,
                                 items_populares=[])
            
        cursor = conn.cursor(dictionary=True)
        
        # Obtener total de ventas de hoy
        cursor.execute("""
            SELECT COALESCE(SUM(total), 0) as total
            FROM comandas
            WHERE DATE(fecha) = CURDATE()
            AND estatus = 'pagada'
        """)
        total_ventas_hoy = cursor.fetchone()['total']
        # Convertir Decimal a float
        if total_ventas_hoy is not None:
            total_ventas_hoy = float(total_ventas_hoy)
        else:
            total_ventas_hoy = 0.0
        
        # Obtener total de ventas del mes
        cursor.execute("""
            SELECT COALESCE(SUM(total), 0) as total
            FROM comandas
            WHERE MONTH(fecha) = MONTH(CURDATE())
            AND YEAR(fecha) = YEAR(CURDATE())
            AND estatus = 'pagada'
        """)
        total_ventas_mes = cursor.fetchone()['total']
        # Convertir Decimal a float
        if total_ventas_mes is not None:
            total_ventas_mes = float(total_ventas_mes)
        else:
            total_ventas_mes = 0.0
        
        # Obtener top 5 items más vendidos
        cursor.execute("""
            SELECT p.nombre, COUNT(*) as cantidad, SUM(cd.cantidad) as total_unidades
            FROM comanda_detalle cd
            JOIN productos p ON cd.producto_id = p.id
            JOIN comandas c ON cd.comanda_id = c.id
            WHERE c.estatus = 'pagada'
            AND MONTH(c.fecha) = MONTH(CURDATE())
            AND YEAR(c.fecha) = YEAR(CURDATE())
            GROUP BY p.id, p.nombre
            ORDER BY total_unidades DESC
            LIMIT 5
        """)
        top_items = cursor.fetchall()
        
        # Convertir Decimal a float en top_items
        for item in top_items:
            if item['total_unidades'] is not None:
                item['total_unidades'] = float(item['total_unidades'])
            else:
                item['total_unidades'] = 0.0
        
        # Obtener ventas diarias del mes actual
        cursor.execute("""
            SELECT DATE(fecha) as fecha, SUM(total) as total
            FROM comandas
            WHERE MONTH(fecha) = MONTH(CURDATE())
            AND YEAR(fecha) = YEAR(CURDATE())
            AND estatus = 'pagada'
            GROUP BY DATE(fecha)
            ORDER BY fecha
        """)
        ventas_diarias = cursor.fetchall()
        
        # Convertir Decimal a float en ventas_diarias
        for venta in ventas_diarias:
            if venta['total'] is not None:
                venta['total'] = float(venta['total'])
            else:
                venta['total'] = 0.0
        
        # Obtener estadísticas adicionales
        cursor.execute("SELECT COUNT(*) as total FROM comandas")
        total_comandas = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as activas FROM comandas WHERE estatus = 'activa'")
        comandas_activas = cursor.fetchone()['activas']
        
        cursor.execute("SELECT COUNT(*) as total FROM productos WHERE estatus = 'activo'")
        total_items = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM mesas WHERE estatus = 'activo'")
        total_mesas = cursor.fetchone()['total']
        
        # Obtener items populares
        cursor.execute("""
            SELECT p.nombre, g.nombre as grupo, COUNT(*) as cantidad
            FROM comanda_detalle cd
            JOIN productos p ON cd.producto_id = p.id
            LEFT JOIN grupos g ON p.grupo_id = g.id
            JOIN comandas c ON cd.comanda_id = c.id
            WHERE c.estatus = 'pagada'
            AND DATE(c.fecha) = CURDATE()
            GROUP BY p.id, p.nombre, g.nombre
            ORDER BY cantidad DESC
            LIMIT 5
        """)
        items_populares = cursor.fetchall()
        
        print(f"Datos obtenidos exitosamente:")  # Debug
        print(f"  total_ventas_hoy: {total_ventas_hoy}")
        print(f"  total_ventas_mes: {total_ventas_mes}")
        print(f"  top_items: {len(top_items)} items")
        print(f"  ventas_diarias: {len(ventas_diarias)} días")
        
        return render_template('partials/dashboard.html', 
                             total_ventas_hoy=total_ventas_hoy,
                             total_ventas_mes=total_ventas_mes,
                             top_items=top_items,
                             ventas_diarias=ventas_diarias,
                             total_comandas=total_comandas,
                             comandas_activas=comandas_activas,
                             total_items=total_items,
                             total_mesas=total_mesas,
                             items_populares=items_populares)
        
    except Exception as e:
        print(f"Error en manager_dashboard: {str(e)}")  # Debug
        flash(f'Error al cargar el dashboard: {str(e)}', 'danger')
        return render_template('partials/dashboard.html', 
                             total_ventas_hoy=0, 
                             total_ventas_mes=0, 
                             top_items=[], 
                             ventas_diarias=[],
                             total_comandas=0,
                             comandas_activas=0,
                             total_items=0,
                             total_mesas=0,
                             items_populares=[])
    finally:
        if 'cursor' in locals(): 
            cursor.close()
        if 'conn' in locals(): 
            conn.close()

@app.route('/api/empresa', methods=['POST'])
@login_required
def actualizar_empresa():
    """API para actualizar datos de la empresa (admin y soporte)"""
    print("=== INICIO actualizar_empresa ===")  # Debug
    print(f"Session data: {session}")  # Debug
    print(f"User role: {session.get('rol')}")  # Debug
    
    if session.get('rol') not in ['admin', 'soporte']:
        print("Error: Usuario sin permisos")  # Debug
        return jsonify({'success': False, 'message': 'No tiene permisos para realizar esta acción'}), 403
        
    try:
        print("Conectando a la base de datos...")  # Debug
        conn = get_db_connection()
        if not conn:
            print("Error: No se pudo conectar a la base de datos")  # Debug
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
            
        cursor = conn.cursor()
        
        # Obtener datos del formulario
        print("Obteniendo datos del formulario...")  # Debug
        nombre_empresa = request.form.get('nombre_empresa')
        rif = request.form.get('rif')
        direccion = request.form.get('direccion')
        
        # Datos de WhatsApp
        whatsapp_api_key = request.form.get('whatsapp_api_key')
        whatsapp_api_url = request.form.get('whatsapp_api_url')
        whatsapp_phone_number = request.form.get('whatsapp_phone_number')
        
        # Manejo del archivo de logo
        logo = request.files.get('logo')
        logo_data = None
        
        if logo and logo.filename:
            print(f"Archivo de logo recibido: {logo.filename}")  # Debug
            print(f"Tipo de archivo: {logo.content_type}")  # Debug
            print(f"Tamaño del archivo: {logo.content_length} bytes")  # Debug
            
            # Validar tipo de archivo
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
            if logo.content_type not in allowed_types:
                return jsonify({'success': False, 'message': 'Solo se permiten archivos de imagen (JPEG, PNG, GIF)'}), 400
            
            # Validar tamaño del archivo (máximo 5MB)
            max_size = 5 * 1024 * 1024  # 5MB
            if logo.content_length and logo.content_length > max_size:
                return jsonify({'success': False, 'message': 'El archivo es demasiado grande. Máximo 5MB'}), 400
            
            try:
                logo_data = logo.read()
                print(f"Logo leído exitosamente: {len(logo_data)} bytes")  # Debug
            except Exception as e:
                print(f"Error al leer el archivo: {str(e)}")  # Debug
                return jsonify({'success': False, 'message': f'Error al procesar el archivo: {str(e)}'}), 400
        else:
            print("No se recibió archivo de logo")  # Debug
        
        print(f"Datos recibidos:")  # Debug
        print(f"  nombre_empresa: {nombre_empresa}")
        print(f"  rif: {rif}")
        print(f"  direccion: {direccion}")
        print(f"  logo_data: {'Sí' if logo_data else 'No'}")
        print(f"  whatsapp_api_key: {whatsapp_api_key}")
        print(f"  whatsapp_api_url: {whatsapp_api_url}")
        print(f"  whatsapp_phone_number: {whatsapp_phone_number}")
        
        # Validaciones básicas
        if not nombre_empresa or not rif or not direccion:
            print("Error: Campos requeridos faltantes")  # Debug
            return jsonify({'success': False, 'message': 'Todos los campos son requeridos'}), 400
            
        # Verificar si ya existe un registro
        print("Verificando si existe registro de empresa...")  # Debug
        cursor.execute("SELECT id FROM empresa LIMIT 1")
        empresa_existente = cursor.fetchone()
        print(f"Empresa existente: {empresa_existente}")  # Debug
        
        try:
            if empresa_existente:
                print("Actualizando registro existente...")  # Debug
                # Actualizar registro existente
                if logo_data:
                    print("Actualizando con logo...")  # Debug
                    cursor.execute("""
                        UPDATE empresa 
                        SET nombre_empresa = %s, rif = %s, direccion = %s, logo = %s,
                            whatsapp_api_key = %s, whatsapp_api_url = %s, whatsapp_phone_number = %s
                        WHERE id = %s
                    """, (nombre_empresa, rif, direccion, logo_data, 
                          whatsapp_api_key, whatsapp_api_url, whatsapp_phone_number,
                          empresa_existente[0]))
                else:
                    print("Actualizando sin logo...")  # Debug
                    cursor.execute("""
                        UPDATE empresa 
                        SET nombre_empresa = %s, rif = %s, direccion = %s,
                            whatsapp_api_key = %s, whatsapp_api_url = %s, whatsapp_phone_number = %s
                        WHERE id = %s
                    """, (nombre_empresa, rif, direccion,
                          whatsapp_api_key, whatsapp_api_url, whatsapp_phone_number,
                          empresa_existente[0]))
            else:
                print("Creando nuevo registro...")  # Debug
                # Crear nuevo registro
                if logo_data:
                    print("Insertando con logo...")  # Debug
                    cursor.execute("""
                        INSERT INTO empresa (nombre_empresa, rif, direccion, logo,
                                           whatsapp_api_key, whatsapp_api_url, whatsapp_phone_number)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (nombre_empresa, rif, direccion, logo_data,
                          whatsapp_api_key, whatsapp_api_url, whatsapp_phone_number))
                else:
                    print("Insertando sin logo...")  # Debug
                    cursor.execute("""
                        INSERT INTO empresa (nombre_empresa, rif, direccion,
                                           whatsapp_api_key, whatsapp_api_url, whatsapp_phone_number)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (nombre_empresa, rif, direccion,
                          whatsapp_api_key, whatsapp_api_url, whatsapp_phone_number))
            
            print("Haciendo commit...")  # Debug
            conn.commit()
            print("Commit exitoso")  # Debug
            
            mensaje = "Datos de la empresa actualizados correctamente"
            if logo_data:
                mensaje += " (incluyendo logo)"
            
            return jsonify({'success': True, 'message': mensaje})
            
        except Exception as e:
            print(f"Error en la operación de base de datos: {str(e)}")  # Debug
            conn.rollback()
            raise e
        
    except Exception as e:
        print(f"Error al actualizar empresa: {str(e)}")  # Debug
        import traceback
        print(f"Traceback completo: {traceback.format_exc()}")  # Debug
        if 'conn' in locals(): conn.rollback()
        return jsonify({'success': False, 'message': f'Error al actualizar datos: {str(e)}'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()
        print("=== FIN actualizar_empresa ===")  # Debug

@app.route('/api/empresa/logo')
@login_required
def obtener_logo_empresa():
    """API para obtener el logo de la empresa (requiere autenticación)"""
    try:
        conn = get_db_connection()
        if not conn:
            print("Error: No se pudo conectar a la base de datos")  # Debug
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
            
        cursor = conn.cursor()
        cursor.execute("SELECT logo FROM empresa LIMIT 1")
        logo = cursor.fetchone()
        
        print(f"Logo encontrado: {logo is not None}")  # Debug
        
        if logo and logo[0]:
            print(f"Tamaño del logo: {len(logo[0])} bytes")  # Debug
            return send_file(
                BytesIO(logo[0]),
                mimetype='image/png',
                as_attachment=False,
                cache_timeout=0  # Deshabilitar caché
            )
        else:
            print("No se encontró logo en la base de datos")  # Debug
            return jsonify({'success': False, 'message': 'No hay logo disponible'}), 404
            
    except Exception as e:
        print(f"Error al obtener logo: {str(e)}")  # Debug
        return jsonify({'success': False, 'message': f'Error al obtener logo: {str(e)}'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/public/empresa/logo')
def obtener_logo_empresa_publico():
    """API para obtener el logo de la empresa (público, sin autenticación)"""
    try:
        conn = get_db_connection()
        if not conn:
            print("Error: No se pudo conectar a la base de datos")  # Debug
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
            
        cursor = conn.cursor()
        cursor.execute("SELECT logo FROM empresa LIMIT 1")
        logo = cursor.fetchone()
        
        print(f"Logo encontrado: {logo is not None}")  # Debug
        
        if logo and logo[0]:
            print(f"Tamaño del logo: {len(logo[0])} bytes")  # Debug
            return send_file(
                BytesIO(logo[0]),
                mimetype='image/png',
                as_attachment=False,
                cache_timeout=0  # Deshabilitar caché
            )
        else:
            print("No se encontró logo en la base de datos")  # Debug
            return jsonify({'success': False, 'message': 'No hay logo disponible'}), 404
            
    except Exception as e:
        print(f"Error al obtener logo: {str(e)}")  # Debug
        return jsonify({'success': False, 'message': f'Error al obtener logo: {str(e)}'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/comandas/<int:comanda_id>/cancelar', methods=['PUT'])
@login_required
def cancelar_comanda(comanda_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Obtener la comanda
            cursor.execute('''
                SELECT mesa_id, estatus 
                FROM comandas 
                WHERE id = %s
            ''', (comanda_id,))
            comanda = cursor.fetchone()
            
            if not comanda:
                return jsonify({'success': False, 'error': 'Comanda no encontrada'}), 404
                
            # Verificar que la comanda no esté ya cancelada o pagada
            if comanda[1] in ['cancelada', 'pagada']:
                return jsonify({'success': False, 'error': 'La comanda ya está cerrada'}), 400
            
            # Actualizar el estado de la comanda a cancelada
            cursor.execute('''
                UPDATE comandas 
                SET estatus = 'cancelada', 
                    fecha_cierre = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (comanda_id,))
            
            # Liberar la mesa
            cursor.execute('''
                UPDATE mesas 
                SET estatus = 'libre' 
                WHERE id = %s
            ''', (comanda[0],))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Comanda cancelada correctamente'})
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/monitor')
@login_required
def monitor():
    """Pantalla de monitor para cocina"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Error de conexión a la base de datos', 'danger')
            return render_template('monitor.html', comandas=[])
            
        cursor = conn.cursor(dictionary=True)
        
        # Obtener comandas pendientes con sus mesas
        cursor.execute("""
            SELECT c.id, c.mesa_id, c.fecha, c.estatus, m.nombre as mesa_nombre
            FROM comandas c
            JOIN mesas m ON c.mesa_id = m.id
            WHERE c.estatus = 'pendiente'
            ORDER BY c.fecha DESC
        """)
        comandas = cursor.fetchall()
        
        # Procesar cada comanda
        comandas_list = []
        for comanda in comandas:
            # Obtener los items de la comanda
            cursor.execute("""
                SELECT cd.id, cd.item_id, cd.cantidad, cd.estatus, i.nombre
                FROM comanda_detalle cd
                JOIN item i ON cd.item_id = i.id
                WHERE cd.comanda_id = %s
                AND cd.estatus IN ('pendiente', 'preparando')
            """, (comanda['id'],))
            items = cursor.fetchall()
            
            # Crear diccionario de comanda
            comanda_dict = {
                'id': comanda['id'],
                'mesa_nombre': comanda['mesa_nombre'],
                'fecha': str(comanda['fecha'])[11:16] if comanda['fecha'] else '',
                'estatus': comanda['estatus'],
                'items': []
            }
            
            # Procesar items
            for item in items:
                item_dict = {
                    'item_id': item['item_id'],
                    'cantidad': item['cantidad'],
                    'nombre': item['nombre'],
                    'estatus': item['estatus'] or 'pendiente'
                }
                comanda_dict['items'].append(item_dict)
            
            # Solo agregar comandas que tengan items
            if comanda_dict['items']:
                comandas_list.append(comanda_dict)
        
        return render_template('monitor.html', comandas=comandas_list)
        
    except Exception as e:
        print(f"Error en monitor: {str(e)}")
        flash('Error al cargar el monitor', 'danger')
        return render_template('monitor.html', comandas=[])
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/comanda/<int:comanda_id>/item/<int:item_id>/estatus', methods=['PUT'])
@login_required
def actualizar_estatus_item(comanda_id, item_id):
    """Actualiza el estatus de un item en una comanda"""
    try:
        data = request.get_json()
        if not data or 'estatus' not in data:
            return jsonify({'success': False, 'message': 'Estatus no proporcionado'}), 400
            
        nuevo_estatus = data['estatus']
        if nuevo_estatus not in ['pendiente', 'preparando', 'terminado']:
            return jsonify({'success': False, 'message': 'Estatus inválido'}), 400
            
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
            
        cursor = conn.cursor()
        
        # Actualizar el estatus del item
        cursor.execute("""
            UPDATE comanda_detalle 
            SET estatus = %s 
            WHERE comanda_id = %s AND item_id = %s
        """, (nuevo_estatus, comanda_id, item_id))
        
        # Verificar si se actualizó algún registro
        if cursor.rowcount == 0:
            conn.rollback()
            return jsonify({'success': False, 'message': 'Item no encontrado'}), 404
            
        # Verificar si todos los items están terminados
        cursor.execute("""
            SELECT COUNT(*) as total, 
                   SUM(CASE WHEN estatus = 'terminado' THEN 1 ELSE 0 END) as terminados
            FROM comanda_detalle 
            WHERE comanda_id = %s
        """, (comanda_id,))
        result = cursor.fetchone()
        
        # Si todos los items están terminados, actualizar el estatus de la comanda
        if result and result[0] > 0 and result[0] == result[1]:
            cursor.execute("""
                UPDATE comandas 
                SET estatus = 'terminado' 
                WHERE id = %s
            """, (comanda_id,))
        
        conn.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error al actualizar estatus: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()



@app.route('/manager/backup')
@login_required
@soporte_required
def manager_backup():
    """Gestión de respaldo de base de datos (solo soporte)"""
    return render_template('partials/backup.html')

@app.route('/api/backup', methods=['POST'])
@login_required
@soporte_required
def crear_backup():
    """API para crear respaldo de base de datos"""
    try:
        # Obtener la fecha y hora actual
        fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Crear el nombre del archivo de respaldo
        backup_file = f'backup_{fecha}.sql'
        
        # Obtener la configuración de la base de datos
        db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'comandas'
        }
        
        # Crear el comando mysqldump
        command = [
            'mysqldump',
            f'--host={db_config["host"]}',
            f'--user={db_config["user"]}',
            f'--password={db_config["password"]}',
            db_config['database']
        ]
        
        # Ejecutar el comando y guardar la salida en el archivo
        with open(backup_file, 'w') as f:
            subprocess.run(command, stdout=f, stderr=subprocess.PIPE)
        
        return jsonify({
            'success': True,
            'message': 'Respaldo creado exitosamente',
            'file': backup_file
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error al crear el respaldo: {str(e)}'
        }), 500

@app.route('/manager/actualizar-estructura')
@login_required
@soporte_required
def manager_actualizar_estructura():
    """Gestión de actualización de estructura de base de datos (solo soporte)"""
    return render_template('partials/actualizar_estructura.html')

@app.route('/api/actualizar-estructura', methods=['POST'])
@login_required
@soporte_required
def actualizar_estructura():
    """API para actualizar la estructura de la base de datos"""
    try:
        # Obtener la carpeta seleccionada
        carpeta = request.form.get('carpeta')
        if not carpeta:
            return jsonify({
                'success': False,
                'message': 'Debe seleccionar una carpeta'
            }), 400
            
        # Obtener la configuración de la base de datos
        db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'comandas'
        }
        
        # Crear el comando mysql
        command = [
            'mysql',
            f'--host={db_config["host"]}',
            f'--user={db_config["user"]}',
            f'--password={db_config["password"]}',
            db_config['database']
        ]
        
        # Ejecutar el comando
        subprocess.run(command, stderr=subprocess.PIPE)
        
        return jsonify({
            'success': True,
            'message': 'Estructura actualizada exitosamente'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error al actualizar la estructura: {str(e)}'
        }), 500

@app.route('/api/seleccionar-carpeta', methods=['POST'])
@login_required
@soporte_required
def seleccionar_carpeta():
    """API para seleccionar una carpeta"""
    try:
        # Obtener la carpeta seleccionada
        carpeta = request.form.get('carpeta')
        if not carpeta:
            return jsonify({
                'success': False,
                'message': 'Debe seleccionar una carpera'
            }), 400
            
        return jsonify({
            'success': True,
            'message': 'Carpeta seleccionada exitosamente',
            'carpeta': carpeta
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error al seleccionar la carpeta: {str(e)}'
        }), 500

@app.route('/manager/crear-base-datos')
@login_required
@soporte_required
def manager_crear_base_datos():
    """Gestión de creación de base de datos (solo soporte)"""
    return render_template('partials/crear_base_datos.html')

@app.route('/api/crear-base-datos', methods=['POST'])
@login_required
@soporte_required
def crear_base_datos():
    """API para crear la base de datos"""
    try:
        # Obtener datos del formulario
        host = request.form.get('host', 'localhost')
        port = request.form.get('port', '3306')
        user = request.form.get('user')
        password = request.form.get('password')
        database = request.form.get('database')
        
        if not all([user, password, database]):
            return jsonify({'success': False, 'message': 'Todos los campos son requeridos'}), 400
            
        # Intentar conectar al servidor MySQL
        try:
            conn = mysql.connector.connect(
                host=host,
                port=port,
                user=user,
                password=password
            )
            cursor = conn.cursor()
            
            # Crear la base de datos si no existe
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
            
            # Seleccionar la base de datos
            cursor.execute(f"USE {database}")
            
            # Crear las tablas necesarias
            # Tabla de usuarios
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuario (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user VARCHAR(50) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    nombre_completo VARCHAR(100) NOT NULL,
                    rol ENUM('admin', 'soporte', 'mesero') NOT NULL,
                    estatus ENUM('activo', 'inactivo') DEFAULT 'activo'
                )
            """)
            
            # Tabla de empresa
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS empresa (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre_empresa VARCHAR(100) NOT NULL,
                    rif VARCHAR(20) NOT NULL,
                    direccion TEXT,
                    logo LONGBLOB,
                    whatsapp_api_key VARCHAR(255),
                    whatsapp_api_url VARCHAR(255),
                    whatsapp_phone_number VARCHAR(20)
                )
            """)
            
            # Tabla de grupos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS grupos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(50) NOT NULL,
                    estatus ENUM('activo', 'inactivo') DEFAULT 'activo'
                )
            """)
            
            # Tabla de items
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS item (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL,
                    precio DECIMAL(10,2) NOT NULL,
                    existencia INT DEFAULT 0,
                    grupo_codigo INT,
                    estatus ENUM('activo', 'inactivo') DEFAULT 'activo',
                    FOREIGN KEY (grupo_codigo) REFERENCES grupos(id)
                )
            """)
            
            # Tabla de mesas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mesas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(50) NOT NULL,
                    estatus ENUM('activa', 'inactiva') DEFAULT 'activa'
                )
            """)
            
            # Tabla de comandas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comandas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    mesa_id INT,
                    usuario_id INT,
                    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                    total DECIMAL(10,2) DEFAULT 0,
                    servicio ENUM('local', 'delivery') DEFAULT 'local',
                    estatus ENUM('pendiente', 'pagada', 'cancelada') DEFAULT 'pendiente',
                    FOREIGN KEY (mesa_id) REFERENCES mesas(id),
                    FOREIGN KEY (usuario_id) REFERENCES usuario(id)
                )
            """)
            
            # Tabla de items de comanda
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comanda_detalle (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    comanda_id INT,
                    item_id INT,
                    cantidad INT NOT NULL,
                    precio_unitario DECIMAL(10,2) NOT NULL,
                    total DECIMAL(10,2) NOT NULL,
                    nota TEXT,
                    impreso DATETIME NULL,
                    cantidad_impresa INT DEFAULT 0,
                    estatus ENUM('pendiente', 'preparando', 'terminado') DEFAULT 'pendiente',
                    FOREIGN KEY (comanda_id) REFERENCES comandas(id),
                    FOREIGN KEY (item_id) REFERENCES item(id)
                )
            """)
            
            # Tabla de impresoras
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS impresoras (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL,
                    tipo ENUM('windows', 'red') NOT NULL,
                    ip VARCHAR(15),
                    puerto INT,
                    estatus ENUM('activa', 'inactiva') DEFAULT 'activa'
                )
            """)
            
            # Tabla de relación impresora-grupos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS impresora_grupos (
                    impresora_id INT,
                    grupo_id INT,
                    PRIMARY KEY (impresora_id, grupo_id),
                    FOREIGN KEY (impresora_id) REFERENCES impresoras(id),
                    FOREIGN KEY (grupo_id) REFERENCES grupos(id)
                )
            """)
            
            # Tabla de productos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL,
                    cantidad_disponible DECIMAL(10,2) DEFAULT 0,
                    unidad_medida VARCHAR(20) NOT NULL,
                    estatus ENUM('activo', 'inactivo') DEFAULT 'activo'
                )
            """)
            
            # Tabla de movimientos de inventario
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS movimientos_inventario (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    producto_id INT,
                    tipo ENUM('entrada', 'salida') NOT NULL,
                    cantidad DECIMAL(10,2) NOT NULL,
                    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (producto_id) REFERENCES productos(id)
                )
            """)
            
            # Crear usuario administrador por defecto
            cursor.execute("""
                INSERT INTO usuario (user, password, nombre_completo, rol)
                VALUES ('admin', 'admin123', 'Administrador', 'admin')
            """)
            
            conn.commit()
            return jsonify({
                'success': True, 
                'message': 'Base de datos creada exitosamente'
            })
            
        except mysql.connector.Error as err:
            return jsonify({
                'success': False, 
                'message': f'Error al crear la base de datos: {str(err)}'
            }), 500
        finally:
            if 'cursor' in locals(): cursor.close()
            if 'conn' in locals(): conn.close()
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Error inesperado: {str(e)}'
        }), 500

@app.route('/api/actualizar-estructura-comandas', methods=['POST'])
@login_required
@soporte_required
def actualizar_estructura_comandas():
    """API para actualizar la estructura de la tabla comandas"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Error de conexión a la base de datos'
            }), 500
            
        cursor = conn.cursor()
        
        try:
            cambios_realizados = []
            
            # Verificar si existe el campo cliente_id
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'comandas' 
                AND COLUMN_NAME = 'cliente_id'
            """)
            
            if not cursor.fetchone():
                # Agregar el campo cliente_id
                cursor.execute("""
                    ALTER TABLE comandas 
                    ADD COLUMN cliente_id INT,
                    ADD FOREIGN KEY (cliente_id) REFERENCES clientes(id)
                """)
                cambios_realizados.append("campo cliente_id agregado")
            
            # Verificar si existe el campo empresa_id
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'comandas' 
                AND COLUMN_NAME = 'empresa_id'
            """)
            
            if not cursor.fetchone():
                # Agregar el campo empresa_id
                cursor.execute("""
                    ALTER TABLE comandas 
                    ADD COLUMN empresa_id INT,
                    ADD FOREIGN KEY (empresa_id) REFERENCES empresa(id) ON DELETE CASCADE
                """)
                cambios_realizados.append("campo empresa_id agregado")
            
            # Verificar si existe el campo usuario_id
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'comandas' 
                AND COLUMN_NAME = 'usuario_id'
            """)
            
            if not cursor.fetchone():
                # Agregar el campo usuario_id
                cursor.execute("""
                    ALTER TABLE comandas 
                    ADD COLUMN usuario_id INT,
                    ADD COLUMN servicio ENUM('local', 'delivery') DEFAULT 'local',
                    ADD FOREIGN KEY (usuario_id) REFERENCES usuario(id)
                """)
                cambios_realizados.append("campo usuario_id y servicio agregados")
            
            conn.commit()
            
            if cambios_realizados:
                return jsonify({
                    'success': True,
                    'message': f'Estructura de comandas actualizada correctamente - {", ".join(cambios_realizados)}'
                })
            else:
                return jsonify({
                    'success': True,
                    'message': 'La estructura ya está actualizada'
                })
                
        except Exception as e:
            conn.rollback()
            return jsonify({
                'success': False,
                'message': f'Error al actualizar estructura: {str(e)}'
            }), 500
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error inesperado: {str(e)}'
        }), 500

@app.route('/api/verificar-estructura-comandas')
@login_required
@soporte_required
def verificar_estructura_comandas():
    """API para verificar la estructura de la tabla comandas"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Error de conexión a la base de datos'
            }), 500
            
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Verificar estructura de la tabla comandas
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'comandas'
                ORDER BY ORDINAL_POSITION
            """)
            columnas = cursor.fetchall()
            
            # Verificar si existe el campo cliente_id
            tiene_cliente_id = any(col['COLUMN_NAME'] == 'cliente_id' for col in columnas)
            
            # Verificar foreign keys
            cursor.execute("""
                SELECT 
                    CONSTRAINT_NAME,
                    COLUMN_NAME,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'comandas'
                AND REFERENCED_TABLE_NAME IS NOT NULL
            """)
            foreign_keys = cursor.fetchall()
            
            # Verificar datos de ejemplo
            cursor.execute("""
                SELECT c.id, c.mesa_id, c.usuario_id, c.servicio, c.cliente_id,
                       m.nombre as mesa_nombre, u.nombre_completo as usuario_nombre,
                       cl.nombre as cliente_nombre
                FROM comandas c
                LEFT JOIN mesas m ON c.mesa_id = m.id
                LEFT JOIN usuario u ON c.usuario_id = u.id
                LEFT JOIN clientes cl ON c.cliente_id = cl.id
                ORDER BY c.id DESC
                LIMIT 5
            """)
            comandas_ejemplo = cursor.fetchall()
            
            return jsonify({
                'success': True,
                'columnas': columnas,
                'foreign_keys': foreign_keys,
                'comandas_ejemplo': comandas_ejemplo,
                'tiene_cliente_id': tiene_cliente_id
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error al verificar estructura: {str(e)}'
            }), 500
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error inesperado: {str(e)}'
        }), 500

@app.route('/api/limpiar-registros-problematicos', methods=['POST'])
@login_required
@soporte_required
def limpiar_registros_problematicos():
    """API para limpiar registros problemáticos en la base de datos"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Error de conexión a la base de datos'
            }), 500
            
        cursor = conn.cursor()
        
        try:
            # Limpiar registros con impreso vacío
            cursor.execute("UPDATE comanda_detalle SET impreso = NULL WHERE impreso = ''")
            registros_limpiados = cursor.rowcount
            
            # Verificar si hay comandas sin usuario_id
            cursor.execute("SELECT COUNT(*) FROM comandas WHERE usuario_id IS NULL")
            comandas_sin_usuario = cursor.fetchone()[0]
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': f'Limpieza completada. {registros_limpiados} registros de impreso corregidos. {comandas_sin_usuario} comandas sin usuario.',
                'registros_limpiados': registros_limpiados,
                'comandas_sin_usuario': comandas_sin_usuario
            })
                
        except Exception as e:
            conn.rollback()
            return jsonify({
                'success': False,
                'message': f'Error al limpiar registros: {str(e)}'
            }), 500
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error inesperado: {str(e)}'
        }), 500

@app.route('/test/empresa')
def test_empresa():
    """Página de prueba para el formulario de empresa"""
    return send_file('test_empresa.html')

@app.route('/test/db')
def test_db():
    """Página de prueba para verificar la conexión a la base de datos"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'No se pudo conectar a la base de datos'})
            
        cursor = conn.cursor()
        
        # Verificar si la tabla empresa existe
        cursor.execute("SHOW TABLES LIKE 'empresa'")
        tabla_existe = cursor.fetchone()
        
        # Verificar datos en la tabla empresa
        cursor.execute("SELECT COUNT(*) FROM empresa")
        total_registros = cursor.fetchone()[0]
        
        # Obtener un registro de ejemplo
        cursor.execute("SELECT id, nombre_empresa, rif FROM empresa LIMIT 1")
        registro = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Conexión exitosa',
            'tabla_empresa_existe': tabla_existe is not None,
            'total_registros': total_registros,
            'registro_ejemplo': registro
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@app.route('/test/empresa-archivo')
def test_empresa_archivo():
    """Página de prueba para el formulario de empresa con archivos"""
    return send_file('test_empresa_archivo.html')

@app.route('/test/ventas')
@login_required
@admin_required
def test_ventas():
    """Ruta de prueba para diagnosticar ventas"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'No se pudo conectar a la base de datos'})
            
        cursor = conn.cursor(dictionary=True)
        
        # Verificar datos básicos
        cursor.execute("SELECT COUNT(*) as total FROM comandas")
        total_comandas = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM comanda_detalle")
        total_detalles = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM productos")
        total_items = cursor.fetchone()['total']
        
        cursor.execute("SELECT estatus, COUNT(*) as cantidad FROM comandas GROUP BY estatus")
        estatus_comandas = cursor.fetchall()
        
        # Verificar comandas pagadas
        cursor.execute("SELECT COUNT(*) as total FROM comandas WHERE estatus = 'pagada'")
        comandas_pagadas = cursor.fetchone()['total']
        
        # Probar la consulta de ventas
        cursor.execute("""
            SELECT p.nombre as item, SUM(d.cantidad) as cantidad, SUM(d.total) as total
            FROM comanda_detalle d
            JOIN productos p ON d.producto_id = p.id
            JOIN comandas c ON d.comanda_id = c.id
            WHERE c.estatus = 'pagada'
            GROUP BY p.nombre 
            ORDER BY total DESC
        """)
        ventas_resultado = cursor.fetchall()
        
        # Verificar algunas comandas recientes
        cursor.execute("""
            SELECT c.id, c.estatus, c.fecha, c.total, COUNT(cd.id) as detalles
            FROM comandas c
            LEFT JOIN comanda_detalle cd ON c.id = cd.comanda_id
            GROUP BY c.id, c.estatus, c.fecha, c.total
            ORDER BY c.fecha DESC
            LIMIT 5
        """)
        comandas_recientes = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'total_comandas': total_comandas,
            'total_detalles': total_detalles,
            'total_items': total_items,
            'estatus_comandas': estatus_comandas,
            'comandas_pagadas': comandas_pagadas,
            'ventas_resultado': ventas_resultado,
            'comandas_recientes': comandas_recientes
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/test/ventas-pagina')
def test_ventas_pagina():
    """Página de prueba para diagnosticar ventas"""
    return send_file('test_ventas.html')

# ======================
# RUTAS PARA INVENTARIO COMPLETO
# ======================

@app.route('/manager/inventario/productos')
@login_required
@admin_required
def manager_inventario_productos():
    """Gestión de productos del inventario"""
    try:
        conn = get_db_connection()
        if not conn:
            return render_template('partials/inventario_productos.html', productos=[])
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, nombre, cantidad_disponible, unidad_medida, estatus, 
                   es_receta, costo, ganancia, precio_venta
            FROM productos
            WHERE empresa_id = %s
            ORDER BY nombre
        """, (session.get('empresa_id'),))
        productos = cursor.fetchall()
        
        # Convertir Decimal a float
        for producto in productos:
            producto['cantidad_disponible'] = float(producto['cantidad_disponible'])
            producto['costo'] = float(producto['costo']) if producto['costo'] else 0.0
            producto['ganancia'] = float(producto['ganancia']) if producto['ganancia'] else 0.0
            producto['precio_venta'] = float(producto['precio_venta']) if producto['precio_venta'] else 0.0
        
        return render_template('partials/inventario_productos.html', productos=productos)
        
    except Error as e:
        flash(f'Error al cargar productos: {str(e)}', 'danger')
        return render_template('partials/inventario_productos.html', productos=[])
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/formulario/inventario/producto')
@login_required
@admin_required
def formulario_producto_inventario():
    """Formulario para crear/editar producto del inventario"""
    producto_id = request.args.get('id')
    producto = None
    
    try:
        conn = get_db_connection()
        if not conn:
            return render_template('partials/form_producto_inventario.html', producto=None, grupos=[])
            
        cursor = conn.cursor(dictionary=True)
        
        # Obtener grupos para el select
        cursor.execute("""
            SELECT id, nombre 
            FROM grupos 
            WHERE empresa_id = %s AND estatus = 'activo' 
            ORDER BY nombre
        """, (session.get('empresa_id'),))
        grupos = cursor.fetchall()
        
        if producto_id:
            cursor.execute("SELECT * FROM productos WHERE id = %s AND empresa_id = %s", (producto_id, session.get('empresa_id')))
            producto = cursor.fetchone()
            
            if producto:
                producto['cantidad_disponible'] = float(producto['cantidad_disponible'])
                producto['costo'] = float(producto['costo']) if producto['costo'] else 0.0
                producto['ganancia'] = float(producto['ganancia']) if producto['ganancia'] else 0.0
                producto['precio_venta'] = float(producto['precio_venta']) if producto['precio_venta'] else 0.0
        
        return render_template('partials/form_producto_inventario.html', producto=producto, grupos=grupos)
        
    except Exception as e:
        flash(f'Error al cargar formulario: {str(e)}', 'danger')
        return render_template('partials/form_producto_inventario.html', producto=None, grupos=[])
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/inventario/productos', methods=['POST'])
@login_required
@admin_required
def crear_producto_inventario():
    """API para crear nuevo producto en inventario"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        data = request.get_json()
        
        # Validaciones
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
            
        if not data.get('nombre'):
            return jsonify({'success': False, 'message': 'El nombre es requerido'}), 400
            
        if not data.get('unidad_medida'):
            return jsonify({'success': False, 'message': 'La unidad de medida es requerida'}), 400
            
        if data.get('cantidad_disponible') is None or float(data.get('cantidad_disponible', -1)) < 0:
            return jsonify({'success': False, 'message': 'La cantidad no puede ser negativa'}), 400
            
        if data.get('costo') is None or float(data.get('costo', -1)) < 0:
            return jsonify({'success': False, 'message': 'El costo no puede ser negativo'}), 400
            
        if data.get('ganancia') is None or float(data.get('ganancia', -1)) < 0:
            return jsonify({'success': False, 'message': 'La ganancia no puede ser negativa'}), 400
            
        if data.get('precio_venta') is None or float(data.get('precio_venta', -1)) < 0:
            return jsonify({'success': False, 'message': 'El precio de venta no puede ser negativo'}), 400

        # Insertar nuevo producto
        cursor.execute('''
            INSERT INTO productos (nombre, cantidad_disponible, unidad_medida, estatus, 
                                 es_receta, costo, ganancia, precio_venta, empresa_id, grupo_id, es_para_comandar) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (data['nombre'], data['cantidad_disponible'], data['unidad_medida'], 
              data.get('estatus', 'activo'), data.get('es_receta', 'no'),
              data['costo'], data['ganancia'], data['precio_venta'], 
              session.get('empresa_id'), data.get('grupo_id'), data.get('es_para_comandar', 'no')))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Producto creado correctamente'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error al crear el producto: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/inventario/productos/<int:producto_id>', methods=['PUT', 'DELETE'])
@login_required
@admin_required
def gestion_producto_inventario(producto_id):
    """API para gestionar productos del inventario"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if request.method == 'PUT':
            data = request.get_json()
            
            # Validaciones
            if not data:
                return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
                
            if not data.get('nombre'):
                return jsonify({'success': False, 'message': 'El nombre es requerido'}), 400
                
            if not data.get('unidad_medida'):
                return jsonify({'success': False, 'message': 'La unidad de medida es requerida'}), 400
                
            if data.get('cantidad_disponible') is None or float(data.get('cantidad_disponible', -1)) < 0:
                return jsonify({'success': False, 'message': 'La cantidad no puede ser negativa'}), 400
                
            if data.get('costo') is None or float(data.get('costo', -1)) < 0:
                return jsonify({'success': False, 'message': 'El costo no puede ser negativo'}), 400
                
            if data.get('ganancia') is None or float(data.get('ganancia', -1)) < 0:
                return jsonify({'success': False, 'message': 'La ganancia no puede ser negativa'}), 400
                
            if data.get('precio_venta') is None or float(data.get('precio_venta', -1)) < 0:
                return jsonify({'success': False, 'message': 'El precio de venta no puede ser negativo'}), 400

            # Verificar si el producto existe y pertenece a la empresa
            cursor.execute('SELECT id FROM productos WHERE id = %s AND empresa_id = %s', (producto_id, session.get('empresa_id')))
            if not cursor.fetchone():
                return jsonify({'success': False, 'message': 'El producto no existe o no pertenece a su empresa'}), 404

            # Actualizar producto
            cursor.execute('''
                UPDATE productos 
                SET nombre = %s, cantidad_disponible = %s, unidad_medida = %s, estatus = %s,
                    es_receta = %s, costo = %s, ganancia = %s, precio_venta = %s, grupo_id = %s, es_para_comandar = %s
                WHERE id = %s AND empresa_id = %s
            ''', (data['nombre'], data['cantidad_disponible'], data['unidad_medida'], 
                  data.get('estatus', 'activo'), data.get('es_receta', 'no'),
                  data['costo'], data['ganancia'], data['precio_venta'], 
                  data.get('grupo_id'), data.get('es_para_comandar', 'no'), producto_id, session.get('empresa_id')))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Producto actualizado correctamente'})

        elif request.method == 'DELETE':
            # Verificar si el producto existe y pertenece a la empresa
            cursor.execute('SELECT id FROM productos WHERE id = %s AND empresa_id = %s', (producto_id, session.get('empresa_id')))
            if not cursor.fetchone():
                return jsonify({'success': False, 'message': 'El producto no existe o no pertenece a su empresa'}), 404

            # Verificar si el producto está en uso
            cursor.execute('''
                SELECT COUNT(*) FROM receta_ingredientes 
                WHERE producto_id = %s
            ''', (producto_id,))
            if cursor.fetchone()[0] > 0:
                return jsonify({'success': False, 'message': 'No se puede eliminar, el producto está en uso en recetas'}), 400

            cursor.execute('DELETE FROM productos WHERE id = %s AND empresa_id = %s', (producto_id, session.get('empresa_id')))
            conn.commit()
            return jsonify({'success': True, 'message': 'Producto eliminado correctamente'})

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error en la operación: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/manager/inventario/compras')
@login_required
@admin_required
def manager_inventario_compras():
    """Gestión de compras del inventario"""
    try:
        conn = get_db_connection()
        if not conn:
            return render_template('partials/inventario_compras.html', compras=[])
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.id, c.proveedor, DATE_FORMAT(c.fecha, '%Y-%m-%d') as fecha, c.total 
            FROM compras c
            ORDER BY c.fecha DESC
        """)
        compras = cursor.fetchall()
        
        # Convertir Decimal a float
        for compra in compras:
            compra['total'] = float(compra['total'])
        
        return render_template('partials/inventario_compras.html', compras=compras)
        
    except Error as e:
        flash(f'Error al cargar compras: {str(e)}', 'danger')
        return render_template('partials/inventario_compras.html', compras=[])
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/formulario/inventario/compra')
@login_required
@admin_required
def formulario_compra_inventario():
    """Formulario para crear nueva compra"""
    return render_template('partials/form_compra_inventario.html')

@app.route('/api/inventario/compras', methods=['POST'])
@login_required
@admin_required
def crear_compra_inventario():
    """API para crear nueva compra"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        data = request.get_json()
        
        # Validaciones
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
            
        if not data.get('proveedor'):
            return jsonify({'success': False, 'message': 'El proveedor es requerido'}), 400
            
        if not data.get('fecha'):
            return jsonify({'success': False, 'message': 'La fecha es requerida'}), 400
            
        if not data.get('items') or len(data['items']) == 0:
            return jsonify({'success': False, 'message': 'Debe agregar al menos un item'}), 400

        # Calcular total
        total = sum(item['cantidad'] * item['precio'] for item in data['items'])

        # Insertar compra
        cursor.execute('''
            INSERT INTO compras (proveedor, fecha, total) 
            VALUES (%s, %s, %s)
        ''', (data['proveedor'], data['fecha'], total))
        
        compra_id = cursor.lastrowid
        
        # Insertar items de la compra
        for item in data['items']:
            cursor.execute('''
                INSERT INTO compra_detalles (compra_id, producto_id, cantidad, precio_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            ''', (compra_id, item['producto_id'], item['cantidad'], 
                  item['precio'], item['cantidad'] * item['precio']))
            
            # Actualizar stock del producto
            cursor.execute('''
                UPDATE productos 
                SET cantidad_disponible = cantidad_disponible + %s 
                WHERE id = %s
            ''', (item['cantidad'], item['producto_id']))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Compra creada correctamente'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error al crear la compra: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/inventario/productos/buscar')
@login_required
@admin_required
def buscar_productos_compra():
    """API para buscar productos para compras"""
    busqueda = request.args.get('busqueda', '')
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
            
        cursor = conn.cursor(dictionary=True)
        
        if busqueda.strip():
            cursor.execute("""
                SELECT id, nombre, unidad_medida, cantidad_disponible, costo
                FROM productos 
                WHERE nombre LIKE %s AND estatus = 'activo' AND empresa_id = %s
                ORDER BY nombre
                LIMIT 20
            """, (f"%{busqueda}%", session.get('empresa_id')))
        else:
            cursor.execute("""
                SELECT id, nombre, unidad_medida, cantidad_disponible, costo
                FROM productos 
                WHERE estatus = 'activo' AND empresa_id = %s
                ORDER BY nombre
                LIMIT 20
            """, (session.get('empresa_id'),))
        
        productos = cursor.fetchall()
        
        # Convertir Decimal a float
        for producto in productos:
            producto['cantidad_disponible'] = float(producto['cantidad_disponible'])
            producto['costo'] = float(producto['costo']) if producto['costo'] else 0.0
        
        return jsonify({'success': True, 'productos': productos})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/manager/inventario/recetas')
@login_required
@admin_required
def manager_inventario_recetas():
    """Gestión de recetas del inventario"""
    try:
        conn = get_db_connection()
        if not conn:
            return render_template('partials/inventario_recetas.html', recetas=[])
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT r.id, p.nombre as producto_nombre, r.unidad_producida
            FROM recetas r
            JOIN productos p ON r.producto_id = p.id
            ORDER BY p.nombre
        """)
        recetas = cursor.fetchall()
        
        return render_template('partials/inventario_recetas.html', recetas=recetas)
        
    except Error as e:
        flash(f'Error al cargar recetas: {str(e)}', 'danger')
        return render_template('partials/inventario_recetas.html', recetas=[])
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/formulario/inventario/receta')
@login_required
@admin_required
def formulario_receta_inventario():
    """Formulario para crear nueva receta"""
    return render_template('partials/form_receta_inventario.html')

@app.route('/api/inventario/recetas', methods=['POST'])
@login_required
@admin_required
def crear_receta_inventario():
    """API para crear nueva receta"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        data = request.get_json()
        
        # Validaciones
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
            
        if not data.get('producto_id'):
            return jsonify({'success': False, 'message': 'El producto es requerido'}), 400
            
        if not data.get('unidad_producida'):
            return jsonify({'success': False, 'message': 'La unidad producida es requerida'}), 400
            
        if not data.get('ingredientes') or len(data['ingredientes']) == 0:
            return jsonify({'success': False, 'message': 'Debe agregar al menos un ingrediente'}), 400

        # Verificar que el producto no tenga ya una receta
        cursor.execute('SELECT id FROM recetas WHERE producto_id = %s', (data['producto_id'],))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Este producto ya tiene una receta asignada'}), 400

        # Insertar receta
        cursor.execute('''
            INSERT INTO recetas (producto_id, unidad_producida) 
            VALUES (%s, %s)
        ''', (data['producto_id'], data['unidad_producida']))
        
        receta_id = cursor.lastrowid
        
        # Insertar ingredientes
        for ingrediente in data['ingredientes']:
            cursor.execute('''
                INSERT INTO receta_ingredientes (receta_id, producto_id, cantidad)
                VALUES (%s, %s, %s)
            ''', (receta_id, ingrediente['producto_id'], ingrediente['cantidad']))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Receta creada correctamente'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error al crear la receta: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/inventario/recetas/<int:receta_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@admin_required
def gestion_receta_inventario(receta_id):
    """API para gestionar recetas"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if request.method == 'GET':
            # Obtener receta con ingredientes
            cursor.execute("""
                SELECT r.id, r.producto_id, r.unidad_producida, p.nombre as producto_nombre
                FROM recetas r
                JOIN productos p ON r.producto_id = p.id
                WHERE r.id = %s
            """, (receta_id,))
            receta = cursor.fetchone()
            
            if not receta:
                return jsonify({'success': False, 'message': 'Receta no encontrada'}), 404
            
            # Obtener ingredientes
            cursor.execute("""
                SELECT ri.producto_id, ri.cantidad, p.nombre as producto_nombre, p.unidad_medida
                FROM receta_ingredientes ri
                JOIN productos p ON ri.producto_id = p.id
                WHERE ri.receta_id = %s
            """, (receta_id,))
            ingredientes = cursor.fetchall()
            
            # Convertir Decimal a float
            for ingrediente in ingredientes:
                ingrediente['cantidad'] = float(ingrediente['cantidad'])
            
            return jsonify({
                'success': True, 
                'receta': receta, 
                'ingredientes': ingredientes
            })
            
        elif request.method == 'PUT':
            data = request.get_json()
            
            # Validaciones
            if not data:
                return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
                
            if not data.get('unidad_producida'):
                return jsonify({'success': False, 'message': 'La unidad producida es requerida'}), 400
                
            if not data.get('ingredientes') or len(data['ingredientes']) == 0:
                return jsonify({'success': False, 'message': 'Debe agregar al menos un ingrediente'}), 400

            # Actualizar receta
            cursor.execute('''
                UPDATE recetas 
                SET unidad_producida = %s 
                WHERE id = %s
            ''', (data['unidad_producida'], receta_id))
            
            # Eliminar ingredientes existentes
            cursor.execute('DELETE FROM receta_ingredientes WHERE receta_id = %s', (receta_id,))
            
            # Insertar nuevos ingredientes
            for ingrediente in data['ingredientes']:
                cursor.execute('''
                    INSERT INTO receta_ingredientes (receta_id, producto_id, cantidad)
                    VALUES (%s, %s, %s)
                ''', (receta_id, ingrediente['producto_id'], ingrediente['cantidad']))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Receta actualizada correctamente'})

        elif request.method == 'DELETE':
            # Verificar si la receta existe
            cursor.execute('SELECT id FROM recetas WHERE id = %s', (receta_id,))
            if not cursor.fetchone():
                return jsonify({'success': False, 'message': 'La receta no existe'}), 404

            # Verificar si la receta está en uso en producción
            cursor.execute('''
                SELECT COUNT(*) FROM produccion_detalles 
                WHERE receta_id = %s
            ''', (receta_id,))
            if cursor.fetchone()['COUNT(*)'] > 0:
                return jsonify({'success': False, 'message': 'No se puede eliminar, la receta está en uso en producción'}), 400

            # Eliminar ingredientes primero
            cursor.execute('DELETE FROM receta_ingredientes WHERE receta_id = %s', (receta_id,))
            
            # Eliminar receta
            cursor.execute('DELETE FROM recetas WHERE id = %s', (receta_id,))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Receta eliminada correctamente'})

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error en la operación: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/inventario/productos/receta')
@login_required
@admin_required
def obtener_productos_receta():
    """API para obtener productos que pueden ser recetas"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
            
        cursor = conn.cursor(dictionary=True)
        
        # Obtener productos que son recetas pero que NO tienen una receta ya asignada
        cursor.execute("""
            SELECT p.id, p.nombre 
            FROM productos p 
            WHERE p.es_receta = 'si' 
            AND p.estatus = 'activo' 
            AND p.id NOT IN (SELECT producto_id FROM recetas)
            ORDER BY p.nombre
        """)
        productos = cursor.fetchall()
        
        return jsonify({'success': True, 'productos': productos})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/manager/inventario/produccion')
@login_required
@admin_required
def manager_inventario_produccion():
    """Gestión de producción del inventario"""
    try:
        conn = get_db_connection()
        if not conn:
            return render_template('partials/inventario_produccion.html', producciones=[])
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, concepto, DATE_FORMAT(fecha, '%Y-%m-%d') as fecha
            FROM producciones
            ORDER BY fecha DESC
        """)
        producciones = cursor.fetchall()
        
        return render_template('partials/inventario_produccion.html', producciones=producciones)
        
    except Error as e:
        flash(f'Error al cargar producción: {str(e)}', 'danger')
        return render_template('partials/inventario_produccion.html', producciones=[])
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/formulario/inventario/produccion')
@login_required
@admin_required
def formulario_produccion_inventario():
    """Formulario para crear nueva producción"""
    return render_template('partials/form_produccion_inventario.html')

@app.route('/api/inventario/produccion', methods=['POST'])
@login_required
@admin_required
def crear_produccion_inventario():
    """API para crear nueva producción"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        data = request.get_json()
        
        # Validaciones
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
            
        if not data.get('concepto'):
            return jsonify({'success': False, 'message': 'El concepto es requerido'}), 400
            
        if not data.get('fecha'):
            return jsonify({'success': False, 'message': 'La fecha es requerida'}), 400
            
        if not data.get('recetas') or len(data['recetas']) == 0:
            return jsonify({'success': False, 'message': 'Debe agregar al menos una receta'}), 400

        # Insertar producción
        cursor.execute('''
            INSERT INTO producciones (concepto, fecha) 
            VALUES (%s, %s)
        ''', (data['concepto'], data['fecha']))
        
        produccion_id = cursor.lastrowid
        
        # Insertar detalles de producción y actualizar inventario
        for receta_data in data['recetas']:
            # Insertar detalle de producción
            cursor.execute('''
                INSERT INTO produccion_detalles (produccion_id, receta_id, cantidad)
                VALUES (%s, %s, %s)
            ''', (produccion_id, receta_data['receta_id'], receta_data['cantidad']))
            
            # Obtener ingredientes de la receta
            cursor.execute('''
                SELECT producto_id, cantidad 
                FROM receta_ingredientes 
                WHERE receta_id = %s
            ''', (receta_data['receta_id'],))
            ingredientes = cursor.fetchall()
            
            # Descontar ingredientes del inventario
            for ingrediente in ingredientes:
                cantidad_necesaria = float(ingrediente[1]) * float(receta_data['cantidad'])
                cursor.execute('''
                    UPDATE productos 
                    SET cantidad_disponible = cantidad_disponible - %s 
                    WHERE id = %s
                ''', (cantidad_necesaria, ingrediente[0]))
            
            # Obtener el producto de la receta y aumentar su stock
            cursor.execute('''
                SELECT producto_id, unidad_producida 
                FROM recetas 
                WHERE id = %s
            ''', (receta_data['receta_id'],))
            receta = cursor.fetchone()
            
            if receta:
                cantidad_producida = float(receta[1]) * float(receta_data['cantidad'])
                cursor.execute('''
                    UPDATE productos 
                    SET cantidad_disponible = cantidad_disponible + %s 
                    WHERE id = %s
                ''', (cantidad_producida, receta[0]))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Producción creada correctamente'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error al crear la producción: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/inventario/recetas/disponibles')
@login_required
@admin_required
def obtener_recetas_disponibles():
    """API para obtener recetas disponibles para producción"""
    busqueda = request.args.get('busqueda', '')
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
            
        cursor = conn.cursor(dictionary=True)
        
        if busqueda.strip():
            cursor.execute("""
                SELECT r.id, p.nombre, r.unidad_producida 
                FROM recetas r 
                JOIN productos p ON r.producto_id = p.id 
                WHERE p.nombre LIKE %s 
                ORDER BY p.nombre 
                LIMIT 20
            """, (f"%{busqueda}%",))
        else:
            cursor.execute("""
                SELECT r.id, p.nombre, r.unidad_producida 
                FROM recetas r 
                JOIN productos p ON r.producto_id = p.id 
                ORDER BY p.nombre 
                LIMIT 20
            """)
        
        recetas = cursor.fetchall()
        
        # Convertir Decimal a float
        for receta in recetas:
            receta['unidad_producida'] = float(receta['unidad_producida'])
        
        return jsonify({'success': True, 'recetas': recetas})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/inventario/produccion/<int:produccion_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@admin_required
def gestion_produccion_inventario(produccion_id):
    """API para gestionar producción"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if request.method == 'GET':
            # Obtener producción con detalles
            cursor.execute("""
                SELECT id, concepto, fecha
                FROM producciones
                WHERE id = %s
            """, (produccion_id,))
            produccion = cursor.fetchone()
            
            if not produccion:
                return jsonify({'success': False, 'message': 'Producción no encontrada'}), 404
            
            # Obtener detalles
            cursor.execute("""
                SELECT pd.receta_id, pd.cantidad, p.nombre as producto_nombre, r.unidad_producida
                FROM produccion_detalles pd
                JOIN recetas r ON pd.receta_id = r.id
                JOIN productos p ON r.producto_id = p.id
                WHERE pd.produccion_id = %s
            """, (produccion_id,))
            detalles = cursor.fetchall()
            
            # Convertir Decimal a float
            for detalle in detalles:
                detalle['precio_unitario'] = float(detalle['precio_unitario'])
                detalle['total'] = float(detalle['total'])
                # Ajustar el stock mostrado: stock real + cantidad ya en la comanda
                cursor.execute("SELECT cantidad_disponible FROM productos WHERE id = %s AND empresa_id = %s", (detalle['producto_id'], session.get('empresa_id')))
                stock_global = cursor.fetchone()
                detalle['stock'] = (float(stock_global[0]) if stock_global else 0) + float(detalle['cantidad'])
                        
            return jsonify({
                'success': True, 
                'produccion': produccion, 
                'detalles': detalles
            })
            
        elif request.method == 'PUT':
            data = request.get_json()
            
            # Validaciones
            if not data:
                return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
                
            if not data.get('concepto'):
                return jsonify({'success': False, 'message': 'El concepto es requerido'}), 400
                
            if not data.get('fecha'):
                return jsonify({'success': False, 'message': 'La fecha es requerida'}), 400
                
            if not data.get('recetas') or len(data['recetas']) == 0:
                return jsonify({'success': False, 'message': 'Debe agregar al menos una receta'}), 400

            # Actualizar producción
            cursor.execute('''
                UPDATE producciones 
                SET concepto = %s, fecha = %s 
                WHERE id = %s
            ''', (data['concepto'], data['fecha'], produccion_id))
            
            # Eliminar detalles existentes
            cursor.execute('DELETE FROM produccion_detalles WHERE produccion_id = %s', (produccion_id,))
            
            # Insertar nuevos detalles
            for receta_data in data['recetas']:
                cursor.execute('''
                    INSERT INTO produccion_detalles (produccion_id, receta_id, cantidad)
                    VALUES (%s, %s, %s)
                ''', (produccion_id, receta_data['receta_id'], receta_data['cantidad']))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Producción actualizada correctamente'})

        elif request.method == 'DELETE':
            # Verificar si la producción existe
            cursor.execute('SELECT id FROM producciones WHERE id = %s', (produccion_id,))
            if not cursor.fetchone():
                return jsonify({'success': False, 'message': 'La producción no existe'}), 404

            # Eliminar detalles primero
            cursor.execute('DELETE FROM produccion_detalles WHERE produccion_id = %s', (produccion_id,))
            
            # Eliminar producción
            cursor.execute('DELETE FROM producciones WHERE id = %s', (produccion_id,))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Producción eliminada correctamente'})

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error en la operación: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

# ======================
# CREAR TABLAS NECESARIAS
# ======================

@app.route('/api/inventario/crear-tablas', methods=['POST'])
@login_required
@soporte_required
def crear_tablas_inventario():
    """API para crear las tablas necesarias del sistema de inventario"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
            
        cursor = conn.cursor()
        
        try:
            # Crear tabla productos si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL,
                    cantidad_disponible DECIMAL(10,2) DEFAULT 0,
                    unidad_medida VARCHAR(20) NOT NULL,
                    estatus ENUM('activo', 'inactivo') DEFAULT 'activo',
                    es_receta ENUM('si', 'no') DEFAULT 'no',
                    costo DECIMAL(10,2) DEFAULT 0,
                    ganancia DECIMAL(5,2) DEFAULT 0,
                    precio_venta DECIMAL(10,2) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Crear tabla compras si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS compras (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    proveedor VARCHAR(100) NOT NULL,
                    fecha DATE NOT NULL,
                    total DECIMAL(10,2) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Crear tabla compra_items si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS compra_detalles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    compra_id INT NOT NULL,
                    producto_id INT NOT NULL,
                    cantidad DECIMAL(10,2) NOT NULL,
                    precio_unitario DECIMAL(10,2) NOT NULL,
                    subtotal DECIMAL(10,2) NOT NULL,
                    FOREIGN KEY (compra_id) REFERENCES compras(id) ON DELETE CASCADE,
                    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
                )
            """)
            
            # Crear tabla recetas si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recetas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    producto_id INT NOT NULL,
                    unidad_producida DECIMAL(10,2) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
                )
            """)
            
            # Crear tabla receta_ingredientes si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS receta_ingredientes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    receta_id INT NOT NULL,
                    producto_id INT NOT NULL,
                    cantidad DECIMAL(10,2) NOT NULL,
                    FOREIGN KEY (receta_id) REFERENCES recetas(id) ON DELETE CASCADE,
                    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
                )
            """)
            
            # Crear tabla producciones si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS producciones (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    concepto VARCHAR(255) NOT NULL,
                    fecha DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Crear tabla produccion_detalles si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS produccion_detalles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    produccion_id INT NOT NULL,
                    receta_id INT NOT NULL,
                    cantidad DECIMAL(10,2) NOT NULL,
                    FOREIGN KEY (produccion_id) REFERENCES producciones(id) ON DELETE CASCADE,
                    FOREIGN KEY (receta_id) REFERENCES recetas(id) ON DELETE CASCADE
                )
            """)
            
            # 2. Crear tabla de pagos de comandas con campo banco
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pagos_comanda (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    comanda_id INT NOT NULL,
                    medio_pago_id INT NOT NULL,
                    monto DECIMAL(10,2) NOT NULL,
                    referencia VARCHAR(100),
                    banco VARCHAR(100),
                    observaciones TEXT,
                    usuario_id INT,
                    fecha_pago TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (comanda_id) REFERENCES comandas(id) ON DELETE CASCADE,
                    FOREIGN KEY (medio_pago_id) REFERENCES medios_pago(id),
                    FOREIGN KEY (usuario_id) REFERENCES usuario(id)
                )
            """)
            
            # 3. Crear tabla de pagos de facturas con campo banco
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pagos_factura (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    factura_id INT NOT NULL,
                    medio_pago_id INT NOT NULL,
                    monto DECIMAL(10,2) NOT NULL,
                    referencia VARCHAR(100),
                    banco VARCHAR(100),
                    observaciones TEXT,
                    usuario_id INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (factura_id) REFERENCES comandas(id) ON DELETE CASCADE,
                    FOREIGN KEY (medio_pago_id) REFERENCES medios_pago(id),
                    FOREIGN KEY (usuario_id) REFERENCES usuario(id)
                )
            """)
            
            # 4. Agregar columna estatus_pago a la tabla comandas si no existe
            cursor.execute("""
                ALTER TABLE comandas 
                ADD COLUMN IF NOT EXISTS estatus_pago ENUM('pendiente', 'pagado', 'credito') DEFAULT 'pendiente'
            """)
            
            conn.commit()
            return jsonify({
                'success': True, 
                'message': 'Tablas del sistema de inventario creadas correctamente'
            })
            
        except Exception as e:
            conn.rollback()
            return jsonify({
                'success': False, 
                'message': f'Error al crear las tablas: {str(e)}'
            }), 500
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Error inesperado: {str(e)}'
        }), 500

# ======================
# GESTIÓN DE GRUPOS
# ======================

@app.route('/manager/grupos')
@login_required
@admin_required
def manager_grupos():
    """Gestión de grupos de items (solo admin)"""
    try:
        conn = get_db_connection()
        if not conn:
            return render_template('partials/grupos.html', grupos=[])
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre FROM grupos WHERE empresa_id = %s ORDER BY nombre", (session.get('empresa_id'),))
        grupos = cursor.fetchall()
        # Adaptar los campos para la plantilla
        for grupo in grupos:
            grupo['codigo'] = grupo['id']
        return render_template('partials/grupos.html', grupos=grupos)
    except Exception as e:
        flash(f'Error al cargar grupos: {str(e)}', 'danger')
        return render_template('partials/grupos.html', grupos=[])
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/grupos', methods=['GET'])
@login_required
def obtener_grupos():
    """API para obtener todos los grupos"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, nombre, descripcion, estatus 
            FROM grupos 
            WHERE empresa_id = %s AND estatus = 'activo'
            ORDER BY nombre
        """, (session.get('empresa_id'),))
        grupos = cursor.fetchall()
        
        # Adaptar los campos para el frontend
        for grupo in grupos:
            grupo['codigo'] = grupo['id']
        
        return jsonify(grupos)
        
    except Exception as e:
        print("Error al obtener grupos:", str(e))
        return jsonify({'success': False, 'message': f'Error al obtener grupos: {str(e)}'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/grupos', methods=['POST'])
@login_required
@admin_required
def crear_grupo():
    """API para crear un nuevo grupo"""
    try:
        data = request.get_json()
        print(f"Datos recibidos para crear grupo: {data}")  # Debug
        
        if not data or not data.get('nombre'):
            return jsonify({'success': False, 'message': 'El nombre es obligatorio'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
            
        cursor = conn.cursor()
        
        # Insertar nuevo grupo (sin especificar id, se genera automáticamente)
        cursor.execute('''
            INSERT INTO grupos (empresa_id, nombre, formato, estatus) 
            VALUES (%s, %s, %s, %s)
        ''', (session.get('empresa_id'), data['nombre'], data.get('formato', ''), data.get('estatus', 'activo')))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Grupo creado correctamente'})
        
    except Exception as e:
        print(f"Error al crear grupo: {str(e)}")  # Debug
        if 'conn' in locals(): conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/grupos/<string:grupo_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@admin_required
def gestion_grupo(grupo_id):
    """API para obtener, actualizar o eliminar un grupo"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
            
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            # Obtener grupo
            cursor.execute('SELECT * FROM grupos WHERE id = %s AND empresa_id = %s', (grupo_id, session.get('empresa_id')))
            grupo = cursor.fetchone()
            if not grupo:
                return jsonify({'success': False, 'message': 'Grupo no encontrado'}), 404
            return jsonify({'success': True, 'grupo': grupo})
            
        elif request.method == 'PUT':
            # Actualizar grupo
            data = request.get_json()
            if not data or not data.get('nombre'):
                return jsonify({'success': False, 'message': 'Datos incompletos'}), 400

            cursor.execute('''
                UPDATE grupos 
                SET nombre = %s, formato = %s, estatus = %s 
                WHERE id = %s AND empresa_id = %s
            ''', (data['nombre'], data.get('formato', ''), data.get('estatus', 'activo'), grupo_id, session.get('empresa_id')))
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': 'Grupo no encontrado'}), 404
                
            conn.commit()
            return jsonify({'success': True, 'message': 'Grupo actualizado correctamente'})

        elif request.method == 'DELETE':
            # Verificar si el grupo está en uso
            cursor.execute('SELECT COUNT(*) as count FROM item WHERE grupo_codigo = %s AND empresa_id = %s', (grupo_id, session.get('empresa_id')))
            if cursor.fetchone()['count'] > 0:
                return jsonify({'success': False, 'message': 'No se puede eliminar el grupo porque tiene items asociados'}), 400

            cursor.execute('DELETE FROM grupos WHERE id = %s AND empresa_id = %s', (grupo_id, session.get('empresa_id')))
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': 'Grupo no encontrado'}), 404
                
            conn.commit()
            return jsonify({'success': True, 'message': 'Grupo eliminado correctamente'})

    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

# ======================
# GESTIÓN DE PRODUCTOS (REEMPLAZA ITEMS)
# ======================

@app.route('/manager/productos')
@login_required
@admin_required
def manager_productos():
    """Gestión de productos del menú (solo admin)"""
    try:
        conn = get_db_connection()
        if not conn:
            return render_template('partials/productos.html', productos=[], grupos=[])
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.id, p.nombre, p.precio_venta, p.cantidad_disponible, p.estatus, g.nombre as grupo 
            FROM productos p 
            LEFT JOIN grupos g ON p.grupo_id = g.id
            WHERE p.empresa_id = %s
            ORDER BY p.nombre
        """, (session.get('empresa_id'),))
        productos = cursor.fetchall()
        
        # Convertir Decimal a float para JSON
        for producto in productos:
            producto['precio_venta'] = float(producto['precio_venta'])
            producto['cantidad_disponible'] = float(producto['cantidad_disponible'])
        
        cursor.execute("""
            SELECT id, nombre 
            FROM grupos 
            WHERE empresa_id = %s AND estatus = 'activo'
            ORDER BY nombre
        """, (session.get('empresa_id'),))
        grupos = cursor.fetchall()
        
        return render_template('partials/productos.html', productos=productos, grupos=grupos)
        
    except Exception as e:
        flash(f'Error al cargar productos: {str(e)}', 'danger')
        return render_template('partials/productos.html', productos=[], grupos=[])
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/formulario/productos')
@login_required
@admin_required
def formulario_productos():
    """Formulario para crear/editar productos"""
    producto_id = request.args.get('id')
    producto = None
    
    try:
        conn = get_db_connection()
        if not conn:
            return render_template('partials/form_producto.html', producto=None, grupos=[])
            
        cursor = conn.cursor(dictionary=True)
        
        # Obtener grupos para el select
        cursor.execute("""
            SELECT id, nombre 
            FROM grupos 
            WHERE empresa_id = %s AND estatus = 'activo' 
            ORDER BY nombre
        """, (session.get('empresa_id'),))
        grupos = cursor.fetchall()
        
        # Si hay ID, obtener el producto
        if producto_id:
            cursor.execute("""
                SELECT p.*, g.nombre as grupo_nombre 
                FROM productos p 
                LEFT JOIN grupos g ON p.grupo_id = g.id 
                WHERE p.id = %s AND p.empresa_id = %s
            """, (producto_id, session.get('empresa_id')))
            producto = cursor.fetchone()
            
            if producto:
                # Convertir Decimal a float para el formulario
                producto['precio_venta'] = float(producto['precio_venta'])
                producto['cantidad_disponible'] = float(producto['cantidad_disponible'])
                producto['costo'] = float(producto['costo'])
        
        return render_template('partials/form_producto.html', producto=producto, grupos=grupos)
        
    except Exception as e:
        flash(f'Error al cargar formulario: {str(e)}', 'danger')
        return render_template('partials/form_producto.html', producto=None, grupos=[])
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/productos', methods=['POST'])
@login_required
@admin_required
def crear_producto():
    """API para crear nuevo producto"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        data = request.get_json()
        print("Datos recibidos para crear producto:", data)  # Debug
        
        # Validaciones
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
            
        if not data.get('nombre'):
            return jsonify({'success': False, 'message': 'El nombre es requerido'}), 400
            
        if data.get('precio_venta') is None or float(data.get('precio_venta', 0)) <= 0:
            return jsonify({'success': False, 'message': 'El precio debe ser mayor a 0'}), 400
            
        if data.get('cantidad_disponible') is None or float(data.get('cantidad_disponible', -1)) < 0:
            return jsonify({'success': False, 'message': 'La cantidad no puede ser negativa'}), 400

        # Insertar nuevo producto
        cursor.execute('''
            INSERT INTO productos (nombre, precio_venta, cantidad_disponible, grupo_id, estatus, empresa_id, unidad_medida, costo) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data['nombre'], 
            data['precio_venta'], 
            data.get('cantidad_disponible', 0),
            data.get('grupo_id'),
            data.get('estatus', 'activo'),
            session.get('empresa_id'),
            data.get('unidad_medida', 'unidad'),
            data.get('costo', 0)
        ))
        conn.commit()
        return jsonify({'success': True, 'message': 'Producto creado correctamente'})
    except Exception as e:
        print("Error al crear producto:", str(e))  # Debug
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error al crear el producto: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/productos/<int:producto_id>', methods=['PUT', 'DELETE'])
@login_required
@admin_required
def gestion_producto(producto_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if request.method == 'PUT':
            data = request.get_json()
            print("Datos recibidos para actualizar producto:", data)  # Debug
            
            # Validaciones
            if not data:
                return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
                
            if not data.get('nombre'):
                return jsonify({'success': False, 'message': 'El nombre es requerido'}), 400
                
            if data.get('precio_venta') is None or float(data.get('precio_venta', 0)) <= 0:
                return jsonify({'success': False, 'message': 'El precio debe ser mayor a 0'}), 400
                
            if data.get('cantidad_disponible') is None or float(data.get('cantidad_disponible', -1)) < 0:
                return jsonify({'success': False, 'message': 'La cantidad no puede ser negativa'}), 400

            # Verificar si el producto existe
            cursor.execute('SELECT id FROM productos WHERE id = %s AND empresa_id = %s', (producto_id, session.get('empresa_id')))
            if not cursor.fetchone():
                return jsonify({'success': False, 'message': 'El producto no existe'}), 404

            # Actualizar producto
            cursor.execute('''
                UPDATE productos 
                SET nombre = %s, precio_venta = %s, cantidad_disponible = %s, grupo_id = %s, estatus = %s, 
                    unidad_medida = %s, costo = %s
                WHERE id = %s AND empresa_id = %s
            ''', (
                data['nombre'], 
                data['precio_venta'], 
                data.get('cantidad_disponible', 0),
                data.get('grupo_id'),
                data.get('estatus', 'activo'),
                data.get('unidad_medida', 'unidad'),
                data.get('costo', 0),
                producto_id,
                session.get('empresa_id')
            ))
            conn.commit()
            return jsonify({'success': True, 'message': 'Producto actualizado correctamente'})

        elif request.method == 'DELETE':
            # Verificar si el producto existe
            cursor.execute('SELECT id FROM productos WHERE id = %s AND empresa_id = %s', (producto_id, session.get('empresa_id')))
            if not cursor.fetchone():
                return jsonify({'success': False, 'message': 'El producto no existe'}), 404

            # Verificar si el producto está en uso
            cursor.execute('''
                SELECT COUNT(*) FROM comanda_detalle_productos 
                WHERE producto_id = %s
            ''', (producto_id,))
            if cursor.fetchone()[0] > 0:
                return jsonify({'success': False, 'message': 'No se puede eliminar, el producto tiene comandas asociadas'}), 400

            cursor.execute('DELETE FROM productos WHERE id = %s AND empresa_id = %s', (producto_id, session.get('empresa_id')))
            conn.commit()
            return jsonify({'success': True, 'message': 'Producto eliminado correctamente'})

    except Exception as e:
        print("Error en gestión de producto:", str(e))  # Debug
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error en la operación: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

# ======================
# GESTIÓN DE CLIENTES
# ======================

from flask import request, jsonify

@app.route('/api/clientes/buscar', methods=['GET'])
@login_required
def buscar_clientes_api():
    """API para buscar clientes por nombre, RIF o teléfono"""
    try:
        query = request.args.get('q', '').strip()
        if len(query) < 2:
            return jsonify([])
            
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, nombre, cedula_rif, telefono, direccion, correo
            FROM clientes
            WHERE empresa_id = %s AND (
                nombre LIKE %s OR cedula_rif LIKE %s OR telefono LIKE %s
            )
            ORDER BY nombre
            LIMIT 20
        """, (session.get('empresa_id'), f'%{query}%', f'%{query}%', f'%{query}%'))
        
        clientes = cursor.fetchall()
        return jsonify(clientes)
        
    except Exception as e:
        print("Error al buscar clientes:", str(e))
        return jsonify({'success': False, 'message': f'Error al buscar clientes: {str(e)}'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/clientes', methods=['GET'])
@login_required
def buscar_clientes():
    busqueda = request.args.get('busqueda', '').strip()
    empresa_id = session.get('empresa_id')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT * FROM clientes
            WHERE empresa_id = %s AND (
                nombre LIKE %s OR cedula_rif LIKE %s OR telefono LIKE %s OR correo LIKE %s
            )
            LIMIT 20
        """
        like = f"%{busqueda}%"
        cursor.execute(query, (empresa_id, like, like, like, like))
        clientes = cursor.fetchall()
        return jsonify({'success': True, 'clientes': clientes})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/clientes', methods=['POST'])
@login_required
def crear_cliente():
    data = request.json
    empresa_id = session.get('empresa_id')
    usuario_id = session['usuario']['id']
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO clientes (nombre, cedula_rif, telefono, direccion, correo, empresa_id, usuario_creador_id, estatus, fecha_nacimiento, observaciones)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data.get('nombre'),
            data.get('cedula_rif'),
            data.get('telefono'),
            data.get('direccion'),
            data.get('correo'),
            empresa_id,
            usuario_id,
            data.get('estatus', 'activo'),
            data.get('fecha_nacimiento'),
            data.get('observaciones')
        ))
        conn.commit()
        return jsonify({'success': True, 'cliente_id': cursor.lastrowid})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        cursor.close()
        conn.close()

# ======================
# GESTIÓN DE COMANDA
# ======================

@app.route('/api/comanda', methods=['GET', 'POST'])
@login_required
def api_comanda():
    if request.method == 'GET':
        # Obtener comanda por mesa_id
        mesa_id = request.args.get('mesa_id')
        if not mesa_id:
            return jsonify({'error': 'mesa_id es requerido'}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Buscar comanda activa para la mesa
            cursor.execute("""
                SELECT c.*, m.nombre as mesa_nombre, 
                       cl.id as cliente_id, cl.nombre as cliente_nombre, cl.cedula_rif as cliente_cedula_rif, 
                       cl.telefono as cliente_telefono, cl.direccion as cliente_direccion, cl.correo as cliente_correo
                FROM comandas c
                JOIN mesas m ON c.mesa_id = m.id
                LEFT JOIN clientes cl ON c.cliente_id = cl.id
                WHERE c.mesa_id = %s AND c.estatus = 'pendiente' AND c.empresa_id = %s
                ORDER BY c.fecha DESC
                LIMIT 1
            """, (mesa_id, session.get('empresa_id')))
            
            comanda = cursor.fetchone()
            
            if comanda:
                # Obtener detalles de la comanda
                cursor.execute("""
                    SELECT cd.*, p.nombre, p.precio_venta, g.nombre as grupo_nombre, p.cantidad_disponible as stock
                    FROM comanda_detalle cd
                    JOIN productos p ON cd.producto_id = p.id
                    LEFT JOIN grupos g ON p.grupo_id = g.id
                    WHERE cd.comanda_id = %s
                """, (comanda['id'],))
                
                detalles = cursor.fetchall()
                
                # Convertir Decimal a float
                comanda['total'] = float(comanda['total'])
                for detalle in detalles:
                    print('DEBUG detalle:', detalle)  # Depuración
                    detalle['precio_unitario'] = float(detalle['precio_unitario'])
                    detalle['total'] = float(detalle['total'])
                    # Ajustar el stock mostrado: stock real + cantidad ya en la comanda
                    cantidad_en_comanda = float(detalle.get('cantidad', 0))
                    cursor.execute("SELECT cantidad_disponible FROM productos WHERE id = %s AND empresa_id = %s", (detalle['producto_id'], session.get('empresa_id')))
                    stock_global = cursor.fetchone()
                    detalle['stock'] = (float(stock_global[0]) if stock_global else 0) + cantidad_en_comanda
                    detalle['stock'] = float(detalle['stock'])
                    detalle['total'] = float(detalle['total'])
                    detalle['precio_unitario'] = float(detalle['precio_unitario'])
                # Convertir cualquier otro campo Decimal a float en comanda
                for k, v in comanda.items():
                    if isinstance(v, Decimal):
                        comanda[k] = float(v)
                # Convertir cualquier otro campo Decimal a float en detalles
                for detalle in detalles:
                    for k, v in detalle.items():
                        if isinstance(v, Decimal):
                            detalle[k] = float(v)
                
                return jsonify({
                    'success': True,
                    'comanda': comanda,
                    'detalles': detalles
                })
            else:
                return jsonify({
                    'success': True,
                    'comanda': None,
                    'detalles': []
                })
                
        except Exception as e:
            print(f"Error al obtener comanda: {str(e)}")
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()
    
    elif request.method == 'POST':
        # Crear o actualizar comanda
        data = request.json
        print('DEBUG - Datos recibidos en POST /api/comanda:', data)  # Debug
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            mesa_id = data.get('mesa_id')
            comanda_id = data.get('comanda_id')
            servicio = data.get('servicio', 'local')
            cliente_id = data.get('cliente_id')
            items = data.get('items', [])
            print(f'DEBUG - Items recibidos: {items}')  # Debug
            
            if not mesa_id or not items:
                print('DEBUG - Faltan mesa_id o items')  # Debug
                return jsonify({'error': 'mesa_id e items son requeridos'}), 400
            
            usuario_id = session['usuario']['id']
            
            if comanda_id:
                # Actualizar comanda existente
                cursor.execute("""
                    UPDATE comandas 
                    SET servicio = %s, cliente_id = %s, empresa_id = %s, total = 0
                    WHERE id = %s
                """, (servicio, cliente_id, session.get('empresa_id'), comanda_id))
                
                # Eliminar detalles existentes
                cursor.execute("DELETE FROM comanda_detalle WHERE comanda_id = %s", (comanda_id,))
            else:
                # Crear nueva comanda
                cursor.execute("""
                    INSERT INTO comandas (mesa_id, usuario_id, servicio, cliente_id, empresa_id, total, estatus)
                    VALUES (%s, %s, %s, %s, %s, 0, 'pendiente')
                """, (mesa_id, usuario_id, servicio, cliente_id, session.get('empresa_id')))
                comanda_id = cursor.lastrowid
            
            # Validar stock antes de insertar detalles
            cantidades_por_producto = {}
            for item in items:
                producto_id = item.get('producto_id')
                cantidad = item.get('cantidad', 0)
                if producto_id and cantidad > 0:
                    cantidades_por_producto[producto_id] = cantidades_por_producto.get(producto_id, 0) + cantidad
            for producto_id, cantidad_total in cantidades_por_producto.items():
                cursor.execute("SELECT cantidad_disponible, nombre FROM productos WHERE id = %s AND empresa_id = %s", (producto_id, session.get('empresa_id')))
                prod = cursor.fetchone()
                if not prod or float(prod[0]) < cantidad_total:
                    return jsonify({'success': False, 'message': f'Stock insuficiente para \"{prod[1] if prod else producto_id}\". Disponible: {prod[0] if prod else 0}'}), 400
            
            # Insertar detalles
            total_comanda = 0
            detalles_insertados = 0
            for item in items:
                producto_id = item.get('producto_id')
                cantidad = item.get('cantidad', 0)
                precio = item.get('precio', 0)
                nota = item.get('nota', '')
                grupo_codigo = item.get('grupo_codigo', '')
                print(f'DEBUG - Intentando insertar detalle: producto_id={producto_id}, cantidad={cantidad}, precio={precio}, nota={nota}')
                
                if producto_id and cantidad > 0:
                    total_item = precio * cantidad
                    total_comanda += total_item
                    try:
                        cursor.execute("""
                            INSERT INTO comanda_detalle 
                            (comanda_id, producto_id, cantidad, precio_unitario, total, nota, estatus)
                            VALUES (%s, %s, %s, %s, %s, %s, 'pendiente')
                        """, (comanda_id, producto_id, cantidad, precio, total_item, nota))
                        detalles_insertados += 1
                        print(f'DEBUG - Detalle insertado correctamente (producto_id={producto_id})')
                    except Exception as e:
                        print(f'ERROR al insertar detalle (producto_id={producto_id}):', e)
            print(f'DEBUG - Total detalles insertados: {detalles_insertados}')
            
            # Actualizar total de la comanda
            cursor.execute("UPDATE comandas SET total = %s WHERE id = %s", (total_comanda, comanda_id))

            # Actualizar estatus de la mesa a 'ocupada'
            cursor.execute("UPDATE mesas SET estatus = %s WHERE id = %s", ('ocupada', mesa_id))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'comanda_id': comanda_id,
                'message': 'Comanda guardada exitosamente'
            })
            
        except Exception as e:
            conn.rollback()
            print(f"Error al guardar comanda: {str(e)}")
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()

@app.route('/api/crear-tabla-clientes', methods=['POST'])
@login_required
@soporte_required
def crear_tabla_clientes():
    """API para crear la tabla clientes si no existe"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
            
        cursor = conn.cursor()
        
        try:
            # Crear tabla clientes si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clientes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL,
                    cedula_rif VARCHAR(20) NOT NULL UNIQUE,
                    telefono VARCHAR(20),
                    direccion TEXT,
                    correo VARCHAR(100),
                    empresa_id INT NOT NULL,
                    usuario_creador_id INT NOT NULL,
                    estatus ENUM('activo', 'inactivo', 'suspendido') DEFAULT 'activo',
                    fecha_nacimiento DATE NULL,
                    observaciones TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (empresa_id) REFERENCES empresa(id),
                    FOREIGN KEY (usuario_creador_id) REFERENCES usuario(id)
                )
            """)
            
            # Verificar si existe el campo cliente_id en la tabla comandas
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'comandas' 
                AND COLUMN_NAME = 'cliente_id'
            """)
            
            if not cursor.fetchone():
                # Agregar el campo cliente_id a la tabla comandas
                cursor.execute("""
                    ALTER TABLE comandas 
                    ADD COLUMN cliente_id INT,
                    ADD FOREIGN KEY (cliente_id) REFERENCES clientes(id)
                """)
            
            conn.commit()
            return jsonify({
                'success': True, 
                'message': 'Tabla clientes creada y estructura de comandas actualizada correctamente'
            })
            
        except Exception as e:
            conn.rollback()
            return jsonify({
                'success': False, 
                'message': f'Error al crear las tablas: {str(e)}'
            }), 500
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Error inesperado: {str(e)}'
        }), 500

@app.route('/api/crear-tablas-pagos', methods=['POST'])
@login_required
def crear_tablas_pagos():
    """Crear las tablas necesarias para el sistema de pagos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Crear tabla de medios de pago
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medios_pago (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(50) NOT NULL,
                descripcion TEXT,
                activo BOOLEAN DEFAULT TRUE,
                empresa_id INT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresa(id) ON DELETE CASCADE
            )
        """)
        
        # 2. Crear tabla de pagos de facturas con campo banco
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pagos_factura (
                id INT AUTO_INCREMENT PRIMARY KEY,
                factura_id INT NOT NULL,
                medio_pago_id INT NOT NULL,
                monto DECIMAL(10,2) NOT NULL,
                referencia VARCHAR(100),
                banco VARCHAR(100),
                observaciones TEXT,
                usuario_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (factura_id) REFERENCES comandas(id) ON DELETE CASCADE,
                FOREIGN KEY (medio_pago_id) REFERENCES medios_pago(id),
                FOREIGN KEY (usuario_id) REFERENCES usuario(id)
            )
        """)
        
        # 3. Agregar columna estatus_pago a la tabla comandas si no existe
        cursor.execute("""
            ALTER TABLE comandas 
            ADD COLUMN IF NOT EXISTS estatus_pago ENUM('pendiente', 'pagado', 'credito') DEFAULT 'pendiente'
        """)
        
        # 4. Insertar medios de pago personalizados
        medios_default = [
            ('Efectivo', 'Pago en efectivo'),
            ('Tarjeta de Débito', 'Pago con tarjeta de débito'),
            ('Tarjeta de Crédito', 'Pago con tarjeta de crédito'),
            ('Transferencia', 'Transferencia bancaria'),
            ('Efectivo$', 'Pago en efectivo en dólares'),
            ('Transferencia$', 'Transferencia bancaria en dólares'),
            ('Cachéa', 'Pago con Cachéa')
        ]
        
        for nombre, descripcion in medios_default:
            cursor.execute("""
                INSERT IGNORE INTO medios_pago (nombre, descripcion, empresa_id)
                VALUES (%s, %s, %s)
            """, (nombre, descripcion, session.get('empresa_id')))
        
        conn.commit()
        return jsonify({
            'success': True,
            'message': 'Tablas de pagos creadas exitosamente'
        })
        
    except Exception as e:
        conn.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/medios-pago', methods=['GET'])
@login_required
def obtener_medios_pago():
    """Obtener medios de pago disponibles"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT id, nombre, descripcion 
            FROM medios_pago 
            WHERE activo = TRUE AND empresa_id = %s
            ORDER BY nombre
        """, (session.get('empresa_id'),))
        
        medios = cursor.fetchall()
        return jsonify({
            'success': True,
            'medios_pago': medios
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/validar-admin', methods=['POST'])
@login_required
def validar_admin():
    """Validar credenciales de administrador para autorizar créditos"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({
            'success': False,
            'error': 'Usuario y contraseña son requeridos'
        }), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT id, nombre_completo, rol, password
            FROM usuario 
            WHERE user = %s AND empresa_id = %s
        """, (username, session.get('empresa_id')))
        
        user = cursor.fetchone()
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Usuario no encontrado'
            }), 401
        
        if user['rol'] != 'admin':
            return jsonify({
                'success': False,
                'error': 'El usuario no tiene permisos de administrador'
            }), 403
        
        # Verificar contraseña en texto plano
        if user['password'] != password:
            return jsonify({
                'success': False,
                'error': 'Contraseña incorrecta'
            }), 401
        
        return jsonify({
            'success': True,
            'message': 'Administrador validado correctamente',
            'admin_id': user['id'],
            'admin_nombre': user['nombre_completo']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/productos', methods=['GET'])
@login_required
def obtener_productos():
    """API para obtener productos, opcionalmente filtrados por grupo"""
    try:
        grupo = request.args.get('grupo')
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
            
        cursor = conn.cursor(dictionary=True)
        
        if grupo:
            # Filtrar por grupo
            cursor.execute("""
                SELECT p.id, p.nombre, p.precio_venta, p.grupo_id, g.nombre as grupo_nombre, g.id as grupo_codigo
                FROM productos p
                LEFT JOIN grupos g ON p.grupo_id = g.id
                WHERE p.empresa_id = %s AND p.estatus = 'activo' AND p.cantidad_disponible > 0 
                AND g.id = %s
                ORDER BY p.nombre
            """, (session.get('empresa_id'), grupo))
        else:
            # Obtener todos los productos
            cursor.execute("""
                SELECT p.id, p.nombre, p.precio_venta, p.grupo_id, g.nombre as grupo_nombre, g.id as grupo_codigo
                FROM productos p
                LEFT JOIN grupos g ON p.grupo_id = g.id
                WHERE p.empresa_id = %s AND p.estatus = 'activo' AND p.cantidad_disponible > 0
                ORDER BY g.nombre, p.nombre
            """, (session.get('empresa_id'),))
        
        productos = cursor.fetchall()
        
        # Convertir Decimal a float para JSON
        for producto in productos:
            producto['precio_venta'] = float(producto['precio_venta'])
        
        return jsonify(productos)
        
    except Exception as e:
        print("Error al obtener productos:", str(e))
        return jsonify({'success': False, 'message': f'Error al obtener productos: {str(e)}'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/facturar', methods=['POST'])
@login_required
def facturar():
    """Emitir una factura a partir de una comanda pagada o a crédito"""
    data = request.json
    comanda_id = data.get('comanda_id')
    empresa_id = session.get('empresa_id')
    usuario_id = session['usuario']['id']
    if not comanda_id:
        return jsonify({'success': False, 'error': 'comanda_id es requerido'}), 400
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. Verificar que la comanda existe y está pagada o a crédito
        cursor.execute("SELECT * FROM comandas WHERE id = %s AND empresa_id = %s", (comanda_id, empresa_id))
        comanda = cursor.fetchone()
        if not comanda:
            return jsonify({'success': False, 'error': 'Comanda no encontrada'}), 404
        if comanda['estatus_pago'] not in ['pagado', 'credito']:
            return jsonify({'success': False, 'error': 'Solo se puede facturar una comanda pagada o a crédito'}), 400
        # 2. Verificar que no exista ya una factura para esta comanda
        cursor.execute("SELECT id FROM facturas WHERE comanda_id = %s AND empresa_id = %s", (comanda_id, empresa_id))
        if cursor.fetchone():
            return jsonify({'success': False, 'error': 'Ya existe una factura para esta comanda'}), 400

        # === CONTROL DE INVENTARIO ===
        # Obtener los productos reales y cantidades de la comanda
        cursor.execute('''
            SELECT d.producto_id, d.cantidad
            FROM comanda_detalle d
            JOIN productos p ON d.producto_id = p.id
            WHERE d.comanda_id = %s
        ''', (comanda_id,))
        productos_comanda = cursor.fetchall()
        productos_sin_stock = []
        for det in productos_comanda:
            producto_id = det[0]
            cantidad_necesaria = float(det[1])
            cursor.execute("SELECT cantidad_disponible, nombre FROM productos WHERE id = %s AND empresa_id = %s", (producto_id, empresa_id))
            prod = cursor.fetchone()
            if not prod or float(prod[0]) < cantidad_necesaria:
                productos_sin_stock.append(prod[1] if prod else f'ID {producto_id}')
        if productos_sin_stock:
            return jsonify({'success': False, 'error': f"Stock insuficiente para: {', '.join(productos_sin_stock)}"}), 400
        # Descontar stock
        for det in productos_comanda:
            producto_id = det[0]
            cantidad_necesaria = float(det[1])
            cursor.execute("UPDATE productos SET cantidad_disponible = cantidad_disponible - %s WHERE id = %s AND empresa_id = %s", (cantidad_necesaria, producto_id, empresa_id))

        # 3. Generar número de factura correlativo por empresa
        cursor.execute("SELECT COALESCE(MAX(numero_factura), 0) + 1 as next_num FROM facturas WHERE empresa_id = %s", (empresa_id,))
        numero_factura = cursor.fetchone()['next_num']
        # 4. Insertar la factura
        cursor.execute("""
            INSERT INTO facturas (comanda_id, numero_factura, cliente_id, total, metodo_pago, estatus, usuario_id, empresa_id)
            VALUES (%s, %s, %s, %s, %s, 'emitida', %s, %s)
        """, (
            comanda_id,
            numero_factura,
            comanda.get('cliente_id'),
            comanda['total'],
            comanda['estatus_pago'],
            usuario_id,
            empresa_id
        ))
        factura_id = cursor.lastrowid
        # 5. Insertar detalles de la factura
        cursor.execute("SELECT * FROM comanda_detalle WHERE comanda_id = %s", (comanda_id,))
        detalles = cursor.fetchall()
        for det in detalles:
            cursor.execute("""
                INSERT INTO factura_detalle (factura_id, producto_id, cantidad, precio_unitario, total, nota, empresa_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                factura_id,
                det['producto_id'],
                det['cantidad'],
                det['precio_unitario'],
                det['total'],
                det.get('nota', ''),
                empresa_id
            ))
        conn.commit()
        return jsonify({
            'success': True,
            'factura_id': factura_id,
            'numero_factura': numero_factura,
            'total': comanda['total'],
            'metodo_pago': comanda['estatus_pago'],
            'cliente_id': comanda.get('cliente_id'),
            'comanda_id': comanda_id
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/factura/<int:factura_id>/pdf')
@login_required
def factura_pdf(factura_id):
    """Genera un PDF tamaño ticket de la factura"""
    import io
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from datetime import datetime
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Obtener datos de la factura, empresa, cliente y detalles
        cursor.execute("""
            SELECT f.*, e.nombre_empresa, e.rif, e.direccion, e.logo, c.nombre as cliente_nombre, c.cedula_rif as cliente_cedula, c.direccion as cliente_direccion
            FROM facturas f
            JOIN empresa e ON f.empresa_id = e.id
            LEFT JOIN clientes c ON f.cliente_id = c.id
            WHERE f.id = %s
        """, (factura_id,))
        factura = cursor.fetchone()
        if not factura:
            return jsonify({'success': False, 'error': 'Factura no encontrada'}), 404
        cursor.execute("""
            SELECT fd.*, p.nombre as producto_nombre
            FROM factura_detalle fd
            LEFT JOIN productos p ON fd.producto_id = p.id
            WHERE fd.factura_id = %s
        """, (factura_id,))
        detalles = cursor.fetchall()
        # Crear PDF tamaño ticket 80mm (ancho 80mm, largo variable)
        buffer = io.BytesIO()
        ticket_width = 80 * mm
        ticket_height = max(120, 60 + 8*len(detalles)) * mm  # Altura mínima + por ítem
        c = canvas.Canvas(buffer, pagesize=(ticket_width, ticket_height))
        y = ticket_height - 10*mm
        # Logo
        if factura['logo']:
            try:
                logo_bytes = factura['logo']
                logo_img = ImageReader(io.BytesIO(logo_bytes))
                c.drawImage(logo_img, 10, y-30, width=60*mm, height=20*mm, preserveAspectRatio=True, mask='auto')
                y -= 22*mm
            except Exception as e:
                y -= 2*mm
        # Empresa
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(ticket_width/2, y, factura['nombre_empresa'])
        y -= 5*mm
        c.setFont("Helvetica", 8)
        c.drawCentredString(ticket_width/2, y, f"RIF: {factura['rif']}")
        y -= 4*mm
        c.drawCentredString(ticket_width/2, y, factura['direccion'] or "")
        y -= 6*mm
        # Factura info
        c.setFont("Helvetica-Bold", 9)
        c.drawString(5*mm, y, f"Factura N°: {factura['numero_factura']}")
        c.setFont("Helvetica", 8)
        fecha_emision = factura['fecha_emision'] if isinstance(factura['fecha_emision'], str) else factura['fecha_emision'].strftime('%d/%m/%Y %H:%M')
        c.drawString(45*mm, y, f"Fecha: {fecha_emision}")
        y -= 5*mm
        # Cliente
        if factura['cliente_nombre']:
            c.setFont("Helvetica-Bold", 8)
            c.drawString(5*mm, y, f"Cliente: {factura['cliente_nombre']}")
            y -= 4*mm
            c.setFont("Helvetica", 7)
            c.drawString(5*mm, y, f"CI/RIF: {factura['cliente_cedula'] or ''}")
            y -= 4*mm
            if factura['cliente_direccion']:
                c.drawString(5*mm, y, f"Dir: {factura['cliente_direccion']}")
                y -= 4*mm
        # Línea
        c.line(5*mm, y, 75*mm, y)
        y -= 3*mm
        # Encabezado ítems
        c.setFont("Helvetica-Bold", 8)
        c.drawString(5*mm, y, "Cant")
        c.drawString(18*mm, y, "Descripción")
        c.drawRightString(75*mm, y, "Total")
        y -= 4*mm
        c.setFont("Helvetica", 7)
        for det in detalles:
            c.drawString(5*mm, y, str(det['cantidad']))
            c.drawString(18*mm, y, det['producto_nombre'] or str(det['producto_id']))
            c.drawRightString(75*mm, y, f"{det['total']:.2f}")
            y -= 4*mm
        y -= 2*mm
        c.line(5*mm, y, 75*mm, y)
        y -= 4*mm
        # Subtotal y total
        c.setFont("Helvetica-Bold", 8)
        c.drawString(5*mm, y, "Subtotal:")
        c.drawRightString(75*mm, y, f"{factura['total']:.2f}")
        y -= 5*mm
        c.drawString(5*mm, y, "Total:")
        c.drawRightString(75*mm, y, f"{factura['total']:.2f}")
        y -= 5*mm
        # Método de pago
        c.setFont("Helvetica", 8)
        c.drawString(5*mm, y, f"Pago: {factura['metodo_pago']}")
        y -= 5*mm
        # Estatus
        c.drawString(5*mm, y, f"Estatus: {factura['estatus']}")
        y -= 5*mm
        c.save()
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f'factura_{factura_id}.pdf', mimetype='application/pdf')
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/facturas/reporte-dia', methods=['GET'])
@login_required
def reporte_facturas_dia():
    """Devuelve todas las facturas emitidas en una fecha dada (default hoy) y permite exportar a PDF."""
    from datetime import datetime, date
    import io
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    fecha = request.args.get('fecha')
    exportar_pdf = request.args.get('pdf') == '1'
    empresa_id = session.get('empresa_id')
    if not fecha:
        fecha = date.today().strftime('%Y-%m-%d')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Obtener facturas con información de cliente
        cursor.execute("""
            SELECT f.id, f.numero_factura, f.fecha_emision, f.total, f.metodo_pago, f.estatus, 
                   c.nombre as cliente_nombre, c.cedula_rif as cliente_cedula
            FROM facturas f
            LEFT JOIN clientes c ON f.cliente_id = c.id
            WHERE DATE(f.fecha_emision) = %s AND f.empresa_id = %s
            ORDER BY f.numero_factura ASC
        """, (fecha, empresa_id))
        facturas = cursor.fetchall()
        
        # Obtener detalles de pago para cada factura
        for f in facturas:
            cursor.execute("""
                SELECT pf.medio_pago_id, pf.monto, pf.referencia, pf.banco, pf.observaciones, 
                       mp.nombre as medio_pago_nombre
                FROM pagos_factura pf
                LEFT JOIN medios_pago mp ON pf.medio_pago_id = mp.id
                WHERE pf.factura_id = %s
                ORDER BY pf.id ASC
            """, (f['id'],))
            f['pagos'] = cursor.fetchall()
        
        if exportar_pdf:
            # Generar PDF mejorado
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, spaceAfter=20)
            subtitle_style = ParagraphStyle('CustomSubtitle', parent=styles['Heading2'], fontSize=12, spaceAfter=10)
            
            elements.append(Paragraph(f"Cierre Diario de Pagos - {fecha}", title_style))
            elements.append(Paragraph(f"Reporte detallado de facturas y pagos realizados", subtitle_style))
            elements.append(Spacer(1, 20))
            
            # Tabla principal con información detallada
            data = [["N° Factura", "Cliente", "Fecha", "Total", "Medios de Pago", "Estatus"]]
            total_general = 0
            
            for f in facturas:
                # Formatear información del cliente
                cliente_info = f["cliente_nombre"] or "Cliente General"
                if f.get("cliente_cedula"):
                    cliente_info += f" ({f['cliente_cedula']})"
                
                # Formatear medios de pago con detalles
                pagos_str = ""
                if f.get('pagos'):
                    pagos_detalle = []
                    for p in f['pagos']:
                        detalle = f"<b>{p['medio_pago_nombre'] or 'Otro'}:</b> ${float(p['monto']):.2f}"
                        if p.get('referencia'):
                            detalle += f" (Ref: {p['referencia']})"
                        if p.get('banco'):
                            detalle += f" - {p['banco']}"
                        if p.get('observaciones'):
                            detalle += f" - {p['observaciones']}"
                        pagos_detalle.append(detalle)
                    pagos_str = '<br/>'.join(pagos_detalle)
                else:
                    pagos_str = f"<b>{f['metodo_pago']}</b>"
                
                data.append([
                    f"#{f['numero_factura']}",
                    cliente_info,
                    f["fecha_emision"].strftime('%d/%m/%Y %H:%M'),
                    f"${float(f['total']):.2f}",
                    pagos_str,
                    f["estatus"].upper()
                ])
                total_general += float(f['total'])
            
            # Agregar total general
            data.append(["", "", "", f"<b>TOTAL: ${total_general:.2f}</b>", "", ""])
            
            # Crear tabla con anchos de columna optimizados
            table = Table(data, colWidths=[80, 150, 100, 80, 150, 80])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (1, 1), (1, -2), 'LEFT'),  # Alinear cliente a la izquierda
                ('ALIGN', (4, 1), (4, -2), 'LEFT'),  # Alinear medios de pago a la izquierda
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, -1), (-1, -1), colors.grey),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.lightgrey])
            ]))
            
            elements.append(table)
            
            # Agregar resumen por medio de pago
            elements.append(Spacer(1, 20))
            elements.append(Paragraph("Resumen por Medio de Pago", subtitle_style))
            
            # Calcular totales por medio de pago
            resumen_medios = {}
            for f in facturas:
                if f.get('pagos'):
                    for p in f['pagos']:
                        medio = p['medio_pago_nombre'] or 'Otro'
                        monto = float(p['monto'])
                        if medio in resumen_medios:
                            resumen_medios[medio] += monto
                        else:
                            resumen_medios[medio] = monto
                else:
                    # Si no hay pagos detallados, usar el método de pago general
                    medio = f['metodo_pago']
                    monto = float(f['total'])
                    if medio in resumen_medios:
                        resumen_medios[medio] += monto
                    else:
                        resumen_medios[medio] = monto
            
            if resumen_medios:
                resumen_data = [["Medio de Pago", "Total"]]
                for medio, total in sorted(resumen_medios.items()):
                    resumen_data.append([medio, f"${total:.2f}"])
                
                resumen_table = Table(resumen_data, colWidths=[200, 100])
                resumen_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
                ]))
                elements.append(resumen_table)
            
            doc.build(elements)
            buffer.seek(0)
            return send_file(buffer, as_attachment=True, download_name=f'cierre_diario_pagos_{fecha}.pdf', mimetype='application/pdf')
        
        # Si no es PDF, devolver JSON mejorado
        for f in facturas:
            f['fecha_emision'] = f['fecha_emision'].strftime('%d/%m/%Y %H:%M')
            f['total'] = float(f['total'])
            if 'pagos' in f:
                for p in f['pagos']:
                    if isinstance(p.get('monto'), Decimal):
                        p['monto'] = float(p['monto'])
        
        return jsonify({
            'success': True, 
            'fecha': fecha, 
            'facturas': facturas,
            'total_facturas': len(facturas),
            'total_general': sum(float(f['total']) for f in facturas)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/facturas/resumen-medios-pago', methods=['GET'])
@login_required
def resumen_medios_pago():
    """Genera un resumen por medio de pago para una fecha específica"""
    from datetime import datetime, date
    import io
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    
    fecha = request.args.get('fecha')
    exportar_pdf = request.args.get('pdf') == '1'
    empresa_id = session.get('empresa_id')
    
    if not fecha:
        fecha = date.today().strftime('%Y-%m-%d')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Obtener todas las facturas del día
        cursor.execute("""
            SELECT f.id, f.total, f.metodo_pago
            FROM facturas f
            WHERE DATE(f.fecha_emision) = %s AND f.empresa_id = %s
        """, (fecha, empresa_id))
        facturas = cursor.fetchall()
        
        # Calcular resumen por medio de pago
        resumen_medios = {}
        total_general = 0
        
        for f in facturas:
            # Obtener pagos detallados
            cursor.execute("""
                SELECT pf.monto, mp.nombre as medio_pago_nombre
                FROM pagos_factura pf
                LEFT JOIN medios_pago mp ON pf.medio_pago_id = mp.id
                WHERE pf.factura_id = %s
            """, (f['id'],))
            pagos = cursor.fetchall()
            
            if pagos:
                # Si hay pagos detallados, usar esos
                for pago in pagos:
                    medio = pago['medio_pago_nombre'] or 'Otro'
                    monto = float(pago['monto'])
                    if medio in resumen_medios:
                        resumen_medios[medio] += monto
                    else:
                        resumen_medios[medio] = monto
                    total_general += monto
            else:
                # Si no hay pagos detallados, usar el método general
                medio = f['metodo_pago']
                monto = float(f['total'])
                if medio in resumen_medios:
                    resumen_medios[medio] += monto
                else:
                    resumen_medios[medio] = monto
                total_general += monto
        
        if exportar_pdf:
            # Generar PDF del resumen
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, spaceAfter=20)
            subtitle_style = ParagraphStyle('CustomSubtitle', parent=styles['Heading2'], fontSize=12, spaceAfter=10)
            
            elements.append(Paragraph(f"Resumen por Medio de Pago - {fecha}", title_style))
            elements.append(Paragraph(f"Reporte consolidado de pagos por método de pago", subtitle_style))
            elements.append(Spacer(1, 20))
            
            # Tabla del resumen
            data = [["Medio de Pago", "Total", "Porcentaje"]]
            
            # Ordenar por monto descendente
            sorted_medios = sorted(resumen_medios.items(), key=lambda x: x[1], reverse=True)
            
            for medio, total in sorted_medios:
                porcentaje = (total / total_general * 100) if total_general > 0 else 0
                data.append([
                    medio,
                    f"${total:.2f}",
                    f"{porcentaje:.1f}%"
                ])
            
            # Agregar total general
            data.append(["", "", ""])
            data.append(["<b>TOTAL GENERAL</b>", f"<b>${total_general:.2f}</b>", "<b>100%</b>"])
            
            table = Table(data, colWidths=[300, 150, 100])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 1), (0, -3), 'LEFT'),  # Alinear medios de pago a la izquierda
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, -2), (-1, -1), colors.grey),
                ('TEXTCOLOR', (0, -2), (-1, -1), colors.whitesmoke),
                ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -3), [colors.white, colors.lightgrey])
            ]))
            
            elements.append(table)
            
            # Agregar estadísticas adicionales
            elements.append(Spacer(1, 20))
            elements.append(Paragraph("Estadísticas Adicionales", subtitle_style))
            
            stats_data = [
                ["Métrica", "Valor"],
                ["Total de Facturas", str(len(facturas))],
                ["Medios de Pago Utilizados", str(len(resumen_medios))],
                ["Medio de Pago Principal", sorted_medios[0][0] if sorted_medios else "N/A"],
                ["Promedio por Factura", f"${(total_general / len(facturas)):.2f}" if facturas else "$0.00"]
            ]
            
            stats_table = Table(stats_data, colWidths=[250, 200])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            elements.append(stats_table)
            
            doc.build(elements)
            buffer.seek(0)
            return send_file(buffer, as_attachment=True, download_name=f'resumen_medios_pago_{fecha}.pdf', mimetype='application/pdf')
        
        # Si no es PDF, devolver JSON
        return jsonify({
            'success': True,
            'fecha': fecha,
            'resumen': resumen_medios,
            'total_general': total_general,
            'total_facturas': len(facturas),
            'medios_utilizados': len(resumen_medios)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/facturas/reporte-medios-pago-completo', methods=['GET'])
@login_required
def reporte_medios_pago_completo():
    """Obtener reporte completo de medios de pago con todos los detalles"""
    from datetime import datetime
    import io
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    
    fecha = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    exportar_pdf = request.args.get('pdf') == '1'
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Obtener facturas con pagos detallados
        cursor.execute("""
            SELECT 
                f.id as factura_id,
                f.numero_factura,
                f.fecha_emision,
                f.total as total_factura,
                f.estatus,
                f.metodo_pago as metodo_pago_general,
                c.nombre as cliente_nombre,
                c.cedula_rif as cliente_cedula,
                c.telefono as cliente_telefono,
                pf.medio_pago_id,
                mp.nombre as medio_pago_nombre,
                pf.monto,
                pf.referencia,
                pf.banco,
                pf.observaciones
            FROM facturas f
            LEFT JOIN clientes c ON f.cliente_id = c.id
            LEFT JOIN pagos_factura pf ON f.id = pf.factura_id
            LEFT JOIN medios_pago mp ON pf.medio_pago_id = mp.id
            WHERE DATE(f.fecha_emision) = %s 
            AND f.empresa_id = %s
            ORDER BY f.numero_factura, pf.id
        """, (fecha, session.get('empresa_id')))
        
        resultados = cursor.fetchall()
        
        # Procesar los resultados
        resumen_medios = {}
        detalles_completos = []
        facturas_procesadas = set()
        
        for row in resultados:
            factura_id = row['factura_id']
            
            if row['medio_pago_id']:  # Si tiene pagos detallados
                medio_pago = row['medio_pago_nombre'] or 'Otro'
                monto = float(row['monto']) if row['monto'] else 0
                
                # Agregar al resumen
                if medio_pago in resumen_medios:
                    resumen_medios[medio_pago] += monto
                else:
                    resumen_medios[medio_pago] = monto
                
                # Agregar detalle completo
                detalles_completos.append({
                    'numero_factura': row['numero_factura'],
                    'cliente_nombre': row['cliente_nombre'] or 'Cliente General',
                    'cliente_cedula': row['cliente_cedula'],
                    'cliente_telefono': row['cliente_telefono'],
                    'medio_pago': medio_pago,
                    'monto': monto,
                    'referencia': row['referencia'],
                    'banco': row['banco'],
                    'observaciones': row['observaciones'],
                    'fecha_emision': row['fecha_emision'],
                    'fecha_pago': row['fecha_emision'],
                    'estatus_factura': row['estatus'],
                    'tipo_pago': 'Detallado'
                })
                
                facturas_procesadas.add(factura_id)
            else:
                # Si no tiene pagos detallados y no se ha procesado
                if factura_id not in facturas_procesadas:
                    medio_pago = row.get('metodo_pago_general', 'No especificado')
                    monto = float(row['total_factura']) if row['total_factura'] else 0
                    
                    if medio_pago in resumen_medios:
                        resumen_medios[medio_pago] += monto
                    else:
                        resumen_medios[medio_pago] = monto
                    
                    detalles_completos.append({
                        'numero_factura': row['numero_factura'],
                        'cliente_nombre': row['cliente_nombre'] or 'Cliente General',
                        'cliente_cedula': row['cliente_cedula'],
                        'cliente_telefono': row['cliente_telefono'],
                        'medio_pago': medio_pago,
                        'monto': monto,
                        'referencia': None,
                        'banco': None,
                        'observaciones': None,
                        'fecha_emision': row['fecha_emision'],
                        'fecha_pago': row['fecha_emision'],
                        'estatus_factura': row['estatus'],
                        'tipo_pago': 'General'
                    })
                    
                    facturas_procesadas.add(factura_id)
        
        # Ordenar detalles por número de factura y medio de pago
        detalles_completos.sort(key=lambda x: (x['numero_factura'], x['medio_pago']))
        
        if exportar_pdf:
            # Generar PDF del reporte completo
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
            elements = []
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, spaceAfter=20)
            subtitle_style = ParagraphStyle('CustomSubtitle', parent=styles['Heading2'], fontSize=12, spaceAfter=10)
            
            elements.append(Paragraph(f"Reporte Completo de Medios de Pago - {fecha}", title_style))
            elements.append(Paragraph(f"Detalle completo de todas las transacciones por método de pago", subtitle_style))
            elements.append(Spacer(1, 20))
            
            # Resumen por medio de pago
            if resumen_medios:
                elements.append(Paragraph("Resumen por Medio de Pago", subtitle_style))
                resumen_data = [["Medio de Pago", "Total", "Porcentaje"]]
                
                sorted_medios = sorted(resumen_medios.items(), key=lambda x: x[1], reverse=True)
                total_general = sum(resumen_medios.values())
                
                for medio, total in sorted_medios:
                    porcentaje = (total / total_general * 100) if total_general > 0 else 0
                    resumen_data.append([
                        medio,
                        f"${total:.2f}",
                        f"{porcentaje:.1f}%"
                    ])
                
                resumen_data.append(["", "", ""])
                resumen_data.append(["<b>TOTAL GENERAL</b>", f"<b>${total_general:.2f}</b>", "<b>100%</b>"])
                
                resumen_table = Table(resumen_data, colWidths=[200, 100, 80])
                resumen_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('ALIGN', (0, 1), (0, -3), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BACKGROUND', (0, -2), (-1, -1), colors.grey),
                    ('TEXTCOLOR', (0, -2), (-1, -1), colors.whitesmoke),
                    ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -3), [colors.white, colors.lightgrey])
                ]))
                elements.append(resumen_table)
                elements.append(Spacer(1, 20))
            
            # Tabla de detalles completos
            elements.append(Paragraph("Detalle Completo de Transacciones", subtitle_style))
            
            # Preparar datos para la tabla
            detalles_data = [["N° Factura", "Cliente", "Cédula/RIF", "Medio de Pago", "Monto", "Referencia", "Banco", "Observaciones", "Fecha"]]
            
            for detalle in detalles_completos:
                detalles_data.append([
                    str(detalle['numero_factura']),
                    detalle['cliente_nombre'],
                    detalle['cliente_cedula'] or '-',
                    detalle['medio_pago'],
                    f"${detalle['monto']:.2f}",
                    detalle['referencia'] or '-',
                    detalle['banco'] or '-',
                    detalle['observaciones'] or '-',
                    str(detalle['fecha_emision'])[:10]
                ])
            
            # Crear tabla con columnas ajustadas para landscape
            detalles_table = Table(detalles_data, colWidths=[50, 120, 80, 100, 60, 80, 80, 100, 80])
            detalles_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (1, 1), (2, -1), 'LEFT'),  # Cliente y Cédula alineados a la izquierda
                ('ALIGN', (7, 1), (7, -1), 'LEFT'),  # Observaciones alineadas a la izquierda
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            elements.append(detalles_table)
            
            # Estadísticas finales
            elements.append(Spacer(1, 20))
            elements.append(Paragraph("Estadísticas del Reporte", subtitle_style))
            
            stats_data = [
                ["Métrica", "Valor"],
                ["Total de Facturas", str(len(facturas_procesadas))],
                ["Total de Transacciones", str(len(detalles_completos))],
                ["Medios de Pago Utilizados", str(len(resumen_medios))],
                ["Total General", f"${sum(resumen_medios.values()):.2f}"],
                ["Promedio por Transacción", f"${(sum(resumen_medios.values()) / len(detalles_completos)):.2f}" if detalles_completos else "$0.00"]
            ]
            
            stats_table = Table(stats_data, colWidths=[200, 150])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            elements.append(stats_table)
            
            doc.build(elements)
            buffer.seek(0)
            return send_file(buffer, as_attachment=True, download_name=f'reporte_completo_medios_pago_{fecha}.pdf', mimetype='application/pdf')
        
        return jsonify({
            'success': True,
            'fecha': fecha,
            'resumen_medios': resumen_medios,
            'detalles_completos': detalles_completos,
            'total_general': sum(resumen_medios.values()),
            'total_facturas': len(facturas_procesadas),
            'total_transacciones': len(detalles_completos)
        })
        
    except Exception as e:
        print(f"Error en reporte_medios_pago_completo: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/corregir-estructura-pagos-factura', methods=['POST'])
@login_required
@soporte_required
def corregir_estructura_pagos_factura():
    """Corregir la estructura de la tabla pagos_factura para que referencie facturas en lugar de comandas"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        print("🔧 Corrigiendo estructura de tabla pagos_factura...")
        
        # 1. Verificar si existe la restricción incorrecta
        cursor.execute("""
            SELECT CONSTRAINT_NAME 
            FROM information_schema.KEY_COLUMN_USAGE 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'pagos_factura' 
            AND COLUMN_NAME = 'factura_id' 
            AND REFERENCED_TABLE_NAME = 'comandas'
        """)
        
        constraint_exists = cursor.fetchone()
        
        if constraint_exists:
            constraint_name = constraint_exists[0]
            print(f"❌ Encontrada restricción incorrecta: {constraint_name}")
            
            # 2. Eliminar la restricción incorrecta
            cursor.execute(f"ALTER TABLE pagos_factura DROP FOREIGN KEY {constraint_name}")
            print(f"✅ Restricción {constraint_name} eliminada")
            
            # 3. Crear la restricción correcta
            cursor.execute("""
                ALTER TABLE pagos_factura 
                ADD CONSTRAINT pagos_factura_ibfk_1 
                FOREIGN KEY (factura_id) REFERENCES facturas(id) ON DELETE CASCADE
            """)
            print("✅ Nueva restricción correcta creada")
        else:
            print("✅ No se encontró restricción incorrecta")
        
        # 4. Verificar que la tabla facturas existe
        cursor.execute("SHOW TABLES LIKE 'facturas'")
        if not cursor.fetchone():
            print("❌ La tabla 'facturas' no existe, creándola...")
            
            # Crear tabla facturas si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facturas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    comanda_id INT,
                    numero_factura INT,
                    cliente_id INT,
                    total DECIMAL(10,2),
                    metodo_pago VARCHAR(50),
                    estatus VARCHAR(20),
                    fecha_emision TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usuario_id INT,
                    empresa_id INT,
                    INDEX idx_comanda_id (comanda_id),
                    INDEX idx_empresa_id (empresa_id),
                    INDEX idx_fecha_emision (fecha_emision)
                )
            """)
            print("✅ Tabla facturas creada")
        
        # 5. Verificar que la tabla pagos_factura tiene la estructura correcta
        cursor.execute("DESCRIBE pagos_factura")
        columns = cursor.fetchall()
        column_names = [col[0] for col in columns]
        
        if 'factura_id' not in column_names:
            print("❌ La columna factura_id no existe en pagos_factura")
            return jsonify({
                'success': False,
                'error': 'La tabla pagos_factura no tiene la estructura correcta'
            }), 500
        
        print("✅ Estructura de pagos_factura verificada correctamente")
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Estructura de pagos_factura corregida exitosamente'
        })
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error corrigiendo estructura: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)