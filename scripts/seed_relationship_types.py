"""
Script de seed para el catálogo de tipos de relación (relationship_types).

Crea los documentos en Firestore en la ruta:
  catalogs/default/relationship_types/{docId}

Uso:
    python scripts/seed_relationship_types.py

Requiere que las credenciales de Firebase estén configuradas:
  - Variable de entorno GOOGLE_APPLICATION_CREDENTIALS apuntando al service account JSON, o
  - Estar autenticado con `gcloud auth application-default login`
"""

import firebase_admin
from firebase_admin import credentials, firestore

RELATIONSHIP_TYPES = [
    {"label": "Padre", "order": 1},
    {"label": "Madre", "order": 2},
    {"label": "Cónyuge / Esposo(a)", "order": 3},
    {"label": "Hijo", "order": 4},
    {"label": "Hija", "order": 5},
    {"label": "Hermano", "order": 6},
    {"label": "Hermana", "order": 7},
    {"label": "Abuelo", "order": 8},
    {"label": "Abuela", "order": 9},
    {"label": "Tío", "order": 10},
    {"label": "Tía", "order": 11},
    {"label": "Sobrino", "order": 12},
    {"label": "Sobrina", "order": 13},
    {"label": "Pareja", "order": 14},
    {"label": "Amigo(a)", "order": 15},
    {"label": "Compañero(a) de trabajo", "order": 16},
    {"label": "Entrenador(a)", "order": 17},
    {"label": "Médico(a)", "order": 18},
    {"label": "Tutor legal", "order": 19},
    {"label": "Otro", "order": 20},
]


def seed():
    if not firebase_admin._apps:
        firebase_admin.initialize_app()

    db = firestore.client()
    ref = (
        db.collection("catalogs")
        .document("default")
        .collection("relationship_types")
    )

    # Verificar si ya existen documentos
    existing = list(ref.limit(1).stream())
    if existing:
        print("El catálogo ya tiene datos. Abortando para evitar duplicados.")
        print("Para forzar la re-creación, elimina los documentos manualmente primero.")
        return

    created = 0
    for item in RELATIONSHIP_TYPES:
        ref.add(item)
        print(f"  ✓ Creado: {item['label']}")
        created += 1

    print(f"\nSeed completado: {created} tipos de relación creados.")
    print("Ruta Firestore: catalogs/default/relationship_types/")


if __name__ == "__main__":
    seed()
