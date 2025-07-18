from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_file
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
from decimal import Decimal
from functools import wraps
from datetime import timedelta, datetime
import win32print
import win32api
import tempfile
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
import subprocess
import tkinter as tk
from tkinter import filedialog

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui_123456'  # Cambia esto por una clave secreta fuerte
app.permanent_session_lifetime = timedelta(hours=1)  # La sesión durará 1 hora

# Configuración de MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'TURING'
app.config['MYSQL_DB'] = 'comandas'

def get_db_connection():
    """Establece conexión con la base de datos"""
    try:
        conn = mysql.connector.connect(
            host=app.config['MYSQL_HOST'],
            port=app.config['MYSQL_PORT'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DB']
        )
        return conn
    except Error as e:
        flash(f'Error al conectar a la base de datos: {str(e)}', 'danger')
        return None

def login_required(f):
    """Decorador para verificar sesión activa"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'warning')
            return redirect(url_for('login'))
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

@app.route('/')
@app.route('/index')
def index():
    """Redirige al usuario según su estado de autenticación"""
    if 'usuario' in session:
        if session.get('rol') == 'admin':
            return redirect(url_for('manager'))
        return redirect(url_for('mesas'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Obtener datos de la empresa
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM empresa LIMIT 1")
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
            
            print(f"Buscando usuario: {user}")  # Debug log
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM usuario WHERE user = %s', (user,))
            user_data = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if user_data:
                print(f"Usuario encontrado: {user_data['user']}")  # Debug log
                print(f"Contraseña almacenada: {user_data['password']}")  # Debug log
                print(f"Contraseña ingresada: {password}")  # Debug log
                
                # Verificar la contraseña directamente (texto plano)
                if user_data['password'] == password:
                    print("Contraseña correcta")  # Debug log
                    session['usuario'] = {
                        'id': user_data['id'],
                        'nombre_completo': user_data['nombre_completo'],
                        'usuario': user_data['user']
                    }
                    session['rol'] = user_data['rol']
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
                    print(f"Contraseña almacenada: {user_data['password']}")  # Debug log
                    print(f"Contraseña ingresada: {password}")  # Debug log
                    flash('Usuario o contraseña incorrectos', 'danger')
            else:
                print("Usuario no encontrado")  # Debug log
                flash('Usuario o contraseña incorrectos', 'danger')
        except Exception as e:
            print(f"Error en login: {str(e)}")  # Debug log
            flash(f'Error al intentar iniciar sesión: {str(e)}', 'danger')
            return render_template('login.html', empresa=empresa)
            
    return render_template('login.html', empresa=empresa)

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
    return render_template('manager.html', usuario=session['usuario'])

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
        cursor.execute("SELECT id, user, nombre_completo, rol, estatus FROM usuario")
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
            cursor.execute("SELECT * FROM usuario WHERE id = %s", (usuario_id,))
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
            cur.execute("SELECT id, user, nombre_completo, estatus, rol FROM usuario")
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
                INSERT INTO usuario (user, password, nombre_completo, estatus, rol)
                VALUES (%s, %s, %s, %s, %s)
            """, (data['user'], data['password'], data['nombre_completo'], data['estatus'], data['rol']))
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
                    WHERE id=%s
                """, (data['user'], data['password'], data['nombre_completo'], data['estatus'], data['rol'], user_id))
            else:
                print("Actualizando usuario sin cambiar contraseña")  # Debug
                cur.execute("""
                    UPDATE usuario 
                    SET user=%s, nombre_completo=%s, estatus=%s, rol=%s 
                    WHERE id=%s
                """, (data['user'], data['nombre_completo'], data['estatus'], data['rol'], user_id))
                
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
            cur.execute("DELETE FROM usuario WHERE id = %s", (user_id,))
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
            ORDER BY i.nombre
        """)
        items = cursor.fetchall()
        
        # Convertir Decimal a float para JSON
        for item in items:
            item['precio'] = float(item['precio'])
        
        cursor.execute("SELECT id, nombre FROM grupos ORDER BY nombre")
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
        cursor.execute("SELECT id, nombre FROM grupos WHERE estatus = 'activo' ORDER BY nombre")
        grupos = cursor.fetchall()
        
        # Si hay ID, obtener el item
        if item_id:
            cursor.execute("""
                SELECT i.*, g.nombre as grupo_nombre 
                FROM item i 
                JOIN grupos g ON i.grupo_codigo = g.id 
                WHERE i.id = %s
            """, (item_id,))
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
            return render_template('mesas.html', mesas=[], items=[], grupos=[])
        
        with conn.cursor(dictionary=True) as cursor:
            # Obtener mesas
            cursor.execute("SELECT Id as id, nombre, estatus FROM mesas ORDER BY nombre")
            mesas = cursor.fetchall()

            # Obtener grupos de items
            cursor.execute("SELECT id, nombre, estatus FROM grupos WHERE estatus = 'activo' ORDER BY id")
            grupos = cursor.fetchall()
            
            # Obtener items disponibles
            cursor.execute("""
                SELECT i.id, i.nombre, i.precio, i.grupo_codigo, g.nombre as grupo_nombre 
                FROM item i
                JOIN grupos g ON i.grupo_codigo = g.id
                WHERE i.estatus = 'activo' AND i.existencia > 0
                ORDER BY g.nombre, i.nombre
            """)
            items = cursor.fetchall()
            
            # Convertir precios Decimal a float
            for item in items:
                item['precio'] = float(item['precio'])
            
            return render_template('mesas.html', 
                                mesas=mesas, 
                                items=items, 
                                grupos=grupos,
                                usuario=session.get('usuario'))
    
    except Error as err:
        flash(f'Error al cargar datos: {str(err)}', 'danger')
        return render_template('mesas.html', mesas=[], items=[], grupos=[])
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

