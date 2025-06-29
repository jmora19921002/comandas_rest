# Sistema de Comandas REST

Sistema de gestión de comandas para restaurantes con funcionalidades de inventario, impresión de tickets y gestión de mesas.

## Características

- Gestión de mesas y comandas
- Sistema de inventario completo
- Impresión de tickets
- Gestión de usuarios y roles
- Reportes de ventas
- Dashboard administrativo
- Monitor de cocina

## Despliegue en Render

### Opción 1: Despliegue Automático con render.yaml

1. Sube tu código a GitHub
2. Ve a [Render Dashboard](https://dashboard.render.com/)
3. Haz clic en "New +" y selecciona "Web Service"
4. Conecta tu repositorio de GitHub
5. Render detectará automáticamente el archivo `render.yaml` y configurará todo

### Opción 2: Configuración Manual

Si prefieres configurar manualmente:

1. Ve a [Render Dashboard](https://dashboard.render.com/)
2. Haz clic en "New +" y selecciona "Web Service"
3. Conecta tu repositorio de GitHub
4. Configura el servicio:

#### Configuración Básica:
- **Name**: `comandas-rest` (o el nombre que prefieras)
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

#### Variables de Entorno:
Configura las siguientes variables de entorno en Render:

```
FLASK_ENV=production
FLASK_DEBUG=false
MYSQL_HOST=comandas-javiersopor9-20f5.j.aivencloud.com
MYSQL_PORT=11906
MYSQL_USER=avnadmin
MYSQL_PASSWORD=AVNS_00hEQzD6sm3WO-V3bV0
MYSQL_DB=comandas
SECRET_KEY=tu_clave_secreta_muy_segura_aqui
```

### 3. Despliegue Automático

Una vez configurado, Render desplegará automáticamente tu aplicación cada vez que hagas push a la rama principal.

### 4. Verificación

Después del despliegue, puedes acceder a tu aplicación en la URL proporcionada por Render.

## Estructura del Proyecto

```
comandas_rest/
├── app.py                 # Aplicación principal Flask
├── config.py              # Configuración de la aplicación
├── requirements.txt       # Dependencias de Python
├── render.yaml           # Configuración de Render
├── start.sh              # Script de inicio
├── .gitignore           # Archivos a excluir
├── README.md            # Este archivo
├── env.example          # Ejemplo de variables de entorno
├── static/              # Archivos estáticos (CSS, JS, imágenes)
├── templates/           # Plantillas HTML
└── ca.pem              # Certificado SSL para MySQL (si es necesario)
```

## Configuración de Base de Datos

La aplicación está configurada para usar MySQL en Aiven Cloud. Asegúrate de que:

1. La base de datos esté creada y accesible
2. Las credenciales en las variables de entorno sean correctas
3. El certificado SSL esté configurado correctamente

## Desarrollo Local

Para ejecutar la aplicación localmente:

1. Instala las dependencias:
```bash
pip install -r requirements.txt
```

2. Configura las variables de entorno (copia `env.example` a `.env`):
```bash
cp env.example .env
```

3. Ejecuta la aplicación:
```bash
python app.py
```

## Funcionalidades Principales

### Gestión de Comandas
- Crear y editar comandas por mesa
- Agregar items con cantidades y notas
- Calcular totales automáticamente
- Imprimir tickets de comanda

### Sistema de Inventario
- Gestión de productos
- Control de stock
- Compras y proveedores
- Recetas y producción
- Movimientos de inventario

### Impresión
- Soporte para impresoras de red
- Impresión de tickets ESC/POS
- Asignación de impresoras por grupos

### Reportes
- Reporte de ventas por período
- Exportación a PDF
- Dashboard con estadísticas

## Notas Importantes

1. **Impresión**: Las funciones de impresión están adaptadas para funcionar tanto en Windows como en Linux
2. **SSL**: La aplicación maneja automáticamente la configuración SSL para la base de datos
3. **Variables de Entorno**: Todas las configuraciones sensibles están en variables de entorno
4. **Logs**: Los logs se muestran en la consola de Render
5. **Configuración**: La aplicación usa un sistema de configuración basado en clases para diferentes entornos

## Solución de Problemas

### Error de Conexión a Base de Datos
- Verifica que las credenciales de MySQL sean correctas
- Asegúrate de que la base de datos esté accesible desde Render
- Revisa los logs en el dashboard de Render

### Error de Dependencias
- Verifica que todas las dependencias estén en `requirements.txt`
- Asegúrate de que las versiones sean compatibles

### Error de Puerto
- Render asigna automáticamente el puerto a través de la variable `PORT`
- No configures manualmente el puerto en el código

## Soporte

Para problemas o preguntas sobre el despliegue:
1. Revisa los logs en el dashboard de Render
2. Consulta la documentación de Flask y Render
3. Verifica que todas las variables de entorno estén configuradas correctamente 