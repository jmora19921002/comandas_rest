#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

def crear_tablas_inventario():
    """Crear las tablas necesarias del sistema de inventario"""
    try:
        url = "http://localhost:5000/api/inventario/crear-tablas"
        headers = {"Content-Type": "application/json"}
        data = {}
        
        print(f"Haciendo POST a: {url}")
        response = requests.post(url, headers=headers, json=data)
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Response Text: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print("Resultado JSON:", result)
                if result.get('success'):
                    print("✅ Tablas creadas correctamente")
                else:
                    print("❌ Error al crear tablas:", result.get('message'))
            except json.JSONDecodeError as e:
                print(f"❌ Error al decodificar JSON: {e}")
                print("Respuesta no es JSON válido")
        else:
            print(f"❌ Error HTTP: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error de conexión: {e}")

if __name__ == "__main__":
    print("Verificando y creando tablas de inventario...")
    crear_tablas_inventario() 