# API PARA COMANDAS - Mejoras sugeridas
@app.route('/api/comanda', methods=['GET', 'POST'])
@login_required
def gestion_comanda():
    if request.method == 'POST':
        try:
            data = request.get_json()
            mesa_id = data.get('mesa_id')
            comanda_id = data.get('comanda_id')
            items = data.get('items', [])
            servicio = data.get('servicio', 'local')
            
            # Debug para verificar la sesión del usuario
            print(f"Session data: {session}")
            print(f"Usuario en sesión: {session.get('usuario')}")
            print(f"Usuario ID: {session.get('usuario', {}).get('id')}")
            
            if not mesa_id or not items:
                return jsonify({'success': False, 'error': 'Datos incompletos'}), 400
                
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                # Inicializar detalles_existentes como diccionario vacío
                detalles_existentes = {}
                
                if comanda_id:
                    # Actualizar comanda existente
                    cursor.execute('''
                        UPDATE comandas 
                        SET total = %s, servicio = %s
                        WHERE id = %s
                    ''', (sum(item['cantidad'] * item['precio'] for item in items), servicio, comanda_id))
                    
                    # Obtener los detalles existentes para preservar impreso y cantidad_impresa
                    cursor.execute('''
                        SELECT item_id, impreso, cantidad_impresa, estatus
                        FROM comanda_detalle 
                        WHERE comanda_id = %s
                    ''', (comanda_id,))
                    detalles_existentes = {row[0]: {'impreso': row[1], 'cantidad_impresa': row[2], 'estatus': row[3]} 
                                        for row in cursor.fetchall()}
                    
                    # Eliminar detalles existentes
                    cursor.execute('DELETE FROM comanda_detalle WHERE comanda_id = %s', (comanda_id,))
                else:
                    # Crear nueva comanda
                    cursor.execute('''
                        INSERT INTO comandas (mesa_id, total, usuario_id, servicio)
                        VALUES (%s, %s, %s, %s)
                    ''', (mesa_id, sum(item['cantidad'] * item['precio'] for item in items), 
                          session.get('usuario', {}).get('id') or None, servicio))  # Cambiar '' por None
                    comanda_id = cursor.lastrowid
                    
                    # Actualizar estado de la mesa
                    cursor.execute('UPDATE mesas SET estatus = "ocupada" WHERE id = %s', (mesa_id,))
                
                # Insertar nuevos detalles
                for item in items:
                    # Preservar impreso y cantidad_impresa si existen
                    detalle_existente = detalles_existentes.get(item['item_id'], {})
                    impreso = detalle_existente.get('impreso', None)  # Cambiar '' por None
                    cantidad_impresa = detalle_existente.get('cantidad_impresa', 0)
                    estatus = detalle_existente.get('estatus', 'pendiente')
                    
                    cursor.execute('''
                        INSERT INTO comanda_detalle 
                        (comanda_id, item_id, cantidad, precio_unitario, total, nota, impreso, cantidad_impresa, estatus)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (comanda_id, item['item_id'], item['cantidad'], 
                          item['precio'], item['cantidad'] * item['precio'],
                          item.get('nota', ''), impreso, cantidad_impresa, estatus))
                
                conn.commit()
                return jsonify({'success': True, 'comanda_id': comanda_id})
                
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cursor.close()
                conn.close()
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
            
    elif request.method == 'GET':
        mesa_id = request.args.get('mesa_id')
        if not mesa_id:
            return jsonify({'success': False, 'error': 'ID de mesa no proporcionado'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Obtener comanda activa
            cursor.execute('''
                SELECT c.*, m.nombre as mesa_nombre, m.estatus as mesa_estatus, u.nombre_completo as usuario_nombre
                FROM comandas c 
                JOIN mesas m ON c.mesa_id = m.id 
                LEFT JOIN usuario u ON c.usuario_id = u.id
                WHERE c.mesa_id = %s AND c.estatus = 'pendiente'
                ORDER BY c.id DESC LIMIT 1
            ''', (mesa_id,))
            comanda = cursor.fetchone()
            
            print(f"Comanda encontrada: {comanda}")  # Debug
            
            if comanda:
                # Obtener detalles
                cursor.execute('''
                    SELECT cd.*, i.nombre, i.grupo_codigo 
                    FROM comanda_detalle cd 
                    LEFT JOIN item i ON cd.item_id = i.id
                    WHERE cd.comanda_id = %s
                ''', (comanda['id'],))
                detalles = cursor.fetchall()
                
                print(f"Detalles encontrados: {detalles}")  # Debug
                
                # Convertir los detalles a un formato más manejable
                detalles_formateados = []
                for detalle in detalles:
                    detalles_formateados.append({
                        'item_id': detalle['item_id'],
                        'nombre': detalle['nombre'] or 'Producto sin nombre',
                        'cantidad': detalle['cantidad'],
                        'precio': float(detalle['precio_unitario']),
                        'total': float(detalle['total']),
                        'grupo_codigo': detalle['grupo_codigo'],
                        'impreso': detalle['impreso'],
                        'estatus': detalle['estatus'],
                        'nota': detalle['nota'],
                        'cantidad_impresa': detalle['cantidad_impresa'] or 0
                    })
                
                print(f"Detalles formateados: {detalles_formateados}")  # Debug
                print(f"Usuario de la comanda: {comanda['usuario_nombre']}")  # Debug
                
                return jsonify({
                    'success': True,
                    'comanda': {
                        'id': comanda['id'],
                        'mesa_id': comanda['mesa_id'],
                        'mesa_nombre': comanda['mesa_nombre'],
                        'mesa_estatus': comanda['mesa_estatus'],
                        'total': float(comanda['total']),
                        'servicio': comanda['servicio'],
                        'usuario_nombre': comanda['usuario_nombre'] or 'Usuario no especificado'
                    },
                    'detalles': detalles_formateados
                })
            else:
                # Si no hay comanda activa, verificar el estado de la mesa
                cursor.execute('SELECT estatus FROM mesas WHERE id = %s', (mesa_id,))
                mesa = cursor.fetchone()
                
                print(f"Mesa encontrada: {mesa}")  # Debug
                
                return jsonify({
                    'success': True,
                    'comanda': None,
                    'detalles': [],
                    'mesa_estatus': mesa['estatus'] if mesa else 'libre'
                })
                
        except Exception as e:
            print(f"Error en GET /api/comanda: {str(e)}")  # Debug
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()

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
        cursor.execute("SELECT id, nombre FROM grupos ORDER BY nombre")
        grupos = cursor.fetchall()
        
        return render_template('partials/grupos.html', grupos=grupos)
        
    except Error as e:
        flash(f'Error al cargar grupos: {str(e)}', 'danger')
        return render_template('partials/grupos.html', grupos=[])
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/grupos', methods=['POST'])
@login_required
@admin_required
def crear_grupo():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        data = request.get_json()
        print("Datos recibidos:", data)  # Debug
        
        if not data or not data.get('id') or not data.get('nombre') or not data.get('formato'):
            return jsonify({'success': False, 'message': 'Datos incompletos'}), 400

        # Verificar si el ID ya existe
        cursor.execute('SELECT id FROM grupos WHERE id = %s', (data['id'],))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'El código ya existe'}), 400

        # Insertar nuevo grupo
        cursor.execute('''
            INSERT INTO grupos (id, nombre, formato, fecha_creacion, estatus) 
            VALUES (%s, %s, %s, NOW(), %s)
        ''', (data['id'], data['nombre'], data['formato'], data.get('estatus', 'activo')))
        conn.commit()
        return jsonify({'success': True, 'message': 'Grupo creado correctamente'})
    except Exception as e:
        print("Error:", str(e))  # Debug
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/grupos/<string:grupo_id>', methods=['PUT', 'DELETE'])
@login_required
@admin_required
def gestion_grupo(grupo_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if request.method == 'PUT':
            data = request.get_json()
            if not data or not data.get('nombre') or not data.get('formato'):
                return jsonify({'success': False, 'message': 'Datos incompletos'}), 400

            # Actualizar grupo
            cursor.execute('''
                UPDATE grupos 
                SET nombre = %s, formato = %s, estatus = %s 
                WHERE id = %s
            ''', (data['nombre'], data['formato'], data.get('estatus', 'activo'), grupo_id))
            conn.commit()
            return jsonify({'success': True, 'message': 'Grupo actualizado correctamente'})

        elif request.method == 'DELETE':
            # Verificar si el grupo está en uso
            cursor.execute('SELECT COUNT(*) FROM item WHERE grupo_codigo = %s', (grupo_id,))
            if cursor.fetchone()[0] > 0:
                return jsonify({'success': False, 'message': 'No se puede eliminar el grupo porque tiene items asociados'}), 400

            cursor.execute('DELETE FROM grupos WHERE id = %s', (grupo_id,))
            conn.commit()
            return jsonify({'success': True, 'message': 'Grupo eliminado correctamente'})

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


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
            cursor.execute("SELECT * FROM mesas WHERE Id = %s", (mesa_id,))
            mesa = cursor.fetchone()
            cursor.close()
            conn.close()
    
    return render_template('partials/form_mesas.html', mesa=mesa)

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
            INSERT INTO mesas (nombre, estatus) 
            VALUES (%s, %s)
        ''', (data['nombre'], data['estatus']))
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
            cursor.execute('SELECT Id FROM mesas WHERE Id = %s', (mesa_id,))
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
            
            cursor.execute("SELECT COUNT(*) as total FROM item")
            total_items = cursor.fetchone()['total']
            print(f"Total de items en BD: {total_items}")  # Debug
            
            cursor.execute("SELECT estatus, COUNT(*) as cantidad FROM comandas GROUP BY estatus")
            estatus_comandas = cursor.fetchall()
            print(f"Estatus de comandas: {estatus_comandas}")  # Debug
            
            query = """
                SELECT i.nombre as item, SUM(d.cantidad) as cantidad, SUM(d.total) as total
                FROM comanda_detalle d
                JOIN item i ON d.item_id = i.id
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
                
            query += " GROUP BY i.nombre ORDER BY total DESC"
            
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
            SELECT i.nombre as item_nombre, d.cantidad, d.precio_unitario, d.total
            FROM comanda_detalle d
            JOIN item i ON d.item_id = i.id
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

@app.route('/api/comandas/<int:comanda_id>/pagar', methods=['PUT'])
@login_required
def pagar_comanda(comanda_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener la comanda y la mesa
        cursor.execute('''
            SELECT c.id, c.mesa_id, c.total, c.estatus, m.id as mesa_id 
            FROM comandas c 
            JOIN mesas m ON c.mesa_id = m.id 
            WHERE c.id = %s
        ''', (comanda_id,))
        comanda = cursor.fetchone()
        
        if not comanda:
            return jsonify({'error': 'Comanda no encontrada'}), 404
        
        # Actualizar estatus de la comanda
        cursor.execute('UPDATE comandas SET estatus = %s WHERE id = %s', ('pagada', comanda_id))
        
        # Actualizar estatus de la mesa a DISPONIBLE en mayúsculas
        cursor.execute('UPDATE mesas SET estatus = %s WHERE id = %s', ('DISPONIBLE', comanda[1]))  # comanda[1] es mesa_id
        
        conn.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error en pagar_comanda: {str(e)}")  # Debug
        import traceback
        print(f"Traceback completo: {traceback.format_exc()}")  # Debug
        conn.rollback()
        return jsonify({'error': str(e)}), 500
        
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
            JOIN item i ON d.item_id = i.id
            WHERE i.nombre = %s AND c.estatus = 'pagada'
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
        import win32print
        printers = []
        for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS):
            printers.append(printer[2])  # printer[2] contiene el nombre de la impresora
        return jsonify(printers)
    except Exception as e:
        print("Error al obtener impresoras de Windows:", str(e))  # Debug
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
    except Exception as e:
        print(f"Error al imprimir en impresora de Windows {printer_name}: {e}")
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
                    SELECT i.nombre as item, SUM(d.cantidad) as cantidad, SUM(d.total) as total
                    FROM comanda_detalle d
                    JOIN item i ON d.item_id = i.id
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
                    
                query += " GROUP BY i.nombre ORDER BY total DESC"
                
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
    if session.get('rol') not in ['admin', 'soporte']:
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect(url_for('manager'))
        
    """Gestión de datos de la empresa (solo admin)"""
    try:
        conn = get_db_connection()
        if not conn:
            return render_template('partials/empresa.html', empresa=None)
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM empresa LIMIT 1")
        empresa = cursor.fetchone()
        
        return render_template('partials/empresa.html', empresa=empresa)
        
    except Error as e:
        flash(f'Error al cargar datos de la empresa: {str(e)}', 'danger')
        return render_template('partials/empresa.html', empresa=None)
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/manager/dashboard')
@login_required
def manager_dashboard():
    """Panel de control para administradores y soporte"""
    if session.get('rol') not in ['admin', 'soporte']:
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect(url_for('manager'))
        
    try:
        conn = get_db_connection()
        if not conn:
            return render_template('partials/dashboard.html', total_ventas_hoy=0, total_ventas_mes=0, top_items=[], ventas_diarias=[])
            
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
            SELECT i.nombre, COUNT(*) as cantidad, SUM(cd.cantidad) as total_unidades
            FROM comanda_detalle cd
            JOIN item i ON cd.item_id = i.id
            JOIN comandas c ON cd.comanda_id = c.id
            WHERE c.estatus = 'pagada'
            AND MONTH(c.fecha) = MONTH(CURDATE())
            AND YEAR(c.fecha) = YEAR(CURDATE())
            GROUP BY i.id, i.nombre
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
        
        return render_template('partials/dashboard.html', 
                             total_ventas_hoy=total_ventas_hoy,
                             total_ventas_mes=total_ventas_mes,
                             top_items=top_items,
                             ventas_diarias=ventas_diarias)
        
    except Error as e:
        flash(f'Error al cargar el dashboard: {str(e)}', 'danger')
        return render_template('partials/dashboard.html', total_ventas_hoy=0, total_ventas_mes=0, top_items=[], ventas_diarias=[])
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

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

# ======================
# RUTAS PARA INVENTARIO
# ======================

@app.route('/manager/inventario')
@login_required
@admin_required
def manager_inventario():
    """Gestión de inventario (solo admin)"""
    try:
        conn = get_db_connection()
        if not conn:
            return render_template('partials/inventario.html', productos=[], items=[])
            
        cursor = conn.cursor(dictionary=True)
        
        # Obtener productos
        cursor.execute("""
            SELECT id, nombre, cantidad_disponible, unidad_medida, estatus
            FROM productos
            ORDER BY nombre
        """)
        productos = cursor.fetchall()
        
        # Obtener items para producción
        cursor.execute("""
            SELECT id, nombre, existencia
            FROM item
            WHERE estatus = 'activo'
            ORDER BY nombre
        """)
        items = cursor.fetchall()
        
        return render_template('partials/inventario.html', productos=productos, items=items)
        
    except Error as e:
        flash(f'Error al cargar inventario: {str(e)}', 'danger')
        return render_template('partials/inventario.html', productos=[], items=[])
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/formulario/producto')
@login_required
@admin_required
def formulario_producto():
    """Formulario para crear/editar producto"""
    producto_id = request.args.get('id')
    producto = None
    
    try:
        conn = get_db_connection()
        if not conn:
            return render_template('partials/form_producto.html', producto=None)
            
        cursor = conn.cursor(dictionary=True)
        
        if producto_id:
            cursor.execute("SELECT * FROM productos WHERE id = %s", (producto_id,))
            producto = cursor.fetchone()
            
            if producto:
                producto['cantidad_disponible'] = float(producto['cantidad_disponible'])
        
        return render_template('partials/form_producto.html', producto=producto)
        
    except Error as e:
        flash(f'Error al cargar formulario: {str(e)}', 'danger')
        return render_template('partials/form_producto.html', producto=None)
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
        
        # Validaciones
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
            
        if not data.get('nombre'):
            return jsonify({'success': False, 'message': 'El nombre es requerido'}), 400
            
        if not data.get('unidad_medida'):
            return jsonify({'success': False, 'message': 'La unidad de medida es requerida'}), 400
            
        if data.get('cantidad_disponible') is None or float(data.get('cantidad_disponible', -1)) < 0:
            return jsonify({'success': False, 'message': 'La cantidad no puede ser negativa'}), 400

        # Insertar nuevo producto
        cursor.execute('''
            INSERT INTO productos (nombre, cantidad_disponible, unidad_medida, estatus) 
            VALUES (%s, %s, %s, %s)
        ''', (data['nombre'], data['cantidad_disponible'], data['unidad_medida'], data.get('estatus', 'activo')))
        
        # Registrar movimiento de entrada inicial
        producto_id = cursor.lastrowid
        cursor.execute('''
            INSERT INTO movimientos_inventario (producto_id, tipo_movimiento, cantidad, motivo, usuario_id)
            VALUES (%s, 'entrada', %s, 'Entrada inicial', %s)
        ''', (producto_id, data['cantidad_disponible'], session.get('usuario_id')))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Producto creado correctamente'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error al crear el producto: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/productos/<int:producto_id>', methods=['PUT', 'DELETE'])
@login_required
@admin_required
def gestion_producto(producto_id):
    """API para gestionar productos"""
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

            # Obtener cantidad actual
            cursor.execute('SELECT cantidad_disponible FROM productos WHERE id = %s', (producto_id,))
            resultado = cursor.fetchone()
            if not resultado:
                return jsonify({'success': False, 'message': 'Producto no encontrado'}), 404
                
            cantidad_actual = float(resultado[0])
            nueva_cantidad = float(data['cantidad_disponible'])
            
            # Actualizar producto
            cursor.execute('''
                UPDATE productos 
                SET nombre = %s, cantidad_disponible = %s, unidad_medida = %s, estatus = %s 
                WHERE id = %s
            ''', (data['nombre'], nueva_cantidad, data['unidad_medida'], data.get('estatus', 'activo'), producto_id))
            
            # Registrar movimiento de ajuste si la cantidad cambió
            if cantidad_actual != nueva_cantidad:
                tipo_movimiento = 'entrada' if nueva_cantidad > cantidad_actual else 'salida'
                cantidad_movimiento = abs(nueva_cantidad - cantidad_actual)
                cursor.execute('''
                    INSERT INTO movimientos_inventario (producto_id, tipo_movimiento, cantidad, motivo, usuario_id)
                    VALUES (%s, %s, %s, 'Ajuste de inventario', %s)
                ''', (producto_id, tipo_movimiento, cantidad_movimiento, session.get('usuario_id')))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Producto actualizado correctamente'})

        elif request.method == 'DELETE':
            # Verificar si el producto existe
            cursor.execute('SELECT id FROM productos WHERE id = %s', (producto_id,))
            if not cursor.fetchone():
                return jsonify({'success': False, 'message': 'El producto no existe'}), 404

            # Verificar si el producto está en uso en producción
            cursor.execute('''
                SELECT COUNT(*) FROM produccion 
                WHERE producto_id = %s
            ''', (producto_id,))
            if cursor.fetchone()[0] > 0:
                return jsonify({'success': False, 'message': 'No se puede eliminar, el producto tiene registros de producción'}), 400

            cursor.execute('DELETE FROM productos WHERE id = %s', (producto_id,))
            conn.commit()
            return jsonify({'success': True, 'message': 'Producto eliminado correctamente'})

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error en la operación: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/produccion', methods=['POST'])
@login_required
@admin_required
def crear_produccion():
    """API para crear registro de producción"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        data = request.get_json()
        
        # Validaciones
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
            
        if not data.get('item_id'):
            return jsonify({'success': False, 'message': 'El item es requerido'}), 400
            
        if not data.get('productos'):
            return jsonify({'success': False, 'message': 'Debe especificar al menos un producto'}), 400

        # Verificar disponibilidad de productos
        for prod in data['productos']:
            cursor.execute('''
                SELECT cantidad_disponible 
                FROM productos 
                WHERE id = %s AND estatus = 'activo'
            ''', (prod['producto_id'],))
            resultado = cursor.fetchone()
            
            if not resultado:
                return jsonify({'success': False, 'message': f'Producto {prod["producto_id"]} no encontrado'}), 404
                
            cantidad_disponible = float(resultado[0])
            if cantidad_disponible < float(prod['cantidad']):
                return jsonify({'success': False, 'message': f'Cantidad insuficiente del producto {prod["producto_id"]}'}), 400

        # Registrar producción y actualizar inventario
        for prod in data['productos']:
            # Insertar registro de producción
            cursor.execute('''
                INSERT INTO produccion (item_id, producto_id, cantidad_requerida)
                VALUES (%s, %s, %s)
            ''', (data['item_id'], prod['producto_id'], prod['cantidad']))
            
            # Actualizar cantidad disponible
            cursor.execute('''
                UPDATE productos 
                SET cantidad_disponible = cantidad_disponible - %s 
                WHERE id = %s
            ''', (prod['cantidad'], prod['producto_id']))
            
            # Registrar movimiento de salida
            cursor.execute('''
                INSERT INTO movimientos_inventario (producto_id, tipo_movimiento, cantidad, motivo, usuario_id)
                VALUES (%s, 'salida', %s, 'Producción de item', %s)
            ''', (prod['producto_id'], prod['cantidad'], session.get('usuario_id')))

        # Actualizar existencia del item
        cursor.execute('''
            UPDATE item 
            SET existencia = existencia + %s 
            WHERE id = %s
        ''', (data.get('cantidad_producida', 1), data['item_id']))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Producción registrada correctamente'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error al registrar producción: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/movimientos-inventario')
