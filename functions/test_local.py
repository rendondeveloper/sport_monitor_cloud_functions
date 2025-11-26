"""
Script para probar las funciones localmente sin subirlas a Firebase.
Ejecutar: python test_local.py
"""
import requests
import json

# URL base del emulador local
EMULATOR_BASE_URL = "http://127.0.0.1:5001"
PROJECT_ID = "sport-monitor"  # Cambia esto por tu Project ID de Firebase


def call_function(function_name: str, data: dict = None):
    """
    Llama a una función callable del emulador local.
    
    Args:
        function_name: Nombre de la función a llamar
        data: Datos a enviar a la función (opcional)
    """
    url = f"{EMULATOR_BASE_URL}/{PROJECT_ID}/us-central1/{function_name}"
    
    payload = {"data": data} if data else {"data": {}}
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error al llamar a la función: {e}")
        if hasattr(e.response, 'text'):
            print(f"Respuesta del servidor: {e.response.text}")
        return None


def test_get_events():
    """Prueba la función get_events"""
    print("\n" + "="*50)
    print("Probando get_events...")
    print("="*50)
    
    result = call_function("get_events")
    
    if result:
        print(f"\n✅ Función ejecutada exitosamente")
        print(f"Resultado: {json.dumps(result, indent=2, ensure_ascii=False)}")
        if isinstance(result, dict) and "result" in result:
            events = result["result"]
            print(f"\n📊 Total de eventos encontrados: {len(events)}")
    else:
        print("\n❌ Error al ejecutar la función")


def test_track_event_checkpoint():
    """Prueba la función track_event_checkpoint"""
    print("\n" + "="*50)
    print("Probando track_event_checkpoint...")
    print("="*50)
    
    # Datos de prueba - ajusta según tus necesidades
    test_data = {
        "eventId": "test-event-id",
        "status": "inProgress",
        "day": "day1"
    }
    
    result = call_function("track_event_checkpoint", test_data)
    
    if result:
        print(f"\n✅ Función ejecutada exitosamente")
        print(f"Resultado: {json.dumps(result, indent=2, ensure_ascii=False)}")
    else:
        print("\n❌ Error al ejecutar la función")


def test_track_competitors():
    """Prueba la función track_competitors"""
    print("\n" + "="*50)
    print("Probando track_competitors...")
    print("="*50)
    
    # Datos de prueba - ajusta según tus necesidades
    test_data = {
        "eventId": "test-event-id",
        "dayId": "day1",
        "status": "inProgress",
        "dayName": "Día 1"
    }
    
    result = call_function("track_competitors", test_data)
    
    if result:
        print(f"\n✅ Función ejecutada exitosamente")
        print(f"Resultado: {json.dumps(result, indent=2, ensure_ascii=False)}")
    else:
        print("\n❌ Error al ejecutar la función")


if __name__ == "__main__":
    print("\n🚀 Iniciando pruebas de funciones locales...")
    print(f"📍 Asegúrate de que el emulador esté corriendo en {EMULATOR_BASE_URL}")
    print(f"💡 Ejecuta: firebase emulators:start\n")
    
    # Probar get_events (la más simple)
    test_get_events()
    
    # Descomenta las siguientes líneas para probar otras funciones
    # test_track_event_checkpoint()
    # test_track_competitors()
    
    print("\n" + "="*50)
    print("✅ Pruebas completadas")
    print("="*50)

