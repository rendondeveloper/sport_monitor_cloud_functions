# Optimizaciones para Firebase Functions

## Optimizaciones Aplicadas en get_events

### 1. ✅ Eliminado Logging Innecesario
- Removido `logging.debug()` dentro del loop
- Solo se registran errores críticos
- **Impacto**: Reduce tiempo de ejecución significativamente

### 2. ✅ Procesamiento Simplificado
- Conversión directa sin pasos intermedios innecesarios
- Uso eficiente del modelo EventDocument

## Optimizaciones Adicionales Recomendadas

### 3. Usar Select() para Limitar Campos (Si no necesitas todos)
```python
# Si solo necesitas ciertos campos, puedes usar select()
events_query = events_ref.select(["name", "description", "status", "createdAt"])
events_docs = events_query.get()
```
**Impacto**: Reduce el tamaño de datos transferidos

### 4. Implementar Cache (Para datos que no cambian frecuentemente)
```python
from functools import lru_cache
import time

# Cache por 5 minutos
@lru_cache(maxsize=1)
def get_cached_events(cache_key):
    # Tu lógica aquí
    pass
```
**Impacto**: Respuestas instantáneas para datos cacheados

### 5. Paginación (Si hay muchos eventos)
```python
# Limitar resultados iniciales
events_query = events_ref.limit(50)
events_docs = events_query.get()
```
**Impacto**: Reduce tiempo de procesamiento y transferencia

### 6. Usar Streaming (Para grandes volúmenes)
```python
# Procesar documentos mientras se reciben
for doc in events_ref.stream():
    # Procesar cada documento inmediatamente
    pass
```
**Impacto**: Mejora la percepción de velocidad

### 7. Procesamiento Paralelo (Si hay muchas transformaciones)
```python
from concurrent.futures import ThreadPoolExecutor

def process_event(doc):
    # Procesar documento
    pass

with ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(process_event, events_docs))
```
**Impacto**: Procesa múltiples documentos simultáneamente

### 8. Índices en Firestore
Asegúrate de tener índices creados para las queries que uses:
- Firebase Console → Firestore → Indexes
- Crea índices compuestos si usas múltiples filtros

### 9. Reducir Tamaño de Respuesta
Si no necesitas todos los campos del modelo:
```python
# Crear un método to_dict_lightweight() en EventDocument
def to_dict_lightweight(self) -> dict:
    return {
        "id": self.id,
        "name": self.name,
        "status": self.status.value,
        # Solo campos esenciales
    }
```

### 10. Usar Firestore Batch Reads
```python
# Leer múltiples documentos en batch
doc_refs = [db.collection("events").document(id) for id in event_ids]
docs = db.get_all(doc_refs)
```
**Impacto**: Reduce número de round-trips a Firestore

## Métricas a Monitorear

1. **Cold Start Time**: Tiempo de inicialización de la función
2. **Execution Time**: Tiempo de procesamiento
3. **Memory Usage**: Uso de memoria
4. **Network Latency**: Tiempo de red con Firestore

## Recomendaciones Específicas para tu Caso

Dado que tu función tarda 888ms:

1. **Si tienes muchos eventos (>50)**: Implementa paginación
2. **Si los eventos no cambian frecuentemente**: Implementa cache
3. **Si solo necesitas campos específicos**: Usa select()
4. **Si el problema es la red**: Verifica la latencia con Firestore
5. **Si el problema es el procesamiento**: Optimiza el modelo EventDocument

## Verificar Dónde está el Cuello de Botella

```python
import time

start = time.time()
events_docs = events_ref.get()
fetch_time = time.time() - start
print(f"Firestore fetch: {fetch_time}ms")

start = time.time()
# Procesamiento
process_time = time.time() - start
print(f"Processing: {process_time}ms")
```

Esto te ayudará a identificar si el problema es:
- **Red/Firestore**: Tiempo de fetch alto
- **Procesamiento**: Tiempo de conversión alto

