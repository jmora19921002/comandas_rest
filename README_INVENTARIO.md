# Sistema de Inventario Completo

## Descripción
Este sistema de inventario completo ha sido transformado desde una aplicación Tkinter a Flask, integrado en el sistema de comandas existente. Incluye gestión de productos, compras, recetas y producción.

## Funcionalidades Principales

### 1. Gestión de Productos (`/manager/inventario/productos`)
- **Crear productos**: Agregar nuevos productos con nombre, cantidad, unidad de medida, costo, ganancia y precio de venta
- **Editar productos**: Modificar información de productos existentes
- **Eliminar productos**: Remover productos (solo si no están en uso)
- **Cálculo automático**: El sistema calcula automáticamente el precio de venta basado en costo y ganancia
- **Tipos de producto**: Distinguir entre productos regulares y productos de receta

### 2. Gestión de Compras (`/manager/inventario/compras`)
- **Registrar compras**: Crear registros de compras con proveedor, fecha y productos
- **Actualizar inventario**: Al registrar una compra, se actualiza automáticamente el stock de los productos
- **Historial de compras**: Ver todas las compras realizadas
- **Búsqueda de productos**: Buscar productos disponibles para agregar a la compra

### 3. Gestión de Recetas (`/manager/inventario/recetas`)
- **Crear recetas**: Definir recetas con ingredientes y cantidades
- **Editar recetas**: Modificar ingredientes y cantidades de recetas existentes
- **Eliminar recetas**: Remover recetas (solo si no están en uso en producción)
- **Búsqueda de ingredientes**: Buscar productos disponibles para usar como ingredientes
- **Validaciones**: Asegurar que un producto solo tenga una receta asignada

### 4. Gestión de Producción (`/manager/inventario/produccion`)
- **Registrar producción**: Crear registros de producción con concepto, fecha y recetas
- **Actualizar inventario**: Al producir, se descuentan los ingredientes y se aumenta el stock del producto final
- **Historial de producción**: Ver todas las producciones realizadas
- **Editar producción**: Modificar detalles de producción existente
- **Eliminar producción**: Remover registros de producción

## Estructura de Base de Datos

### Tablas Principales

#### `productos`
```sql
CREATE TABLE productos (
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
);
```

#### `compras`
```sql
CREATE TABLE compras (
    id INT AUTO_INCREMENT PRIMARY KEY,
    proveedor VARCHAR(100) NOT NULL,
    fecha DATE NOT NULL,
    total DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `compra_items`
```sql
CREATE TABLE compra_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    compra_id INT NOT NULL,
    producto_id INT NOT NULL,
    cantidad DECIMAL(10,2) NOT NULL,
    precio_unitario DECIMAL(10,2) NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (compra_id) REFERENCES compras(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
);
```

#### `recetas`
```sql
CREATE TABLE recetas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    producto_id INT NOT NULL,
    unidad_producida DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
);
```

#### `receta_ingredientes`
```sql
CREATE TABLE receta_ingredientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    receta_id INT NOT NULL,
    producto_id INT NOT NULL,
    cantidad DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (receta_id) REFERENCES recetas(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
);
```

#### `producciones`
```sql
CREATE TABLE producciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    concepto VARCHAR(255) NOT NULL,
    fecha DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `produccion_detalles`
```sql
CREATE TABLE produccion_detalles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    produccion_id INT NOT NULL,
    receta_id INT NOT NULL,
    cantidad DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (produccion_id) REFERENCES producciones(id) ON DELETE CASCADE,
    FOREIGN KEY (receta_id) REFERENCES recetas(id) ON DELETE CASCADE
);
```

## Rutas API

### Productos
- `GET /manager/inventario/productos` - Vista de productos
- `POST /api/inventario/productos` - Crear producto
- `PUT /api/inventario/productos/<id>` - Actualizar producto
- `DELETE /api/inventario/productos/<id>` - Eliminar producto
- `GET /api/inventario/productos/buscar` - Buscar productos
- `GET /api/inventario/productos/receta` - Productos disponibles para recetas

### Compras
- `GET /manager/inventario/compras` - Vista de compras
- `POST /api/inventario/compras` - Crear compra

### Recetas
- `GET /manager/inventario/recetas` - Vista de recetas
- `POST /api/inventario/recetas` - Crear receta
- `GET /api/inventario/recetas/<id>` - Obtener receta
- `PUT /api/inventario/recetas/<id>` - Actualizar receta
- `DELETE /api/inventario/recetas/<id>` - Eliminar receta

### Producción
- `GET /manager/inventario/produccion` - Vista de producción
- `POST /api/inventario/produccion` - Crear producción
- `GET /api/inventario/produccion/<id>` - Obtener producción
- `PUT /api/inventario/produccion/<id>` - Actualizar producción
- `DELETE /api/inventario/produccion/<id>` - Eliminar producción
- `GET /api/inventario/recetas/disponibles` - Recetas disponibles para producción

### Utilidades
- `POST /api/inventario/crear-tablas` - Crear tablas necesarias (solo soporte)

## Instalación y Configuración

### 1. Crear las tablas
Acceder como usuario con rol de soporte y usar la función "Crear Tablas" en el menú de sistema.

### 2. Configurar productos
1. Ir a "Inventario Completo" > "Productos"
2. Crear los productos base del negocio
3. Marcar como "Sí" los productos que serán recetas

### 3. Configurar recetas
1. Ir a "Inventario Completo" > "Recetas"
2. Seleccionar un producto de receta
3. Agregar los ingredientes necesarios con sus cantidades

### 4. Registrar compras iniciales
1. Ir a "Inventario Completo" > "Compras"
2. Registrar las compras iniciales de ingredientes

### 5. Registrar producción
1. Ir a "Inventario Completo" > "Producción"
2. Crear registros de producción usando las recetas configuradas

## Características Técnicas

### Validaciones
- Cantidades no pueden ser negativas
- Precios deben ser mayores a 0
- Un producto solo puede tener una receta
- No se pueden eliminar productos/recetas en uso
- Verificación de stock disponible en producción

### Cálculos Automáticos
- Precio de venta = Costo + (Costo × Ganancia / 100)
- Ganancia = ((Precio de venta - Costo) / Costo) × 100
- Total de compra = Suma de (cantidad × precio) de todos los items
- Stock se actualiza automáticamente en compras y producción

### Interfaz de Usuario
- Diseño responsive con Bootstrap
- DataTables para listas con búsqueda y paginación
- Modales para formularios
- Validaciones en tiempo real
- Notificaciones de éxito/error

## Permisos
- **Admin**: Acceso completo a todas las funcionalidades
- **Soporte**: Solo puede crear tablas del sistema
- **Otros roles**: Sin acceso al sistema de inventario

## Notas de Implementación
- El sistema está completamente integrado con el sistema de comandas existente
- Utiliza la misma base de datos y sistema de autenticación
- Mantiene la consistencia de datos con transacciones SQL
- Incluye manejo de errores y validaciones robustas
- Interfaz moderna y fácil de usar 