import os

class Config:
    """Configuración base de la aplicación"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'tu_clave_secreta_aqui_123456'
    
    # Configuración de MySQL
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'comandas-javiersopor9-20f5.j.aivencloud.com')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 11906))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'avnadmin')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'AVNS_00hEQzD6sm3WO-V3bV0')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'comandas')
    
    # Configuración de SSL
    MYSQL_SSL_CA = os.environ.get('MYSQL_SSL_CA') or os.path.join(os.path.dirname(__file__), 'ca.pem')
    
    # Configuración de la aplicación
    FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Configuración de sesión
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hora en segundos
    
    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    DEBUG = True
    FLASK_ENV = 'development'

class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False
    FLASK_ENV = 'production'

class TestingConfig(Config):
    """Configuración para testing"""
    TESTING = True
    DEBUG = True

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': ProductionConfig
} 