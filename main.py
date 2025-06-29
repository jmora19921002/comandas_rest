import customtkinter as ctk
from tkinter import messagebox, ttk
import mysql.connector
from datetime import datetime


ctk.set_appearance_mode("light")  # Modos: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Temas: "blue" (standard), "green", "dark-blue"

ventana = ctk.CTk()
ventana.geometry("1400x900")
ventana.title("Sistema de Inventario - Gestion Integral")
ventana.configure(fg_color=("#f0f0f0", "#2b2b2b"))

# Variables globales para los frames
frame_productos = None
frame_compras = None
frame_recetas = None
frame_produccion = None

# Variables globales para producción
tree_recetas_disp = None
entry_buscar_receta = None

# Variables globales para recetas
combo_producto_receta_global = None
producto_id_map_global = {}

def buscar_recetas_disp():
    """Función global para buscar recetas en producción"""
    if not entry_buscar_receta or not tree_recetas_disp:
        return
    
    busqueda = entry_buscar_receta.get()
    conexion = conectar_bd()
    if conexion:
        cursor = conexion.cursor(dictionary=True)
        if busqueda.strip():
            # Si hay búsqueda, filtrar por nombre
            query = """
                SELECT r.id, p.nombre, r.unidad_producida 
                FROM recetas r 
                JOIN productos p ON r.producto_id = p.id 
                WHERE p.nombre LIKE %s 
                ORDER BY p.nombre 
                LIMIT 20
            """
            cursor.execute(query, (f"%{busqueda}%",))
        else:
            # Si no hay búsqueda, mostrar todas las recetas
            query = """
                SELECT r.id, p.nombre, r.unidad_producida 
                FROM recetas r 
                JOIN productos p ON r.producto_id = p.id 
                ORDER BY p.nombre 
                LIMIT 20
            """
            cursor.execute(query)
        
        recetas = cursor.fetchall()
        conexion.close()
        
        # Limpiar el Treeview
        for item in tree_recetas_disp.get_children():
            tree_recetas_disp.delete(item)
        
        # Insertar los nuevos datos
        for rec in recetas:
            tree_recetas_disp.insert("", "end", values=(rec['id'], rec['nombre'], rec['unidad_producida']))

def mostrar_pantalla(frame_a_mostrar):
    """Función para mostrar solo el frame seleccionado"""
    # Ocultar todos los frames
    if frame_productos:
        frame_productos.pack_forget()
    if frame_compras:
        frame_compras.pack_forget()
    if frame_recetas:
        frame_recetas.pack_forget()
    if frame_produccion:
        frame_produccion.pack_forget()
    
    # Mostrar solo el frame seleccionado
    if frame_a_mostrar:
        frame_a_mostrar.pack(fill="both", expand=True, padx=20, pady=(80, 20))
        
        # Si es la pantalla de producción, actualizar las recetas después de un breve delay
        if frame_a_mostrar == frame_produccion:
            frame_produccion.after(300, lambda: buscar_recetas_disp())
        
        # Si es la pantalla de recetas, actualizar la lista de productos disponibles
        if frame_a_mostrar == frame_recetas:
            frame_recetas.after(300, lambda: actualizar_lista_productos_receta_global())

def crear_menu():
    """Crear el menú superior con estilo moderno"""
    menu_frame = ctk.CTkFrame(ventana, height=60, fg_color="#f8fafc", border_width=0)
    menu_frame.pack(fill="x", padx=10, pady=10)

    estilo_btn = {
        "width": 160,
        "height": 48,
        "corner_radius": 18,
        "font": ctk.CTkFont(size=16, weight="bold"),
        "fg_color": "#e3e8f0",
        "text_color": "#1f538d",
        "hover_color": "#d0d8e8",
        "border_width": 2,
        "border_color": "#b6c2d9",
        "anchor": "w"
    }

    btn_articulos = ctk.CTkButton(
        menu_frame,
        text="Artículos",
        command=lambda: mostrar_pantalla(frame_productos),
        **estilo_btn
    )
    btn_articulos.pack(side="left", padx=12, pady=8)

    btn_compras = ctk.CTkButton(
        menu_frame,
        text="Compras",
        command=lambda: mostrar_pantalla(frame_compras),
        **estilo_btn
    )
    btn_compras.pack(side="left", padx=12, pady=8)

    btn_recetas = ctk.CTkButton(
        menu_frame,
        text="Recetas",
        command=lambda: mostrar_pantalla(frame_recetas),
        **estilo_btn
    )
    btn_recetas.pack(side="left", padx=12, pady=8)

    btn_produccion = ctk.CTkButton(
        menu_frame,
        text="Producción",
        command=lambda: mostrar_pantalla(frame_produccion),
        **estilo_btn
    )
    btn_produccion.pack(side="left", padx=12, pady=8)

def conectar_bd():
    try:
        conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password="TURING",
            database="comandas",
            port=3306
        )
        return conexion
    except mysql.connector.Error as err:
        messagebox.showerror("Error de conexion", f"No se pudo conectar a la base de datos: {err}")
        return None
    
def crear_tablas_produccion():
    """Crear las tablas de producción si no existen"""
    conexion = conectar_bd()
    if not conexion:
        return
    
    cursor = conexion.cursor()
    try:
        # Crear tabla producciones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS producciones (
                id INT AUTO_INCREMENT PRIMARY KEY,
                concepto VARCHAR(255) NOT NULL,
                fecha DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Crear tabla produccion_detalles
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
        
        conexion.commit()
        print("Tablas de producción creadas/verificadas correctamente")
    except mysql.connector.Error as err:
        print(f"Error creando tablas de producción: {err}")
    finally:
        conexion.close()

def cargar_productos():
    conexion = conectar_bd()
    if conexion:
        cursor = conexion.cursor()
        cursor.execute("SELECT id, nombre, cantidad_disponible, unidad_medida, estatus, es_receta, costo, ganancia, precio_venta FROM productos")
        productos = cursor.fetchall()
        conexion.close()
        return productos
    return []

def mostrar_productos():
    lista_productos = cargar_productos()
    if not lista_productos:
        messagebox.showinfo("Informacion", "No hay productos disponibles.")
        return
    
    # Limpiar el Treeview
    for item in tree_productos.get_children():
        tree_productos.delete(item)
    
    # Insertar los nuevos datos
    for producto in lista_productos:
        tree_productos.insert("", "end", values=producto)

