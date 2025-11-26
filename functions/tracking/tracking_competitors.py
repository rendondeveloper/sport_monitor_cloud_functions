from firebase_functions import https_fn
from firebase_admin import firestore
import logging
from datetime import datetime, timezone
from models.event_document import EventDocument, EventStatus
from models.checkpoint_tracking import CheckpointType
from utils.helpers import format_utc_to_local_datetime


@https_fn.on_call()
def track_competitors(req: https_fn.CallableRequest) -> dict:
    """
    Función que recibe eventId, dayId y status.
    Si el status es 'inProgress', toma los datos del evento y crea
    la estructura de tracking de competidores optimizada para actualizaciones granulares.
    """
    try:
        # Obtener datos de la petición callable
        data = req.data
        logging.info(f"track_competitors: Iniciando función con datos: {data}")

        # Validar parámetros requeridos
        if (
            not data
            or "eventId" not in data
            or "dayId" not in data
            or "status" not in data
        ):
            logging.error("track_competitors: Parámetros requeridos faltantes")
            raise https_fn.HttpsError(
                code="invalid-argument",
                message="Se requieren los parámetros 'eventId', 'dayId' y 'status'",
            )

        event_id = data["eventId"]
        day_id = data["dayId"]
        day_status = data["status"]
        day_name = data["dayName"]

        logging.info(
            f"track_competitors: Procesando evento {event_id}, día {day_id}, status {day_status}, nombre del día {day_name}"
        )

        # Inicializar Firestore
        db = firestore.client()

        # Buscar el evento
        logging.info(f"track_competitors: Buscando evento {event_id} en Firestore")
        event_ref = db.collection("events").document(event_id)
        event_doc = event_ref.get()

        if not event_doc.exists:
            logging.error(
                f"track_competitors: Evento {event_id} no encontrado en Firestore"
            )
            raise https_fn.HttpsError(
                code="not-found", message=f"Evento con ID {event_id} no encontrado"
            )

        logging.info(f"track_competitors: Evento {event_id} encontrado en Firestore")

        # Mapear el documento del evento al modelo
        event_data = event_doc.to_dict()
        event = EventDocument.from_dict(event_data, event_id)
        logging.info(
            f"track_competitors: Evento mapeado - Nombre: {event.name}, Estado: {event.status.value}"
        )

        # Validar: solo continuar si el evento está en progreso
        if event.status != EventStatus.IN_PROGRESS:
            logging.warning(
                f"track_competitors: Evento {event.name} no está en progreso. Estado actual: {event.status.display_name}"
            )
            return {
                "success": False,
                "message": f"El evento '{event.name}' no está en progreso (estado actual: {event.status.display_name}).",
                "event_id": event_id,
                "day_id": day_id,
                "event_status": event.status.value,
            }

        # Obtener checkpoints desde la subcolección events/{eventId}/checkpoints
        # Filtrar solo los checkpoints asociados al día específico usando dayOfRaceId
        logging.info(
            f"track_competitors: Buscando checkpoints en events/{event_id}/checkpoints filtrados por dayOfRaceId={day_id}"
        )
        checkpoints_ref = db.collection(f"events/{event_id}/checkpoints")
        # Filtrar checkpoints que contengan el day_id en el array dayOfRaceId
        checkpoints_query = checkpoints_ref.where(
            "dayOfRaceId", "array_contains", day_id
        )
        checkpoints_docs = checkpoints_query.get()

        logging.info(
            f"track_competitors: Encontrados {len(checkpoints_docs)} checkpoints asociados al día {day_id}"
        )

        # Obtener participantes desde la subcolección events/{eventId}/participants
        logging.info(
            f"track_competitors: Buscando participantes en events/{event_id}/participants"
        )
        participants_ref = db.collection(f"events/{event_id}/participants")
        participants_docs = participants_ref.get()

        logging.info(
            f"track_competitors: Encontrados {len(participants_docs)} participantes en la subcolección"
        )

        # Obtener categorías del evento para mapear IDs con descripciones
        # La colección es event_categories y el campo de descripción es 'name'
        logging.info(
            f"track_competitors: Buscando categorías en events/{event_id}/event_categories"
        )
        categories_ref = db.collection(f"events/{event_id}/event_categories")
        categories_docs = categories_ref.get()

        # Crear mapa de categorías: ID -> descripción
        # El ID es el document ID y la descripción está en el campo 'name'
        categories_map = {}
        for category_doc in categories_docs:
            category_data = category_doc.to_dict()
            if category_data is None:
                continue

            category_id = category_doc.id
            # El campo 'name' contiene la descripción/nombre de la categoría
            category_description = category_data.get("name", "Sin descripción")
            categories_map[category_id] = category_description
            logging.debug(
                f"track_competitors: Categoría mapeada - ID: {category_id}, name (descripción): {category_description}"
            )

        # Si no hay categorías en la colección, crear un mapa desde los participantes
        if len(categories_map) == 0:
            logging.info(
                f"track_competitors: No se encontraron categorías en la colección. Creando mapa desde participantes..."
            )
            for participant_doc in participants_docs:
                participant_data = participant_doc.to_dict()
                competition_category = participant_data.get("competitionCategory", {})
                category_id = competition_category.get(
                    "id"
                ) or competition_category.get("registrationCategory")
                category_description = competition_category.get(
                    "registrationCategory", "Sin categoría"
                )

                if category_id and category_id not in categories_map:
                    categories_map[category_id] = category_description
                    logging.debug(
                        f"track_competitors: Categoría desde participante - ID: {category_id}, Descripción: {category_description}"
                    )

        logging.info(
            f"track_competitors: Mapa de categorías creado con {len(categories_map)} categorías"
        )

        # Obtener routes desde la subcolección events/{eventId}/routes
        # Filtrar solo las routes asociadas al día específico usando dayOfRaceId
        logging.info(
            f"track_competitors: Buscando routes en events/{event_id}/routes filtradas por dayOfRaceId={day_id}"
        )
        routes_ref = db.collection(f"events/{event_id}/routes")

        # Primero obtener todas las routes para debug
        all_routes_docs = routes_ref.get()
        logging.info(
            f"track_competitors: Total de routes en el evento: {len(all_routes_docs)}"
        )

        if len(all_routes_docs) > 0:
            # Mostrar información de las primeras routes para debug
            for i, route_doc in enumerate(all_routes_docs[:3]):  # Primeras 3 para debug
                route_data = route_doc.to_dict()
                day_of_race_ids = route_data.get("dayOfRaceIds", [])
                logging.info(
                    f"track_competitors: Route {route_doc.id} - name: {route_data.get('name', 'N/A')}, dayOfRaceIds: {day_of_race_ids}"
                )

        # Filtrar routes que contengan el day_id en el array dayOfRaceIds
        routes_query = routes_ref.where("dayOfRaceIds", "array_contains", day_id)
        routes_docs = routes_query.get()

        logging.info(
            f"track_competitors: Encontradas {len(routes_docs)} routes asociadas al día {day_id}"
        )

        if len(routes_docs) == 0:
            logging.warning(
                f"track_competitors: No se encontraron routes para el día {day_id}. Verificar que las routes tengan el campo 'dayOfRaceIds' (array) que contenga el valor '{day_id}'"
            )

        # Crear el documento principal de tracking
        tracking_doc_id = f"{event_id}_{day_id}"
        collection_path = f"events_tracking/{event_id}/competitor_tracking"

        logging.info(
            f"track_competitors: Creando estructura optimizada con ID: {tracking_doc_id}"
        )

        # Crear documento principal con metadata
        main_doc_ref = db.collection(collection_path).document(tracking_doc_id)

        main_doc_data = {
            "eventId": event_id,
            "dayId": day_id,
            "dayName": day_name,
            "isActive": day_status,
            "createdAt": format_utc_to_local_datetime(datetime.utcnow()),
            "updatedAt": format_utc_to_local_datetime(datetime.utcnow()),
        }

        main_doc_ref.set(main_doc_data)
        logging.info(f"track_competitors: Documento principal creado")

        # Crear subcolección de routes (al mismo nivel que competitors)
        # Las routes son generales para todos los competidores
        routes_collection_ref = main_doc_ref.collection("routes")
        routes_created = []

        if len(routes_docs) > 0:
            logging.info(
                f"track_competitors: Creando {len(routes_docs)} documentos de routes en la colección 'routes'"
            )

            for route_doc in routes_docs:
                try:
                    route_data = route_doc.to_dict()
                    route_id = route_doc.id

                    # Validar que route_data no sea None
                    if route_data is None:
                        logging.warning(
                            f"track_competitors: Route {route_id} tiene datos None, saltando..."
                        )
                        continue

                    route_doc_ref = routes_collection_ref.document(route_id)

                    # Mapear categoryIds a objetos con id y description
                    category_ids = route_data.get("categoryIds", [])
                    categories_with_description = []

                    for cat_id in category_ids:
                        category_info = {
                            "id": cat_id,
                            "description": categories_map.get(
                                cat_id, "Categoría no encontrada"
                            ),
                        }
                        categories_with_description.append(category_info)

                    # Obtener los checkpoints asociados a esta route
                    checkpoint_ids_list = []
                    for checkpoint_doc_item in checkpoints_docs:
                        checkpoint_data_item = checkpoint_doc_item.to_dict()
                        event_route_ids = checkpoint_data_item.get("eventRouteId", [])

                        # Si este checkpoint tiene el route_id en su eventRouteId
                        if route_id in event_route_ids:
                            checkpoint_item_id = checkpoint_doc_item.id
                            checkpoint_ids_list.append(checkpoint_item_id)

                    route_tracking_data = {
                        "name": route_data.get("name", ""),
                        "routeUrl": route_data.get("routeUrl", ""),
                        "categories": categories_with_description,
                        "checkpointIds": checkpoint_ids_list,  # Lista de IDs de checkpoints
                        "createdAt": format_utc_to_local_datetime(datetime.utcnow()),
                        "updatedAt": format_utc_to_local_datetime(datetime.utcnow()),
                    }

                    route_doc_ref.set(route_tracking_data)

                    routes_created.append(
                        {
                            "routeId": route_id,
                            "routeName": route_data.get("name", "Route"),
                            "routeUrl": route_data.get("routeUrl", ""),
                            "checkpointsCount": len(checkpoint_ids_list),
                        }
                    )
                    logging.info(
                        f"track_competitors: Route {route_id} creada exitosamente: {route_data.get('name', 'Route')} con {len(checkpoint_ids_list)} checkpoints"
                    )
                except Exception as e:
                    logging.error(
                        f"track_competitors: Error al crear route {route_doc.id}: {str(e)}",
                        exc_info=True,
                    )
                    continue

            logging.info(
                f"track_competitors: {len(routes_created)} routes creadas exitosamente de {len(routes_docs)} encontradas"
            )
        else:
            logging.info(
                f"track_competitors: No hay routes para crear (0 routes encontradas para el día {day_id})"
            )

        # Crear subcolección de competidores
        competitors_collection_ref = main_doc_ref.collection("competitors")

        competitors_created = []
        logging.info(
            f"track_competitors: Creando {len(participants_docs)} documentos de competidores"
        )

        # Preparar lista de participantes con timeToStart para ordenar
        participants_with_time = []
        participants_without_time = []

        for participant_doc in participants_docs:
            participant_data = participant_doc.to_dict()

            # Extraer datos del participante
            personal_data = participant_data.get("personalData", {})
            competition_category = participant_data.get("competitionCategory", {})

            # Buscar timestoStart (Map<String, DateTime>) y verificar si day_id existe
            time_start_map = participant_data.get("timesToStart", {})
            time_to_start = None

            if time_start_map and day_id in time_start_map:
                # Obtener el valor DateTime del mapa
                time_start_value = time_start_map[day_id]

                # Convertir Timestamp de Firestore a datetime si es necesario
                # Firebase Admin convierte automáticamente Timestamps a datetime con .to_dict()
                # pero puede haber casos donde sea necesario manejar diferentes tipos
                if isinstance(time_start_value, datetime):
                    # Ya es un datetime (caso más común con Firebase Admin)
                    time_to_start = time_start_value
                    # Asegurar que esté en UTC si no tiene timezone
                    if time_to_start.tzinfo is None:
                        time_to_start = time_to_start.replace(tzinfo=timezone.utc)
                elif hasattr(time_start_value, "timestamp") and callable(
                    getattr(time_start_value, "timestamp", None)
                ):
                    # Es un Timestamp de Firestore (verificación por método timestamp)
                    try:
                        # Intentar convertir usando el método timestamp
                        timestamp_seconds = time_start_value.timestamp()
                        time_to_start = datetime.fromtimestamp(
                            timestamp_seconds, tz=timezone.utc
                        )
                    except (AttributeError, TypeError):
                        # Si tiene método to_datetime, usarlo
                        if hasattr(time_start_value, "to_datetime"):
                            time_to_start = time_start_value.to_datetime()
                            if time_to_start.tzinfo is None:
                                time_to_start = time_to_start.replace(
                                    tzinfo=timezone.utc
                                )
                        else:
                            time_to_start = None
                elif isinstance(time_start_value, str):
                    # Es un string, intentar parsearlo
                    try:
                        time_to_start = datetime.fromisoformat(
                            time_start_value.replace("Z", "+00:00")
                        )
                    except:
                        logging.warning(
                            f"track_competitors: No se pudo parsear timeStart para participante {participant_doc.id}, día {day_id}"
                        )
                        time_to_start = None
                else:
                    logging.warning(
                        f"track_competitors: Tipo de timeStart no reconocido para participante {participant_doc.id}, día {day_id}: {type(time_start_value)}"
                    )
                    time_to_start = None

                logging.debug(
                    f"track_competitors: Participante {participant_doc.id} tiene timeToStart: {time_to_start} para día {day_id}"
                )

            # Crear estructura temporal con los datos del participante
            participant_info = {
                "doc": participant_doc,
                "data": participant_data,
                "personal_data": personal_data,
                "competition_category": competition_category,
                "time_to_start": time_to_start,
            }

            if time_to_start is not None:
                participants_with_time.append(participant_info)
            else:
                participants_without_time.append(participant_info)

        # Ordenar participantes con timeToStart del más antiguo al más nuevo
        participants_with_time.sort(
            key=lambda x: x["time_to_start"] if x["time_to_start"] else datetime.max
        )

        # Combinar listas: primero los que tienen timeToStart (ordenados), luego los que no
        sorted_participants = participants_with_time + participants_without_time

        logging.info(
            f"track_competitors: {len(participants_with_time)} participantes con timeToStart, {len(participants_without_time)} sin timeToStart"
        )

        # Crear documentos de competidores en el orden correcto
        for i, participant_info in enumerate(sorted_participants):
            participant_doc = participant_info["doc"]
            participant_data = participant_info["data"]
            personal_data = participant_info["personal_data"]
            competition_category = participant_info["competition_category"]
            time_to_start = participant_info["time_to_start"]

            # Crear documento del competidor
            competitor_id = participant_doc.id
            competitor_doc_ref = competitors_collection_ref.document(competitor_id)

            competitor_data = {
                "id": competitor_id,
                "name": personal_data.get("fullName", "Competidor"),
                # Asigna el orden del competidor:
                # Si pilotNumber existe y es un número válido, usa ese número como el order.
                # Si no, usa el índice del ciclo + 1 (i + 1) como valor por defecto.
                "order": (
                    int(competition_category.get("pilotNumber", i + 1))
                    if competition_category.get("pilotNumber") is not None
                    and str(competition_category.get("pilotNumber")).isdigit()
                    else int(i + 1)
                ),
                "category": competition_category.get(
                    "registrationCategory", "Sin categoría"
                ),
                "number": competition_category.get("pilotNumber", "Sin número"),
                "createdAt": format_utc_to_local_datetime(datetime.utcnow()),
                "updatedAt": format_utc_to_local_datetime(datetime.utcnow()),
            }

            # Agregar timeToStart si existe
            if time_to_start is not None:
                # Asegurar que el datetime esté en UTC antes de formatearlo
                if time_to_start.tzinfo is not None:
                    # Convertir a UTC si tiene timezone
                    time_to_start_utc = time_to_start.astimezone(timezone.utc).replace(
                        tzinfo=None
                    )
                else:
                    # Asumir que ya está en UTC si no tiene timezone
                    time_to_start_utc = time_to_start

                competitor_data["timeToStart"] = format_utc_to_local_datetime(
                    time_to_start_utc
                )
                logging.debug(
                    f"track_competitors: Competidor {competitor_id} - order: {i + 1}, timeToStart: {competitor_data['timeToStart']}"
                )

            competitor_doc_ref.set(competitor_data)

            # Crear subcolección de checkpoints para este competidor
            checkpoints_collection_ref = competitor_doc_ref.collection("checkpoints")

            checkpoints_created = []
            for checkpoint_doc in checkpoints_docs:
                checkpoint_id = checkpoint_doc.id
                checkpoint_data = checkpoint_doc.to_dict()

                checkpoint_doc_ref = checkpoints_collection_ref.document(checkpoint_id)

                # Obtener y validar el tipo de checkpoint
                checkpoint_type_str = checkpoint_data.get("type", "")
                checkpoint_type_value = ""

                # Mapear el valor del enum CheckpointType
                try:
                    if checkpoint_type_str:
                        # Validar que sea un valor válido del enum
                        checkpoint_type_enum = CheckpointType(checkpoint_type_str)
                        checkpoint_type_value = checkpoint_type_enum.value
                    else:
                        # Valor por defecto si no está especificado
                        checkpoint_type_value = CheckpointType.START.value
                except (ValueError, KeyError):
                    # Si el valor no es válido, usar "start" como valor por defecto
                    logging.warning(
                        f"track_competitors: Tipo de checkpoint inválido '{checkpoint_type_str}' para checkpoint {checkpoint_id}. Usando 'start' como valor por defecto."
                    )
                    checkpoint_type_value = CheckpointType.START.value

                checkpoint_tracking_data = {
                    "id": checkpoint_id,
                    "name": checkpoint_data.get("name", "Checkpoint"),
                    "checkpointType": checkpoint_type_value,
                    "checkpointDisable": None,
                    "checkpointDisableName": None,
                    "order": checkpoint_data.get("order", 0),
                    "statusCompetitor": "none",  # Estado inicial
                    "passTime": format_utc_to_local_datetime(
                        datetime.utcnow()
                    ),  # Se actualizará cuando pase
                    "note": None,
                    "createdAt": format_utc_to_local_datetime(datetime.utcnow()),
                    "updatedAt": format_utc_to_local_datetime(datetime.utcnow()),
                }

                checkpoint_doc_ref.set(checkpoint_tracking_data)
                checkpoints_created.append(
                    {
                        "checkpointId": checkpoint_id,
                        "checkpointName": checkpoint_data.get("name", "Checkpoint"),
                    }
                )

            competitors_created.append(
                {
                    "competitorId": competitor_id,
                    "competitorName": personal_data.get("fullName", "Competidor"),
                    "checkpointsCount": len(checkpoints_created),
                    "checkpoints": checkpoints_created,
                }
            )

            logging.debug(
                f"track_competitors: Competidor {i+1} creado: {competitor_data['name']} (ID: {competitor_id}) con {len(checkpoints_created)} checkpoints"
            )

        logging.info(
            f"track_competitors: {len(competitors_created)} competidores procesados con estructura optimizada"
        )

        result = {
            "success": True,
            "message": f"Tracking de competidores creado para el evento '{event.name}' día {day_id}",
            "event_id": event_id,
            "day_id": day_id,
            "event_name": event.name,
            "competitors_count": len(competitors_created),
            "routes_count": len(routes_created),
            "tracking_id": tracking_doc_id,
            "structure_type": "optimized_granular",
            "competitors": competitors_created,
            "routes": routes_created,
        }

        logging.info(
            f"track_competitors: Función completada exitosamente. Resultado: {result}"
        )
        return result

    except https_fn.HttpsError as e:
        # Re-lanzar errores de Firebase Functions
        logging.error(
            f"track_competitors: Error de Firebase Functions: {e.code} - {e.message}"
        )
        raise
    except Exception as e:
        # Convertir otros errores a HttpsError
        logging.error(f"track_competitors: Error interno: {str(e)}", exc_info=True)
        raise https_fn.HttpsError(
            code="internal", message=f"Error interno del servidor: {str(e)}"
        )


