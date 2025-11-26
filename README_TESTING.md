# Guía para Probar Funciones Localmente

Esta guía te ayudará a probar las Firebase Functions localmente sin necesidad de subirlas a Firebase.

## Prerrequisitos

1. **Instalar Firebase CLI** (si no lo tienes):

   ```bash
   npm install -g firebase-tools
   ```

2. **Iniciar sesión en Firebase**:

   ```bash
   firebase login
   ```

3. **Instalar dependencias de Python**:

   ```bash
   cd functions
   python3 -m venv venv
   source venv/bin/activate  # En macOS/Linux
   # o
   venv\Scripts\activate  # En Windows

   pip install -r requirements.txt
   ```

## Opción 1: Usar el Emulador de Firebase (Recomendado)

### 1. Iniciar el Emulador

Desde la raíz del proyecto:

```bash
firebase emulators:start --only functions
```

O si también quieres emular Firestore:

```bash
firebase emulators:start
```

Esto iniciará:

- **Functions Emulator**: `http://127.0.0.1:5001`
- **Firestore Emulator**: `http://127.0.0.1:8080`
- **Emulator UI**: `http://localhost:4000` (interfaz web para ver logs y datos)

### 2. Probar las Funciones

#### Opción A: Usar el script de prueba

1. Asegúrate de tener `requests` instalado:

   ```bash
   pip install requests
   ```

2. Edita `functions/test_local.py` y cambia `PROJECT_ID` por tu Project ID de Firebase

3. Ejecuta el script:
   ```bash
   cd functions
   python test_local.py
   ```

#### Opción B: Usar curl desde la terminal

```bash
# Probar get_events
curl -X POST http://127.0.0.1:5001/sport-monitor/us-central1/get_events \
  -H "Content-Type: application/json" \
  -d '{"data": {}}'

# Probar track_event_checkpoint
curl -X POST http://127.0.0.1:5001/sport-monitor/us-central1/track_event_checkpoint \
  -H "Content-Type: application/json" \
  -d '{"data": {"eventId": "test-id", "status": "inProgress", "day": "day1"}}'
```

#### Opción C: Usar la UI del Emulador

1. Abre `http://localhost:4000` en tu navegador
2. Ve a la sección "Functions"
3. Selecciona la función que quieres probar
4. Ingresa los datos de prueba y ejecuta

## Opción 2: Probar con Python directamente

Puedes crear un script que importe y llame directamente a las funciones:

```python
# test_direct.py
from firebase_admin import initialize_app, firestore
from events_customer.events_customer import get_events
from firebase_functions import CallableRequest

# Inicializar Firebase Admin (usará credenciales locales o variables de entorno)
initialize_app()

# Crear un request mock
class MockRequest:
    def __init__(self, data=None):
        self.data = data or {}

# Probar get_events
req = MockRequest()
result = get_events(req)
print(result)
```

## Configuración de Firestore Local

Si necesitas datos de prueba en Firestore:

1. Crea un archivo `firestore.rules` (si no existe)
2. Crea datos de prueba en `firestore_export/` o usa la UI del emulador
3. El emulador cargará automáticamente los datos

## Solución de Problemas

### Error: "Port already in use"

Si el puerto está ocupado, cambia los puertos en `firebase.json`:

```json
"emulators": {
  "functions": {
    "port": 5002  // Cambia el puerto
  }
}
```

### Error: "Module not found"

Asegúrate de estar en el entorno virtual y de tener todas las dependencias instaladas:

```bash
cd functions
source venv/bin/activate
pip install -r requirements.txt
```

### Error: "Firebase project not found"

Asegúrate de tener un archivo `.firebaserc` con tu proyecto configurado:

```json
{
  "projects": {
    "default": "tu-project-id"
  }
}
```

## Variables de Entorno

Si necesitas variables de entorno para el emulador, crea un archivo `.env` o usa:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="path/to/credentials.json"
firebase emulators:start
```

## Detener el Emulador

Presiona `Ctrl+C` en la terminal donde está corriendo el emulador.

## Recursos Adicionales

- [Documentación del Emulador de Firebase](https://firebase.google.com/docs/emulator-suite)
- [Firebase Functions Testing](https://firebase.google.com/docs/functions/unit-testing)