def crear_producto():
    def calcular_precio_venta(*args):
        try:
            costo = float(entry_costo.get())
            ganancia = float(entry_ganancia.get())
            precio_venta = costo + (costo * ganancia / 100)
            entry_precio_venta.delete(0, 'end')
            entry_precio_venta.insert(0, f"{precio_venta:.2f}")
        except Exception:
            pass

    def calcular_ganancia(*args):
        try:
            costo = float(entry_costo.get())
            precio_venta = float(entry_precio_venta.get())
            if costo > 0:
                ganancia = ((precio_venta - costo) / costo) * 100
                entry_ganancia.delete(0, 'end')
                entry_ganancia.insert(0, f"{ganancia:.2f}")
        except Exception:
            pass

    def on_costo_change(event):
        if entry_ganancia.get():
            calcular_precio_venta()
        elif entry_precio_venta.get():
            calcular_ganancia()

    def on_ganancia_change(event):
        calcular_precio_venta()

    def on_precio_venta_change(event):
        calcular_ganancia()

    def guardar():
        nombre = entry_nombre.get()
        cantidad = entry_cantidad.get()
        unidad = combo_unidad.get()
        estatus = combo_estatus.get()
        es_receta = combo_es_receta.get()
        costo = entry_costo.get()
        ganancia = entry_ganancia.get()
        precio_venta = entry_precio_venta.get()
        if not nombre or not cantidad or not unidad or not estatus or not es_receta or not costo or not ganancia or not precio_venta:
            messagebox.showwarning("Campos incompletos", "Por favor, completa todos los campos.")
            return
        try:
            cantidad = float(cantidad)
            costo = float(costo)
            ganancia = float(ganancia)
            precio_venta = float(precio_venta)
        except ValueError:
            messagebox.showerror("Error", "Cantidad, costo, ganancia y precio de venta deben ser números válidos.")
            return
        conexion = conectar_bd()
        if conexion:
            cursor = conexion.cursor()
            try:
                cursor.execute(
                    "INSERT INTO productos (nombre, cantidad_disponible, unidad_medida, estatus, es_receta, costo, ganancia, precio_venta) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (nombre, cantidad, unidad, estatus, es_receta, costo, ganancia, precio_venta)
                )
                conexion.commit()
                messagebox.showinfo("Exito", "Producto creado correctamente.")
                top.destroy()
                mostrar_productos()
                
                # Si el producto es tipo receta, actualizar la lista de productos en recetas
                if es_receta == 'si':
                    actualizar_lista_productos_receta_global()
                    
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"No se pudo crear el producto: {err}")
            finally:
                conexion.close()

    top = ctk.CTkToplevel(ventana)
    top.title("Crear Nuevo Producto")
    top.geometry("600x700")
    top.configure(fg_color=("#f0f0f0", "#2b2b2b"))
    top.transient(ventana)
    top.grab_set()
    main_frame = ctk.CTkFrame(top, fg_color="transparent")
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)
    title_label = ctk.CTkLabel(
        main_frame, 
        text="Nuevo Producto", 
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color=("#1f538d", "#4a9eff")
    )
    title_label.pack(pady=(0, 30))
    form_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    form_frame.pack(fill="x", padx=20)
    ctk.CTkLabel(form_frame, text="Nombre del Producto:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0, 5))
    entry_nombre = ctk.CTkEntry(form_frame, width=450, height=35, font=ctk.CTkFont(size=14))
    entry_nombre.pack(fill="x", pady=(0, 15))
    ctk.CTkLabel(form_frame, text="Cantidad:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0, 5))
    entry_cantidad = ctk.CTkEntry(form_frame, width=450, height=35, font=ctk.CTkFont(size=14))
    entry_cantidad.pack(fill="x", pady=(0, 15))
    ctk.CTkLabel(form_frame, text="Unidad de Medida:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0, 5))
    unidades = ["g", "kg", "ml", "L", "taza", "cucharadita", "cucharada", "oz", "lb", "ud", "pz"]
    combo_unidad = ctk.CTkOptionMenu(
        form_frame, 
        values=unidades, 
        width=450, 
        height=35, 
        font=ctk.CTkFont(size=14),
        button_color=("#1f538d", "#4a9eff"),
        button_hover_color=("#1a4a7a", "#3d8ce6")
    )
    combo_unidad.pack(fill="x", pady=(0, 15))
    combo_unidad.set("g")
    ctk.CTkLabel(form_frame, text="Costo:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0, 5))
    entry_costo = ctk.CTkEntry(form_frame, width=450, height=35, font=ctk.CTkFont(size=14))
    entry_costo.pack(fill="x", pady=(0, 15))
    ctk.CTkLabel(form_frame, text="Ganancia (%):", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0, 5))
    entry_ganancia = ctk.CTkEntry(form_frame, width=450, height=35, font=ctk.CTkFont(size=14))
    entry_ganancia.pack(fill="x", pady=(0, 15))
    ctk.CTkLabel(form_frame, text="Precio de Venta:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0, 5))
    entry_precio_venta = ctk.CTkEntry(form_frame, width=450, height=35, font=ctk.CTkFont(size=14))
    entry_precio_venta.pack(fill="x", pady=(0, 15))
    entry_costo.bind('<KeyRelease>', on_costo_change)
    entry_ganancia.bind('<KeyRelease>', on_ganancia_change)
    entry_precio_venta.bind('<KeyRelease>', on_precio_venta_change)
    ctk.CTkLabel(form_frame, text="Estatus:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0, 5))
    combo_estatus = ctk.CTkOptionMenu(
        form_frame, 
        values=["activo", "inactivo"], 
        width=450, 
        height=35, 
        font=ctk.CTkFont(size=14),
        button_color=("#1f538d", "#4a9eff"),
        button_hover_color=("#1a4a7a", "#3d8ce6")
    )
    combo_estatus.pack(fill="x", pady=(0, 15))
    combo_estatus.set("activo")
    ctk.CTkLabel(form_frame, text="¿Es producto de receta?", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0, 5))
    combo_es_receta = ctk.CTkOptionMenu(
        form_frame, 
        values=["si", "no"], 
        width=450, 
        height=35, 
        font=ctk.CTkFont(size=14),
        button_color=("#1f538d", "#4a9eff"),
        button_hover_color=("#1a4a7a", "#3d8ce6")
    )
    combo_es_receta.pack(fill="x", pady=(0, 25))
    combo_es_receta.set("no")
    btn_guardar = ctk.CTkButton(
        form_frame, 
        text="Guardar Producto", 
        command=guardar, 
        width=200, 
        height=40,
        font=ctk.CTkFont(size=16, weight="bold"),
        fg_color=("#1f538d", "#4a9eff"),
        hover_color=("#1a4a7a", "#3d8ce6")
    )
    btn_guardar.pack(pady=10)

def mostrar_compras():
    conexion = conectar_bd()
    if conexion:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.id, c.proveedor, DATE_FORMAT(c.fecha, '%Y-%m-%d') as fecha, c.total 
            FROM compras c
            ORDER BY c.fecha DESC
        """)
        compras = cursor.fetchall()
        conexion.close()
        
        # Limpiar el Treeview
        for item in lista_compras.get_children():
            lista_compras.delete(item)
        
        # Insertar los nuevos datos
        for compra in compras:
            lista_compras.insert("", "end", values=(
                compra['id'],
                compra['proveedor'],
                compra['fecha'],
                f"${compra['total']:.2f}"
            ))

def buscar_productos_compra(busqueda, tree):
    conexion = conectar_bd()
    if conexion:
        cursor = conexion.cursor(dictionary=True)
        query = """
            SELECT id, nombre, cantidad_disponible, unidad_medida 
            FROM productos 
            WHERE nombre LIKE %s AND estatus = 'Activo'
            LIMIT 20
        """
        cursor.execute(query, (f"%{busqueda}%",))
        productos = cursor.fetchall()
        conexion.close()
        
        # Limpiar el Treeview
        for item in tree.get_children():
            tree.delete(item)
        
        # Insertar los nuevos datos
        for producto in productos:
            tree.insert("", "end", values=(
                producto['id'],
                producto['nombre'],
                f"{producto['cantidad_disponible']} {producto['unidad_medida']}"
            ))

def agregar_producto_a_compra(tree_seleccion, items_compra_tree, entry_cantidad, entry_precio):
    seleccion = tree_seleccion.selection()
    if not seleccion:
        messagebox.showwarning("Advertencia", "Por favor seleccione un producto")
        return
    
    try:
        cantidad = float(entry_cantidad.get())
        precio = float(entry_precio.get())
    except ValueError:
        messagebox.showerror("Error", "Cantidad y precio deben ser numeros validos")
        return
    
    if cantidad <= 0 or precio <= 0:
        messagebox.showerror("Error", "Cantidad y precio deben ser mayores a cero")
        return
    
    item_data = tree_seleccion.item(seleccion[0], 'values')
    producto_id = item_data[0]
    nombre_producto = item_data[1]
    subtotal = cantidad * precio
    
    # Agregar a la lista de compra
    items_compra_tree.insert("", "end", values=(
        producto_id,
        nombre_producto,
        f"{cantidad}",
        f"${precio:.2f}",
        f"${subtotal:.2f}"
    ))

def calcular_total(items_compra_tree, entry_total):
    total = 0.0
    for item in items_compra_tree.get_children():
        valores = items_compra_tree.item(item, 'values')
        subtotal = float(valores[4].replace('$', ''))
        total += subtotal
    
    entry_total.delete(0, 'end')
    entry_total.insert(0, f"{total:.2f}")

def crear_compra():
    def guardar_compra():
        proveedor = entry_proveedor.get()
        fecha = entry_fecha.get()
        total_str = entry_total.get()
        
        if not proveedor or not total_str:
            messagebox.showwarning("Campos incompletos", "Por favor complete proveedor y total")
            return
        
        try:
            total = float(total_str)
        except ValueError:
            messagebox.showerror("Error", "Total debe ser un numero valido")
            return
        
        if not items_compra_tree.get_children():
            messagebox.showwarning("Advertencia", "Debe agregar al menos un producto a la compra")
            return
        
        conexion = conectar_bd()
        if not conexion:
            return
        
        cursor = conexion.cursor()
        try:
            # Insertar cabecera de compra
            cursor.execute(
                "INSERT INTO compras (proveedor, fecha, total) VALUES (%s, %s, %s)",
                (proveedor, fecha, total)
            )
            compra_id = cursor.lastrowid
            
            # Insertar detalles de compra y actualizar inventario
            for item in items_compra_tree.get_children():
                valores = items_compra_tree.item(item, 'values')
                producto_id = valores[0]
                cantidad = float(valores[2])
                precio = float(valores[3].replace('$', ''))
                
                # Insertar detalle
                cursor.execute(
                    """INSERT INTO compra_detalles 
                    (compra_id, producto_id, cantidad, precio_unitario, subtotal) 
                    VALUES (%s, %s, %s, %s, %s)""",
                    (compra_id, producto_id, cantidad, precio, cantidad * precio)
                )
                
                # Actualizar inventario
                cursor.execute(
                    "UPDATE productos SET cantidad_disponible = cantidad_disponible + %s WHERE id = %s",
                    (cantidad, producto_id)
                )

                # --- NUEVO: Actualizar costo y precio_venta del producto ---
                # 1. Actualizar costo con el precio unitario de la compra
                # 2. Obtener la ganancia actual
                cursor.execute("SELECT ganancia FROM productos WHERE id = %s", (producto_id,))
                ganancia_row = cursor.fetchone()
                ganancia = float(ganancia_row[0]) if ganancia_row and ganancia_row[0] is not None else 0
                # 3. Calcular nuevo precio de venta
                precio_venta = precio + (precio * ganancia / 100)
                # 4. Actualizar ambos campos
                cursor.execute(
                    "UPDATE productos SET costo = %s, precio_venta = %s WHERE id = %s",
                    (precio, precio_venta, producto_id)
                )
            
            conexion.commit()
            messagebox.showinfo("Exito", "Compra registrada correctamente e inventario actualizado")
            top.destroy()
            mostrar_compras()
            mostrar_productos()  # Actualizar vista de productos
        except mysql.connector.Error as err:
            conexion.rollback()
            messagebox.showerror("Error", f"No se pudo completar la compra: {err}")
        finally:
            conexion.close()

    top = ctk.CTkToplevel(ventana)
    top.title("Registrar Nueva Compra")
    top.geometry("900x900")
    top.configure(fg_color=("#f0f0f0", "#2b2b2b"))
    top.transient(ventana)
    top.grab_set()

    # Frame principal
    main_frame = ctk.CTkFrame(top, fg_color="transparent")
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # Título
    title_label = ctk.CTkLabel(
        main_frame, 
        text="Nueva Compra", 
        font=ctk.CTkFont(size=28, weight="bold"),
        text_color=("#1f538d", "#4a9eff")
    )
    title_label.pack(pady=(0, 20))

    # Frame de búsqueda de productos
    frame_busqueda = ctk.CTkFrame(main_frame, fg_color=("#ffffff", "#3b3b3b"))
    frame_busqueda.pack(fill="x", padx=(0, 15))

    search_label = ctk.CTkLabel(
        frame_busqueda, 
        text="Buscar Producto:", 
        font=ctk.CTkFont(size=16, weight="bold")
    )
    search_label.pack(anchor="w", padx=20, pady=(15, 5))

    search_frame = ctk.CTkFrame(frame_busqueda, fg_color="transparent")
    search_frame.pack(fill="x", padx=20, pady=(0, 15))

    entry_busqueda = ctk.CTkEntry(
        search_frame, 
        width=400, 
        height=35, 
        font=ctk.CTkFont(size=14),
        placeholder_text="Escriba el nombre del producto..."
    )
    entry_busqueda.pack(side="left", padx=(0, 10))

    def on_buscar():
        buscar_productos_compra(entry_busqueda.get(), tree_productos_disponibles)

    btn_buscar = ctk.CTkButton(
        search_frame, 
        text="Buscar", 
        width=120, 
        height=35,
        command=on_buscar,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color=("#1f538d", "#4a9eff"),
        hover_color=("#1a4a7a", "#3d8ce6")
    )
    btn_buscar.pack(side="left")

    # Treeview de productos disponibles
    tree_frame = ctk.CTkFrame(frame_busqueda, fg_color="transparent")
    tree_frame.pack(fill="x", padx=20, pady=(0, 15))

    tree_productos_disponibles = ttk.Treeview(
        tree_frame,
        columns=("ID", "Producto", "Stock"),
        show="headings",
        height=4
    )
    tree_productos_disponibles.heading("ID", text="ID")
    tree_productos_disponibles.heading("Producto", text="Producto")
    tree_productos_disponibles.heading("Stock", text="Stock Actual")
    tree_productos_disponibles.column("ID", width=50, anchor="center")
    tree_productos_disponibles.column("Producto", width=300)
    tree_productos_disponibles.column("Stock", width=150, anchor="center")
    tree_productos_disponibles.pack(fill="x")

    # Frame para agregar productos a la compra
    frame_agregar = ctk.CTkFrame(main_frame, fg_color=("#ffffff", "#3b3b3b"))
    frame_agregar.pack(fill="x", pady=(0, 15))

    add_label = ctk.CTkLabel(
        frame_agregar, 
        text="Agregar Producto a la Compra", 
        font=ctk.CTkFont(size=16, weight="bold")
    )
    add_label.pack(anchor="w", padx=20, pady=(15, 10))

    add_fields_frame = ctk.CTkFrame(frame_agregar, fg_color="transparent")
    add_fields_frame.pack(fill="x", padx=20, pady=(0, 15))

    # Cantidad
    ctk.CTkLabel(add_fields_frame, text="Cantidad:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=(0, 10))
    entry_cantidad = ctk.CTkEntry(add_fields_frame, width=120, height=35, font=ctk.CTkFont(size=14))
    entry_cantidad.pack(side="left", padx=(0, 20))

    # Precio
    ctk.CTkLabel(add_fields_frame, text="Precio Unitario:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=(0, 10))
    entry_precio = ctk.CTkEntry(add_fields_frame, width=120, height=35, font=ctk.CTkFont(size=14))
    entry_precio.pack(side="left", padx=(0, 20))

    def on_agregar():
        agregar_producto_a_compra(
            tree_productos_disponibles,
            items_compra_tree,
            entry_cantidad,
            entry_precio
        )
        calcular_total(items_compra_tree, entry_total)

    btn_agregar = ctk.CTkButton(
        add_fields_frame, 
        text="Agregar a Compra", 
        width=150, 
        height=35,
        command=on_agregar,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color=("#28a745", "#28a745"),
        hover_color=("#218838", "#218838")
    )
    btn_agregar.pack(side="left")

    # Frame de información de compra
    frame_info = ctk.CTkFrame(main_frame, fg_color=("#ffffff", "#3b3b3b"))
    frame_info.pack(fill="x", pady=(0, 15))

    info_label = ctk.CTkLabel(
        frame_info, 
        text="Informacion de la Compra", 
        font=ctk.CTkFont(size=16, weight="bold")
    )
    info_label.pack(anchor="w", padx=20, pady=(15, 10))

    info_fields_frame = ctk.CTkFrame(frame_info, fg_color="transparent")
    info_fields_frame.pack(fill="x", padx=20, pady=(0, 15))

    # Proveedor
    ctk.CTkLabel(info_fields_frame, text="Proveedor:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=(0, 10))
    entry_proveedor = ctk.CTkEntry(info_fields_frame, width=200, height=35, font=ctk.CTkFont(size=14))
    entry_proveedor.pack(side="left", padx=(0, 20))

    # Fecha
    ctk.CTkLabel(info_fields_frame, text="Fecha:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=(0, 10))
    entry_fecha = ctk.CTkEntry(info_fields_frame, width=120, height=35, font=ctk.CTkFont(size=14))
    entry_fecha.insert(0, datetime.now().strftime("%Y-%m-%d"))
    entry_fecha.pack(side="left", padx=(0, 20))

    # Total
    ctk.CTkLabel(info_fields_frame, text="Total:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=(0, 10))
    entry_total = ctk.CTkEntry(info_fields_frame, width=120, height=35, font=ctk.CTkFont(size=14))
    entry_total.pack(side="left")

    # Frame de items en la compra
    frame_items = ctk.CTkFrame(main_frame, fg_color=("#ffffff", "#3b3b3b"))
    frame_items.pack(fill="both", expand=True, pady=(0, 15))

    items_label = ctk.CTkLabel(
        frame_items, 
        text="Productos en la Compra", 
        font=ctk.CTkFont(size=16, weight="bold")
    )
    items_label.pack(anchor="w", padx=20, pady=(15, 10))

    # Treeview de items en la compra
    items_tree_frame = ctk.CTkFrame(frame_items, fg_color="transparent")
    items_tree_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))

    items_compra_tree = ttk.Treeview(
        items_tree_frame,
        columns=("ID", "Producto", "Cantidad", "Precio", "Subtotal"),
        show="headings",
        height=6
    )
    items_compra_tree.heading("ID", text="ID")
    items_compra_tree.heading("Producto", text="Producto")
    items_compra_tree.heading("Cantidad", text="Cantidad")
    items_compra_tree.heading("Precio", text="Precio Unit.")
    items_compra_tree.heading("Subtotal", text="Subtotal")
    items_compra_tree.column("ID", width=50, anchor="center")
    items_compra_tree.column("Producto", width=250)
    items_compra_tree.column("Cantidad", width=100, anchor="center")
    items_compra_tree.column("Precio", width=120, anchor="center")
    items_compra_tree.column("Subtotal", width=120, anchor="center")
    items_compra_tree.pack(fill="both", expand=True)

    # Botón guardar
    btn_guardar = ctk.CTkButton(
        main_frame, 
        text="Guardar Compra", 
        width=200, 
        height=45,
        font=ctk.CTkFont(size=16, weight="bold"),
        command=guardar_compra,
        fg_color=("#1f538d", "#4a9eff"),
        hover_color=("#1a4a7a", "#3d8ce6")
    )
    btn_guardar.pack(pady=10)

def crear_pantalla_productos():
    """Crear la pantalla de productos"""
    global frame_productos
    
    frame_productos = ctk.CTkFrame(ventana, fg_color=("#ffffff", "#3b3b3b"))
    
    # Título de productos
    productos_title = ctk.CTkLabel(
        frame_productos, 
        text="Gestion de Productos", 
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color=("#1f538d", "#4a9eff")
    )
    productos_title.pack(pady=20)

    # Frame de búsqueda y botones
    search_frame = ctk.CTkFrame(frame_productos, fg_color="transparent")
    search_frame.pack(fill="x", padx=20, pady=(0, 20))

    entry_buscar = ctk.CTkEntry(
        search_frame, 
        placeholder_text="Buscar producto...", 
        width=250, 
        height=35,
        font=ctk.CTkFont(size=14)
    )
    entry_buscar.pack(side="left", padx=(0, 10))

    btn_buscar_productos = ctk.CTkButton(
        search_frame, 
        text="Buscar", 
        command=mostrar_productos, 
        width=80, 
        height=35,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color=("#1f538d", "#4a9eff"),
        hover_color=("#1a4a7a", "#3d8ce6")
    )
    btn_buscar_productos.pack(side="left", padx=(0, 10))

    btn_crear = ctk.CTkButton(
        search_frame, 
        text="Nuevo Producto", 
        command=crear_producto, 
        width=120, 
        height=35,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color=("#28a745", "#28a745"),
        hover_color=("#218838", "#218838")
    )
    btn_crear.pack(side="left")

    # Treeview para mostrar los productos
    tree_container = ctk.CTkFrame(frame_productos, fg_color="transparent")
    tree_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    global tree_productos
    tree_productos = ttk.Treeview(
        tree_container, 
        columns=("ID", "Nombre", "Cantidad", "Unidad de Medida", "Estatus", "Es Receta", "Costo", "Ganancia", "Precio Venta"), 
        show="headings",
        height=15
    )

    # Configurar columnas
    tree_productos.heading("ID", text="ID")
    tree_productos.heading("Nombre", text="Nombre")
    tree_productos.heading("Cantidad", text="Cantidad")
    tree_productos.heading("Unidad de Medida", text="Unidad")
    tree_productos.heading("Estatus", text="Estatus")
    tree_productos.heading("Es Receta", text="Es Receta")
    tree_productos.heading("Costo", text="Costo")
    tree_productos.heading("Ganancia", text="Ganancia")
    tree_productos.heading("Precio Venta", text="Precio Venta")

    tree_productos.column("ID", width=50, anchor="center")
    tree_productos.column("Nombre", width=150)
    tree_productos.column("Cantidad", width=80, anchor="center")
    tree_productos.column("Unidad de Medida", width=80, anchor="center")
    tree_productos.column("Estatus", width=80, anchor="center")
    tree_productos.column("Es Receta", width=80, anchor="center")
    tree_productos.column("Costo", width=80, anchor="center")
    tree_productos.column("Ganancia", width=80, anchor="center")
    tree_productos.column("Precio Venta", width=100, anchor="center")

    tree_productos.pack(fill="both", expand=True)

def crear_pantalla_compras():
    """Crear la pantalla de compras"""
    global frame_compras
    
    frame_compras = ctk.CTkFrame(ventana, fg_color=("#ffffff", "#3b3b3b"))
    
    # Título de compras
    compras_title = ctk.CTkLabel(
        frame_compras, 
        text="Gestion de Compras", 
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color=("#1f538d", "#4a9eff")
    )
    compras_title.pack(pady=20)

    # Botón para crear nueva compra
    btn_nueva_compra = ctk.CTkButton(
        frame_compras, 
        text="Nueva Compra", 
        command=crear_compra, 
        width=150, 
        height=35,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color=("#dc3545", "#dc3545"),
        hover_color=("#c82333", "#c82333")
    )
    btn_nueva_compra.pack(pady=(0, 20))

    # Treeview para mostrar las compras
    compras_tree_container = ctk.CTkFrame(frame_compras, fg_color="transparent")
    compras_tree_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    global lista_compras
    lista_compras = ttk.Treeview(
        compras_tree_container, 
        columns=("ID", "Proveedor", "Fecha", "Total"), 
        show="headings",
        height=15
    )

    # Configurar columnas de compras
    lista_compras.heading("ID", text="ID")
    lista_compras.heading("Proveedor", text="Proveedor")
    lista_compras.heading("Fecha", text="Fecha")
    lista_compras.heading("Total", text="Total")

    lista_compras.column("ID", width=50, anchor="center")
    lista_compras.column("Proveedor", width=150)
    lista_compras.column("Fecha", width=100, anchor="center")
    lista_compras.column("Total", width=100, anchor="center")

    lista_compras.pack(fill="both", expand=True)

def crear_pantalla_recetas():
    """Crear la pantalla de recetas"""
    global frame_recetas, combo_producto_receta_global, producto_id_map_global
    frame_recetas = ctk.CTkFrame(ventana, fg_color=("#ffffff", "#3b3b3b"))

    # Título de recetas
    recetas_title = ctk.CTkLabel(
        frame_recetas, 
        text="Gestión de Recetas", 
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color=("#1f538d", "#4a9eff")
    )
    recetas_title.pack(pady=20)

    # --- Frame de búsqueda de recetas existentes ---
    frame_buscar_receta = ctk.CTkFrame(frame_recetas, fg_color="transparent")
    frame_buscar_receta.pack(fill="x", padx=20, pady=(0, 5))
    ctk.CTkLabel(frame_buscar_receta, text="Buscar Receta:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=(0, 10))
    entry_buscar_receta = ctk.CTkEntry(frame_buscar_receta, width=200, height=35, font=ctk.CTkFont(size=14))
    entry_buscar_receta.pack(side="left", padx=(0, 10))

    # Treeview para mostrar recetas encontradas
    tree_recetas = ttk.Treeview(
        frame_recetas,
        columns=("ID", "Producto", "Unidad"),
        show="headings",
        height=4
    )
    tree_recetas.heading("ID", text="ID")
    tree_recetas.heading("Producto", text="Producto")
    tree_recetas.heading("Unidad", text="Unidad")
    tree_recetas.column("ID", width=50, anchor="center")
    tree_recetas.column("Producto", width=200)
    tree_recetas.column("Unidad", width=100, anchor="center")
    tree_recetas.pack(padx=20, pady=(0, 5), fill="x")

    # Obtener productos que son recetas
    def obtener_productos_receta():
        conexion = conectar_bd()
        productos = []
        if conexion:
            cursor = conexion.cursor(dictionary=True)
            # Obtener productos que son recetas pero que NO tienen una receta ya asignada
            query = """
                SELECT p.id, p.nombre 
                FROM productos p 
                WHERE p.es_receta = 'si' 
                AND p.estatus = 'activo' 
                AND p.id NOT IN (SELECT producto_id FROM recetas)
                ORDER BY p.nombre
            """
            cursor.execute(query)
            productos = cursor.fetchall()
            conexion.close()
        return productos

    # --- Frame de datos de la receta ---
    frame_datos = ctk.CTkFrame(frame_recetas, fg_color="transparent")
    frame_datos.pack(fill="x", padx=20, pady=(0, 10))

    ctk.CTkLabel(frame_datos, text="Item Receta:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=(0, 10))
    productos_receta = obtener_productos_receta()
    producto_nombres = [f"{p['id']} - {p['nombre']}" for p in productos_receta]
    producto_id_map_global.clear()
    producto_id_map_global.update({f"{p['id']} - {p['nombre']}": p['id'] for p in productos_receta})
    combo_producto_receta_global = ctk.CTkOptionMenu(frame_datos, values=producto_nombres, width=250, height=35, font=ctk.CTkFont(size=14))
    combo_producto_receta_global.pack(side="left", padx=(0, 20))
    if producto_nombres:
        combo_producto_receta_global.set(producto_nombres[0])

    ctk.CTkLabel(frame_datos, text="Unidad a Producir:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=(0, 10))
    entry_unidad_receta = ctk.CTkEntry(frame_datos, width=100, height=35, font=ctk.CTkFont(size=14))
    entry_unidad_receta.pack(side="left")

    # --- Frame de búsqueda de productos para ingredientes ---
    frame_busqueda = ctk.CTkFrame(frame_recetas, fg_color="transparent")
    frame_busqueda.pack(fill="x", padx=20, pady=(10, 0))
    ctk.CTkLabel(frame_busqueda, text="Buscar Producto:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=(0, 10))
    entry_buscar_item = ctk.CTkEntry(frame_busqueda, width=200, height=35, font=ctk.CTkFont(size=14))
    entry_buscar_item.pack(side="left", padx=(0, 10))

    def buscar_items_receta():
        busqueda = entry_buscar_item.get()
        conexion = conectar_bd()
        if conexion:
            cursor = conexion.cursor(dictionary=True)
            # Buscar productos activos que NO tienen recetas asignadas
            query = """
                SELECT id, nombre, unidad_medida 
                FROM productos 
                WHERE nombre LIKE %s 
                AND estatus = 'activo' 
                AND id NOT IN (SELECT producto_id FROM recetas)
                LIMIT 20
            """
            cursor.execute(query, (f"%{busqueda}%",))
            productos = cursor.fetchall()
            conexion.close()
            for item in tree_items_disponibles.get_children():
                tree_items_disponibles.delete(item)
            for prod in productos:
                tree_items_disponibles.insert("", "end", values=(prod['id'], prod['nombre'], prod['unidad_medida']))

    btn_buscar_item = ctk.CTkButton(
        frame_busqueda, text="Buscar", width=100, height=35,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color=("#1f538d", "#4a9eff"), hover_color=("#1a4a7a", "#3d8ce6"),
        command=buscar_items_receta
    )
    btn_buscar_item.pack(side="left", padx=(0, 10))

    # Treeview de productos disponibles
    tree_items_disponibles = ttk.Treeview(
        frame_recetas,
        columns=("ID", "Producto", "Unidad"),
        show="headings",
        height=4
    )
    tree_items_disponibles.heading("ID", text="ID")
    tree_items_disponibles.heading("Producto", text="Producto")
    tree_items_disponibles.heading("Unidad", text="Unidad")
    tree_items_disponibles.column("ID", width=50, anchor="center")
    tree_items_disponibles.column("Producto", width=200)
    tree_items_disponibles.column("Unidad", width=100, anchor="center")
    tree_items_disponibles.pack(padx=20, pady=(5, 10), fill="x")

    # Frame para agregar ingrediente
    frame_agregar = ctk.CTkFrame(frame_recetas, fg_color="transparent")
    frame_agregar.pack(fill="x", padx=20, pady=(0, 10))
    ctk.CTkLabel(frame_agregar, text="Cantidad:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=(0, 10))
    entry_cantidad_item = ctk.CTkEntry(frame_agregar, width=100, height=35, font=ctk.CTkFont(size=14))
    entry_cantidad_item.pack(side="left", padx=(0, 10))

    def agregar_ingrediente():
        seleccion = tree_items_disponibles.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione un producto para agregar a la receta")
            return
        try:
            cantidad = float(entry_cantidad_item.get())
        except ValueError:
            messagebox.showerror("Error", "La cantidad debe ser un número válido")
            return
        if cantidad <= 0:
            messagebox.showerror("Error", "La cantidad debe ser mayor a cero")
            return
        item_data = tree_items_disponibles.item(seleccion[0], 'values')
        producto_id = item_data[0]
        nombre_producto = item_data[1]
        unidad = item_data[2]
        tree_ingredientes.insert("", "end", values=(producto_id, nombre_producto, unidad, cantidad))
        entry_cantidad_item.delete(0, 'end')

    btn_agregar_item = ctk.CTkButton(
        frame_agregar, text="Agregar a Receta", width=150, height=35,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color=("#28a745", "#28a745"), hover_color=("#218838", "#218838"),
        command=agregar_ingrediente
    )
    btn_agregar_item.pack(side="left", padx=(0, 10))

    # Treeview de ingredientes de la receta
    tree_ingredientes = ttk.Treeview(
        frame_recetas,
        columns=("ID", "Producto", "Unidad", "Cantidad"),
        show="headings",
        height=8
    )
    tree_ingredientes.heading("ID", text="ID")
    tree_ingredientes.heading("Producto", text="Producto")
    tree_ingredientes.heading("Unidad", text="Unidad")
    tree_ingredientes.heading("Cantidad", text="Cantidad")
    tree_ingredientes.column("ID", width=50, anchor="center")
    tree_ingredientes.column("Producto", width=200)
    tree_ingredientes.column("Unidad", width=100, anchor="center")
    tree_ingredientes.column("Cantidad", width=100, anchor="center")
    tree_ingredientes.pack(padx=20, pady=(5, 10), fill="x")

    # --- Guardar, editar y eliminar recetas ---
    def guardar_receta():
        producto_receta_str = combo_producto_receta_global.get()
        producto_id = producto_id_map_global.get(producto_receta_str)
        unidad = entry_unidad_receta.get()
        receta_id = getattr(combo_producto_receta_global, '_receta_id', None)
        if not producto_id or not unidad:
            messagebox.showwarning("Campos incompletos", "Seleccione el item de receta y la unidad")
            return
        if not tree_ingredientes.get_children():
            messagebox.showwarning("Advertencia", "Agregue al menos un ingrediente a la receta")
            return
        conexion = conectar_bd()
        if not conexion:
            return
        cursor = conexion.cursor()
        try:
            if receta_id:
                cursor.execute(
                    "UPDATE recetas SET producto_id=%s, unidad_producida=%s WHERE id=%s",
                    (producto_id, unidad, receta_id)
                )
                cursor.execute("DELETE FROM receta_ingredientes WHERE receta_id=%s", (receta_id,))
            else:
                cursor.execute(
                    "INSERT INTO recetas (producto_id, unidad_producida) VALUES (%s, %s)",
                    (producto_id, unidad)
                )
                receta_id = cursor.lastrowid
            for item in tree_ingredientes.get_children():
                valores = tree_ingredientes.item(item, 'values')
                ingrediente_id = valores[0]
                cantidad = float(valores[3])
                cursor.execute(
                    "INSERT INTO receta_ingredientes (receta_id, producto_id, cantidad) VALUES (%s, %s, %s)",
                    (receta_id, ingrediente_id, cantidad)
                )
            conexion.commit()
            messagebox.showinfo("Éxito", "Receta guardada correctamente")
            combo_producto_receta_global._receta_id = None
            entry_unidad_receta.delete(0, 'end')
            for item in tree_ingredientes.get_children():
                tree_ingredientes.delete(item)
            
            # Actualizar las listas después de guardar
            buscar_recetas()
            actualizar_lista_productos_receta()
            
        except mysql.connector.Error as err:
            conexion.rollback()
            messagebox.showerror("Error", f"No se pudo guardar la receta: {err}")
        finally:
            conexion.close()

    def actualizar_lista_productos_receta():
        """Actualizar la lista de productos disponibles para crear recetas"""
        productos_receta = obtener_productos_receta()
        producto_nombres = [f"{p['id']} - {p['nombre']}" for p in productos_receta]
        producto_id_map_global.clear()
        producto_id_map_global.update({f"{p['id']} - {p['nombre']}": p['id'] for p in productos_receta})
        
        # Actualizar el OptionMenu
        combo_producto_receta_global.configure(values=producto_nombres)
        if producto_nombres:
            combo_producto_receta_global.set(producto_nombres[0])
        else:
            combo_producto_receta_global.set("")

    btn_guardar_receta = ctk.CTkButton(
        frame_recetas, text="Guardar Receta", width=200, height=45,
        font=ctk.CTkFont(size=16, weight="bold"),
        fg_color=("#1f538d", "#4a9eff"), hover_color=("#1a4a7a", "#3d8ce6"),
        command=guardar_receta
    )
    btn_guardar_receta.pack(pady=10)

    # --- Buscar, editar y eliminar recetas existentes ---
    def buscar_recetas():
        busqueda = entry_buscar_receta.get()
        conexion = conectar_bd()
        if conexion:
            cursor = conexion.cursor(dictionary=True)
            query = "SELECT r.id, p.nombre, r.unidad_producida FROM recetas r JOIN productos p ON r.producto_id = p.id WHERE p.nombre LIKE %s ORDER BY p.nombre LIMIT 20"
            cursor.execute(query, (f"%{busqueda}%",))
            recetas = cursor.fetchall()
            conexion.close()
            for item in tree_recetas.get_children():
                tree_recetas.delete(item)
            for rec in recetas:
                tree_recetas.insert("", "end", values=(rec['id'], rec['nombre'], rec['unidad_producida']))

    def cargar_receta_editar():
        seleccion = tree_recetas.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione una receta para editar")
            return
        item_data = tree_recetas.item(seleccion[0], 'values')
        receta_id = item_data[0]
        # Cargar datos de la receta
        conexion = conectar_bd()
        if not conexion:
            return
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT producto_id, unidad_producida FROM recetas WHERE id = %s", (receta_id,))
        receta = cursor.fetchone()
        # Seleccionar el producto en el OptionMenu
        for nombre, pid in producto_id_map_global.items():
            if str(pid) == str(receta['producto_id']):
                combo_producto_receta_global.set(nombre)
                break
        combo_producto_receta_global._receta_id = receta_id
        entry_unidad_receta.delete(0, 'end')
        entry_unidad_receta.insert(0, receta['unidad_producida'])
        # Limpiar ingredientes
        for item in tree_ingredientes.get_children():
            tree_ingredientes.delete(item)
        # Cargar ingredientes
        cursor.execute("SELECT producto_id, cantidad FROM receta_ingredientes WHERE receta_id = %s", (receta_id,))
        ingredientes = cursor.fetchall()
        for ing in ingredientes:
            cursor.execute("SELECT nombre, unidad_medida FROM productos WHERE id = %s", (ing['producto_id'],))
            prod = cursor.fetchone()
            tree_ingredientes.insert("", "end", values=(ing['producto_id'], prod['nombre'], prod['unidad_medida'], ing['cantidad']))
        conexion.close()

    def eliminar_receta():
        seleccion = tree_recetas.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione una receta para eliminar")
            return
        item_data = tree_recetas.item(seleccion[0], 'values')
        receta_id = item_data[0]
        if messagebox.askyesno("Confirmar", "¿Está seguro de eliminar la receta seleccionada?"):
            conexion = conectar_bd()
            if not conexion:
                return
            cursor = conexion.cursor()
            try:
                cursor.execute("DELETE FROM recetas WHERE id = %s", (receta_id,))
                conexion.commit()
                messagebox.showinfo("Éxito", "Receta eliminada correctamente")
                buscar_recetas()
                actualizar_lista_productos_receta()  # Actualizar lista de productos disponibles
            except mysql.connector.Error as err:
                conexion.rollback()
                messagebox.showerror("Error", f"No se pudo eliminar la receta: {err}")
            finally:
                conexion.close()

    # Botones de editar y eliminar
    frame_editar_eliminar = ctk.CTkFrame(frame_recetas, fg_color="transparent")
    frame_editar_eliminar.pack(fill="x", padx=20, pady=(0, 10))
    btn_editar = ctk.CTkButton(
        frame_editar_eliminar, text="Editar", width=100, height=35,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color=("#ffc107", "#ffc107"), hover_color=("#e0a800", "#e0a800"),
        command=cargar_receta_editar
    )
    btn_editar.pack(side="left", padx=(0, 10))
    btn_eliminar = ctk.CTkButton(
        frame_editar_eliminar, text="Eliminar", width=100, height=35,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color=("#dc3545", "#dc3545"), hover_color=("#c82333", "#c82333"),
        command=eliminar_receta
    )
    btn_eliminar.pack(side="left", padx=(0, 10))

def crear_pantalla_produccion():
    """Crear la pantalla de producción"""
    global frame_produccion, tree_recetas_disp, entry_buscar_receta
    frame_produccion = ctk.CTkFrame(ventana, fg_color=("#ffffff", "#3b3b3b"))

    # Título
    produccion_title = ctk.CTkLabel(
        frame_produccion, 
        text="Gestión de Producción", 
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color=("#1f538d", "#4a9eff")
    )
    produccion_title.pack(pady=20)

    # --- NUEVO: Frame de búsqueda de historial de producciones ---
    frame_historial = ctk.CTkFrame(frame_produccion, fg_color="transparent")
    frame_historial.pack(fill="x", padx=20, pady=(0, 5))
    ctk.CTkLabel(frame_historial, text="Buscar Producción:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=(0, 10))
    entry_buscar_prod = ctk.CTkEntry(frame_historial, width=200, height=35, font=ctk.CTkFont(size=14))
    entry_buscar_prod.pack(side="left", padx=(0, 10))

    # Treeview para mostrar historial de producciones
    tree_historial = ttk.Treeview(
        frame_produccion,
        columns=("ID", "Concepto", "Fecha"),
        show="headings",
        height=4
    )
    tree_historial.heading("ID", text="ID")
    tree_historial.heading("Concepto", text="Concepto")
    tree_historial.heading("Fecha", text="Fecha")
    tree_historial.column("ID", width=50, anchor="center")
    tree_historial.column("Concepto", width=200)
    tree_historial.column("Fecha", width=100, anchor="center")
    tree_historial.pack(padx=20, pady=(0, 5), fill="x")

    def buscar_historial():
        busqueda = entry_buscar_prod.get()
        conexion = conectar_bd()
        if conexion:
            cursor = conexion.cursor(dictionary=True)
            query = "SELECT id, concepto, fecha FROM producciones WHERE concepto LIKE %s ORDER BY fecha DESC LIMIT 20"
            cursor.execute(query, (f"%{busqueda}%",))
            producciones = cursor.fetchall()
            conexion.close()
            for item in tree_historial.get_children():
                tree_historial.delete(item)
            for prod in producciones:
                tree_historial.insert("", "end", values=(prod['id'], prod['concepto'], prod['fecha']))

    btn_buscar_historial = ctk.CTkButton(
        frame_historial, text="Buscar", width=100, height=35,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color=("#1f538d", "#4a9eff"), hover_color=("#1a4a7a", "#3d8ce6"),
        command=buscar_historial
    )
    btn_buscar_historial.pack(side="left", padx=(0, 10))

    # --- NUEVO: Botones de editar y eliminar producción ---
    frame_editar_eliminar = ctk.CTkFrame(frame_produccion, fg_color="transparent")
    frame_editar_eliminar.pack(fill="x", padx=20, pady=(0, 10))

    def cargar_produccion_editar():
        seleccion = tree_historial.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione una producción para editar")
            return
        item_data = tree_historial.item(seleccion[0], 'values')
        prod_id = item_data[0]
        # Cargar datos de la producción
        conexion = conectar_bd()
        if not conexion:
            return
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT concepto, fecha FROM producciones WHERE id = %s", (prod_id,))
        prod = cursor.fetchone()
        entry_concepto.delete(0, 'end')
        entry_concepto.insert(0, prod['concepto'])
        entry_fecha.delete(0, 'end')
        entry_fecha.insert(0, prod['fecha'])
        # Limpiar recetas agregadas
        for item in tree_produccion.get_children():
            tree_produccion.delete(item)
        # Cargar detalles
        cursor.execute("SELECT receta_id, cantidad FROM produccion_detalles WHERE produccion_id = %s", (prod_id,))
        detalles = cursor.fetchall()
        for det in detalles:
            cursor.execute("SELECT nombre, unidad_producida FROM recetas WHERE id = %s", (det['receta_id'],))
            receta = cursor.fetchone()
            tree_produccion.insert("", "end", values=(det['receta_id'], receta['nombre'], det['cantidad'], receta['unidad_producida']))
        conexion.close()
        # Guardar el id de la producción en edición
        entry_concepto._produccion_id = prod_id
        actualizar_total()

    def eliminar_produccion():
        seleccion = tree_historial.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione una producción para eliminar")
            return
        item_data = tree_historial.item(seleccion[0], 'values')
        prod_id = item_data[0]
        if messagebox.askyesno("Confirmar", "¿Está seguro de eliminar la producción seleccionada?"):
            conexion = conectar_bd()
            if not conexion:
                return
            cursor = conexion.cursor()
            try:
                cursor.execute("DELETE FROM producciones WHERE id = %s", (prod_id,))
                conexion.commit()
                messagebox.showinfo("Éxito", "Producción eliminada correctamente")
                buscar_historial()
            except mysql.connector.Error as err:
                conexion.rollback()
                messagebox.showerror("Error", f"No se pudo eliminar la producción: {err}")
            finally:
                conexion.close()

    btn_editar = ctk.CTkButton(
        frame_editar_eliminar, text="Editar", width=100, height=35,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color=("#ffc107", "#ffc107"), hover_color=("#e0a800", "#e0a800"),
        command=cargar_produccion_editar
    )
    btn_editar.pack(side="left", padx=(0, 10))

    btn_eliminar = ctk.CTkButton(
        frame_editar_eliminar, text="Eliminar", width=100, height=35,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color=("#dc3545", "#dc3545"), hover_color=("#c82333", "#c82333"),
        command=eliminar_produccion
    )
    btn_eliminar.pack(side="left", padx=(0, 10))

    # Frame de datos generales
    frame_datos = ctk.CTkFrame(frame_produccion, fg_color="transparent")
    frame_datos.pack(fill="x", padx=20, pady=(0, 10))

    ctk.CTkLabel(frame_datos, text="Concepto:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=(0, 10))
    entry_concepto = ctk.CTkEntry(frame_datos, width=200, height=35, font=ctk.CTkFont(size=14))
    entry_concepto.pack(side="left", padx=(0, 20))

    ctk.CTkLabel(frame_datos, text="Fecha de Producción:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=(0, 10))
    entry_fecha = ctk.CTkEntry(frame_datos, width=120, height=35, font=ctk.CTkFont(size=14))
    entry_fecha.pack(side="left")
    entry_fecha.insert(0, datetime.now().strftime("%Y-%m-%d"))

    # Frame de búsqueda de recetas
    frame_busqueda = ctk.CTkFrame(frame_produccion, fg_color="transparent")
    frame_busqueda.pack(fill="x", padx=20, pady=(0, 10))

    ctk.CTkLabel(frame_busqueda, text="Buscar Receta:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=(0, 10))
    entry_buscar_receta = ctk.CTkEntry(frame_busqueda, width=200, height=35, font=ctk.CTkFont(size=14))
    entry_buscar_receta.pack(side="left", padx=(0, 10))

    # Treeview de recetas disponibles
    tree_recetas_disp = ttk.Treeview(
        frame_produccion,
        columns=("ID", "Nombre", "Unidad"),
        show="headings",
        height=4
    )
    tree_recetas_disp.heading("ID", text="ID")
    tree_recetas_disp.heading("Nombre", text="Nombre")
    tree_recetas_disp.heading("Unidad", text="Unidad")
    tree_recetas_disp.column("ID", width=50, anchor="center")
    tree_recetas_disp.column("Nombre", width=200)
    tree_recetas_disp.column("Unidad", width=100, anchor="center")
    tree_recetas_disp.pack(padx=20, pady=(0, 10), fill="x")

    ctk.CTkLabel(frame_busqueda, text="Cantidad:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=(20, 10))
    entry_cantidad = ctk.CTkEntry(frame_busqueda, width=80, height=35, font=ctk.CTkFont(size=14))
    entry_cantidad.pack(side="left", padx=(0, 10))

    btn_buscar_receta = ctk.CTkButton(
        frame_busqueda, text="Buscar", width=100, height=35,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color=("#1f538d", "#4a9eff"), hover_color=("#1a4a7a", "#3d8ce6"),
        command=buscar_recetas_disp
    )
    btn_buscar_receta.pack(side="left", padx=(0, 10))

    def agregar_a_produccion():
        seleccion = tree_recetas_disp.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione una receta para agregar")
            return
        try:
            cantidad = float(entry_cantidad.get())
        except ValueError:
            messagebox.showerror("Error", "La cantidad debe ser un número válido")
            return
        if cantidad <= 0:
            messagebox.showerror("Error", "La cantidad debe ser mayor a cero")
            return
        item_data = tree_recetas_disp.item(seleccion[0], 'values')
        receta_id = item_data[0]
        nombre = item_data[1]
        unidad = item_data[2]
        # Verificar si ya está en la lista
        for item in tree_produccion.get_children():
            if tree_produccion.item(item, 'values')[0] == receta_id:
                messagebox.showwarning("Advertencia", "La receta ya está en la lista de producción")
                return
        tree_produccion.insert("", "end", values=(receta_id, nombre, cantidad, unidad))
        entry_cantidad.delete(0, 'end')
        actualizar_total()

    btn_agregar = ctk.CTkButton(
        frame_busqueda, text="Agregar", width=120, height=35,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color=("#28a745", "#28a745"), hover_color=("#218838", "#218838"),
        command=agregar_a_produccion
    )
    btn_agregar.pack(side="left", padx=(0, 10))

    # Treeview de recetas agregadas a la producción
    tree_produccion = ttk.Treeview(
        frame_produccion,
        columns=("ID", "Nombre", "Cantidad", "Unidad"),
        show="headings",
        height=8
    )
    tree_produccion.heading("ID", text="ID")
    tree_produccion.heading("Nombre", text="Nombre")
    tree_produccion.heading("Cantidad", text="Cantidad")
    tree_produccion.heading("Unidad", text="Unidad")
    tree_produccion.column("ID", width=50, anchor="center")
    tree_produccion.column("Nombre", width=200)
    tree_produccion.column("Cantidad", width=100, anchor="center")
    tree_produccion.column("Unidad", width=100, anchor="center")
    tree_produccion.pack(padx=20, pady=(10, 10), fill="x")

    # Botón para eliminar receta de la lista
    def eliminar_de_produccion():
        seleccion = tree_produccion.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione una receta para eliminar")
            return
        tree_produccion.delete(seleccion[0])
        actualizar_total()

    btn_eliminar = ctk.CTkButton(
        frame_produccion, text="Eliminar Receta", width=150, height=35,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color=("#dc3545", "#dc3545"), hover_color=("#c82333", "#c82333"),
        command=eliminar_de_produccion
    )
    btn_eliminar.pack(padx=20, pady=(0, 10), anchor="w")

    # Etiqueta de total de recetas
    label_total = ctk.CTkLabel(frame_produccion, text="Total recetas: 0", font=ctk.CTkFont(size=16, weight="bold"), text_color="#1f538d")
    label_total.pack(padx=20, anchor="e")

    def actualizar_total():
        total = len(tree_produccion.get_children())
        label_total.configure(text=f"Total recetas: {total}")

    # Botones de acción
    frame_accion = ctk.CTkFrame(frame_produccion, fg_color="transparent")
    frame_accion.pack(fill="x", padx=20, pady=(10, 20))

    def limpiar_todo():
        entry_concepto.delete(0, 'end')
        entry_fecha.delete(0, 'end')
        entry_fecha.insert(0, datetime.now().strftime("%Y-%m-%d"))
        for item in tree_produccion.get_children():
            tree_produccion.delete(item)
        entry_concepto._produccion_id = None
        actualizar_total()

    def grabar_produccion():
        concepto = entry_concepto.get()
        fecha = entry_fecha.get()
        produccion_id = getattr(entry_concepto, '_produccion_id', None)
        if not concepto or not fecha:
            messagebox.showwarning("Campos incompletos", "Ingrese el concepto y la fecha de producción")
            return
        if not tree_produccion.get_children():
            messagebox.showwarning("Advertencia", "Agregue al menos una receta a la producción")
            return
        
        # Verificar stock disponible antes de procesar
        conexion = conectar_bd()
        if not conexion:
            return
        
        cursor = conexion.cursor(dictionary=True)
        try:
            # Verificar stock disponible para cada receta
            for item in tree_produccion.get_children():
                valores = tree_produccion.item(item, 'values')
                receta_id = valores[0]
                cantidad_producir = float(valores[2])
                
                # Obtener ingredientes de la receta
                cursor.execute("""
                    SELECT ri.producto_id, ri.cantidad, p.nombre, p.cantidad_disponible 
                    FROM receta_ingredientes ri 
                    JOIN productos p ON ri.producto_id = p.id 
                    WHERE ri.receta_id = %s
                """, (receta_id,))
                ingredientes = cursor.fetchall()
                
                # Verificar si hay suficiente stock para cada ingrediente
                for ingrediente in ingredientes:
                    cantidad_necesaria = ingrediente['cantidad'] * cantidad_producir
                    stock_disponible = ingrediente['cantidad_disponible']
                    
                    if stock_disponible < cantidad_necesaria:
                        messagebox.showerror("Error de Stock", 
                            f"No hay suficiente stock de '{ingrediente['nombre']}'. "
                            f"Necesario: {cantidad_necesaria}, Disponible: {stock_disponible}")
                        return
            
            # Si llegamos aquí, hay suficiente stock. Proceder con la producción
            if produccion_id:
                # Actualizar producción existente
                cursor.execute(
                    "UPDATE producciones SET concepto=%s, fecha=%s WHERE id=%s",
                    (concepto, fecha, produccion_id)
                )
                cursor.execute("DELETE FROM produccion_detalles WHERE produccion_id=%s", (produccion_id,))
            else:
                cursor.execute(
                    "INSERT INTO producciones (concepto, fecha) VALUES (%s, %s)",
                    (concepto, fecha)
                )
                produccion_id = cursor.lastrowid
            
            # Procesar cada receta en la producción
            for item in tree_produccion.get_children():
                valores = tree_produccion.item(item, 'values')
                receta_id = valores[0]
                cantidad_producir = float(valores[2])
                
                # Insertar detalle de producción
                cursor.execute(
                    "INSERT INTO produccion_detalles (produccion_id, receta_id, cantidad) VALUES (%s, %s, %s)",
                    (produccion_id, receta_id, cantidad_producir)
                )
                
                # Obtener ingredientes de la receta
                cursor.execute("""
                    SELECT ri.producto_id, ri.cantidad 
                    FROM receta_ingredientes ri 
                    WHERE ri.receta_id = %s
                """, (receta_id,))
                ingredientes = cursor.fetchall()
                
                # Descontar ingredientes del inventario
                for ingrediente in ingredientes:
                    cantidad_a_descontar = ingrediente['cantidad'] * cantidad_producir
                    cursor.execute(
                        "UPDATE productos SET cantidad_disponible = cantidad_disponible - %s WHERE id = %s",
                        (cantidad_a_descontar, ingrediente['producto_id'])
                    )
                
                # Obtener el producto que se está produciendo
                cursor.execute("SELECT producto_id FROM recetas WHERE id = %s", (receta_id,))
                producto_producido = cursor.fetchone()
                
                if producto_producido:
                    # Agregar el producto producido al inventario
                    cursor.execute(
                        "UPDATE productos SET cantidad_disponible = cantidad_disponible + %s WHERE id = %s",
                        (cantidad_producir, producto_producido['producto_id'])
                    )
            
            conexion.commit()
            messagebox.showinfo("Éxito", "Producción completada correctamente. Inventario actualizado.")
            limpiar_todo()
            buscar_historial()
            mostrar_productos()  # Actualizar vista de productos
            
        except mysql.connector.Error as err:
            conexion.rollback()
            messagebox.showerror("Error", f"No se pudo completar la producción: {err}")
        finally:
            conexion.close()

    btn_grabar = ctk.CTkButton(
        frame_accion, text="Grabar Producción", width=180, height=40,
        font=ctk.CTkFont(size=16, weight="bold"),
        fg_color=("#1f538d", "#4a9eff"), hover_color=("#1a4a7a", "#3d8ce6"),
        command=grabar_produccion
    )
    btn_grabar.pack(side="right", padx=(10, 0))

    btn_limpiar = ctk.CTkButton(
        frame_accion, text="Limpiar", width=120, height=40,
        font=ctk.CTkFont(size=16, weight="bold"),
        fg_color=("#ffc107", "#ffc107"), hover_color=("#e0a800", "#e0a800"),
        command=limpiar_todo
    )
    btn_limpiar.pack(side="right", padx=(10, 0))

    # Cargar recetas automáticamente al abrir la pantalla
    def cargar_recetas_inicial():
        buscar_recetas_disp()
    
    # Llamar a la función después de un breve delay para asegurar que la interfaz esté lista
    frame_produccion.after(100, cargar_recetas_inicial)

def actualizar_lista_productos_receta_global():
    """Función global para actualizar la lista de productos en recetas"""
    if not combo_producto_receta_global:
        return
    
    conexion = conectar_bd()
    productos = []
    if conexion:
        cursor = conexion.cursor(dictionary=True)
        # Obtener productos que son recetas pero que NO tienen una receta ya asignada
        query = """
            SELECT p.id, p.nombre 
            FROM productos p 
            WHERE p.es_receta = 'si' 
            AND p.estatus = 'activo' 
            AND p.id NOT IN (SELECT producto_id FROM recetas)
            ORDER BY p.nombre
        """
        cursor.execute(query)
        productos = cursor.fetchall()
        conexion.close()
    
    producto_nombres = [f"{p['id']} - {p['nombre']}" for p in productos]
    producto_id_map_global.clear()
    producto_id_map_global.update({f"{p['id']} - {p['nombre']}": p['id'] for p in productos})
    
    # Actualizar el OptionMenu
    combo_producto_receta_global.configure(values=producto_nombres)
    if producto_nombres:
        combo_producto_receta_global.set(producto_nombres[0])
    else:
        combo_producto_receta_global.set("")

# Crear el menú
crear_menu()

# Crear todas las pantallas
crear_pantalla_productos()
crear_pantalla_compras()
crear_pantalla_recetas()
crear_pantalla_produccion()

# Mostrar la pantalla de productos por defecto
mostrar_pantalla(frame_productos)

# Cargar datos al iniciar
mostrar_productos()
mostrar_compras()

# Crear tablas de producción
crear_tablas_produccion()

ventana.mainloop() 