@login_required
@admin_required
def obtener_movimientos():
    """API para obtener movimientos de inventario"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
            
        cursor = conn.cursor(dictionary=True)
        
        # Obtener movimientos con información de producto
        cursor.execute("""
            SELECT m.*, p.nombre as producto_nombre, p.unidad_medida
            FROM movimientos_inventario m
            JOIN productos p ON m.producto_id = p.id
            ORDER BY m.fecha_movimiento DESC
        """)
        movimientos = cursor.fetchall()
        
        # Convertir Decimal a float para JSON
        for mov in movimientos:
            mov['cantidad'] = float(mov['cantidad'])
        
        return jsonify({'success': True, 'movimientos': movimientos})
        
    except Exception as e:
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
                'message': 'Debe seleccionar una carpeta'
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
                
                conn.commit()
                return jsonify({
                    'success': True,
                    'message': 'Estructura de comandas actualizada correctamente'
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
                SELECT c.id, c.mesa_id, c.usuario_id, c.servicio, 
                       m.nombre as mesa_nombre, u.nombre_completo as usuario_nombre
                FROM comandas c
                LEFT JOIN mesas m ON c.mesa_id = m.id
                LEFT JOIN usuario u ON c.usuario_id = u.id
                ORDER BY c.id DESC
                LIMIT 5
            """)
            comandas_ejemplo = cursor.fetchall()
            
            return jsonify({
                'success': True,
                'estructura': {
                    'columnas': columnas,
                    'foreign_keys': foreign_keys,
                    'comandas_ejemplo': comandas_ejemplo
                }
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
        
        cursor.execute("SELECT COUNT(*) as total FROM item")
        total_items = cursor.fetchone()['total']
        
        cursor.execute("SELECT estatus, COUNT(*) as cantidad FROM comandas GROUP BY estatus")
        estatus_comandas = cursor.fetchall()
        
        # Verificar comandas pagadas
        cursor.execute("SELECT COUNT(*) as total FROM comandas WHERE estatus = 'pagada'")
        comandas_pagadas = cursor.fetchone()['total']
        
        # Probar la consulta de ventas
        cursor.execute("""
            SELECT i.nombre as item, SUM(d.cantidad) as cantidad, SUM(d.total) as total
            FROM comanda_detalle d
            JOIN item i ON d.item_id = i.id
            JOIN comandas c ON d.comanda_id = c.id
            WHERE c.estatus = 'pagada'
            GROUP BY i.nombre 
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)