@https_fn.on_call()
def track_competitors_off(req: https_fn.CallableRequest) -> dict:
    """
    Función que recibe eventId y dayId.
    Busca el documento de tracking en events_tracking/{eventId}/competitor_tracking/{eventId_dayId}
    y cambia el valor de isActive a false.
    """
    try:
        data = req.data
        logging.info(f"track_competitors_off: Iniciando función con datos: {data}")

        if not data or "eventId" not in data or "dayId" not in data:
            logging.error("track_competitors_off: Parámetros requeridos faltantes")
            raise https_fn.HttpsError(
                code="invalid-argument",
                message="Se requieren los parámetros 'eventId' y 'dayId'",
            )

        event_id = data["eventId"]
        day_id = data["dayId"]

        logging.info(
            f"track_competitors_off: Procesando evento {event_id}, día {day_id}"
        )

        db = firestore.client()

        # Actualizar el documento del día en events/{event_id}/day_of_races/{day_id}
        day_of_race_ref = db.collection(f"events/{event_id}/day_of_races").document(
            day_id
        )
        day_of_race_doc = day_of_race_ref.get()

        if day_of_race_doc.exists:
            # Obtener estado actual del día
            day_of_race_data = day_of_race_doc.to_dict()
            current_day_is_active = day_of_race_data.get("isActivate", True)

            logging.info(
                f"track_competitors_off: Actualizando documento del día {day_id} en events/{event_id}/day_of_races"
            )
            logging.info(
                f"track_competitors_off: Estado actual isActivate del día: {current_day_is_active}"
            )

            # Actualizar el documento del día con isActivate = false
            day_of_race_ref.update(
                {
                    "isActivate": False,
                    "updatedAt": format_utc_to_local_datetime(datetime.utcnow()),
                }
            )

            logging.info(
                f"track_competitors_off: Documento del día actualizado exitosamente. isActivate cambiado a False"
            )
        else:
            logging.warning(
                f"track_competitors_off: Documento del día {day_id} no encontrado en events/{event_id}/day_of_races"
            )

        # Construir el ID del documento de tracking
        tracking_doc_id = f"{event_id}_{day_id}"
        collection_path = f"events_tracking/{event_id}/competitor_tracking"

        logging.info(
            f"track_competitors_off: Buscando documento {tracking_doc_id} en {collection_path}"
        )

        # Buscar el documento de tracking
        tracking_ref = db.collection(collection_path).document(tracking_doc_id)
        tracking_doc = tracking_ref.get()

        if not tracking_doc.exists:
            logging.error(
                f"track_competitors_off: Documento de tracking {tracking_doc_id} no encontrado"
            )
            raise https_fn.HttpsError(
                code="not-found",
                message=f"Documento de tracking con ID {tracking_doc_id} no encontrado",
            )

        logging.info(
            f"track_competitors_off: Documento de tracking {tracking_doc_id} encontrado"
        )

        # Obtener datos actuales del documento
        tracking_data = tracking_doc.to_dict()
        current_is_active = tracking_data.get("isActivate", True)

        logging.info(
            f"track_competitors_off: Estado actual isActive del tracking: {current_is_active}"
        )

        # Actualizar el documento con isActive = false
        tracking_ref.update(
            {
                "isActivate": False,
                "updatedAt": format_utc_to_local_datetime(datetime.utcnow()),
            }
        )

        logging.info(
            f"track_competitors_off: Documento de tracking actualizado exitosamente. isActivate cambiado a False"
        )

        result = {
            "success": True,
            "message": f"Tracking de competidores desactivado para el evento {event_id} día {day_id}",
            "event_id": event_id,
            "day_id": day_id,
            "tracking_id": tracking_doc_id,
            "is_active": False,
            "previous_status": current_is_active,
        }

        logging.info(
            f"track_competitors_off: Función completada exitosamente. Resultado: {result}"
        )
        return result

    except https_fn.HttpsError as e:
        logging.error(
            f"track_competitors_off: Error de Firebase Functions: {e.code} - {e.message}"
        )
        raise
    except Exception as e:
        logging.error(f"track_competitors_off: Error interno: {str(e)}", exc_info=True)
        raise https_fn.HttpsError(
            code="internal", message=f"Error interno del servidor: {str(e)}"
        )

