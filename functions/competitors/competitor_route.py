"""
Competitor Route - SPRTMNTRPP-74

Lista por usuario autenticado los eventos en los que tiene membership, con rutas
visibles para pilotos que coincidan con su categoría y los checkpoints de cada ruta.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from firebase_admin import firestore
from firebase_functions import https_fn
from google.cloud.firestore_v1.base_query import FieldFilter
from models.firestore_collections import FirestoreCollections
from utils.helper_http import verify_bearer_token
from utils.helper_http_verb import validate_request
from utils.helpers import convert_firestore_value


def _get_registration_category_and_pilot_number(
    participant_data: Dict[str, Any],
) -> Tuple[str, Any]:
    """
    Obtiene registrationCategory (id del doc en event_categories) y pilotNumber.

    La fuente principal es el mapa anidado del participante en Firestore::

        competitionCategory: {
            pilotNumber: null | "" | string,
            registrationCategory: "<id documento event_categories>"
        }

    Solo si falta valor útil en `competitionCategory` se usa la raíz del documento
    (compatibilidad con datos antiguos).
    """
    raw = participant_data.get("competitionCategory")
    comp_cat: Dict[str, Any] = raw if isinstance(raw, dict) else {}

    # registrationCategory: primero el anidado; si vacío/ausente, raíz
    nested_reg = comp_cat.get("registrationCategory")
    root_reg = participant_data.get("registrationCategory", "")
    reg_id = ""
    if nested_reg is not None and str(nested_reg).strip() != "":
        reg_id = str(nested_reg).strip()
    elif root_reg is not None:
        reg_id = str(root_reg).strip()

    # pilotNumber: si la clave existe en competitionCategory, el valor es el del mapa
    # (incluye "" y null); si no existe la clave, se usa la raíz del participante
    if "pilotNumber" in comp_cat:
        pilot = comp_cat.get("pilotNumber")
    else:
        pilot = participant_data.get("pilotNumber")

    return reg_id, pilot


def _normalize_pilot_for_display(pilot: Any) -> Any:
    if pilot is None:
        return None
    if isinstance(pilot, str) and pilot.strip() == "":
        return None
    return pilot


def _get_participant_doc(
    db: firestore.Client, event_id: str, user_id: str
):
    participant_ref = (
        db.collection(FirestoreCollections.EVENTS)
        .document(event_id)
        .collection(FirestoreCollections.EVENT_PARTICIPANTS)
        .document(user_id)
    )
    return participant_ref.get()


def _resolve_participant_event_category(
    db: firestore.Client, event_id: str, category_doc_id: str
) -> Tuple[Optional[str], str]:
    """
    Valida que exista `events/{eventId}/event_categories/{category_doc_id}`.

    Returns:
        (category_id o None, nombre legible desde campo `name` del doc o "")
    """
    cid = (category_doc_id or "").strip()
    if not cid:
        return None, ""
    ref = (
        db.collection(FirestoreCollections.EVENTS)
        .document(event_id)
        .collection(FirestoreCollections.EVENT_CATEGORIES)
        .document(cid)
    )
    snap = ref.get()
    if not snap.exists:
        return None, ""
    data = snap.to_dict() or {}
    display_name = (data.get("name") or "").strip()
    return cid, display_name


def _competitor_payload(
    participant_data: Dict[str, Any],
    category_display_name: str = "",
) -> Dict[str, Any]:
    """category: dorsal si hay pilotNumber; si no, nombre de event_categories (no el id)."""
    registration_id, pilot_raw = _get_registration_category_and_pilot_number(
        participant_data
    )
    pilot = _normalize_pilot_for_display(pilot_raw)
    name_str = (category_display_name or "").strip()

    if pilot is not None:
        category_str = str(pilot)
    else:
        category_str = name_str

    nombre = name_str or (registration_id or "")
    return {
        "category": category_str,
        "nombre": nombre,
    }


def _route_payload(route_data: Dict[str, Any]) -> Dict[str, Any]:
    total_distance = route_data.get("totalDistance")
    if total_distance is None:
        total_distance = 0
    typedistance = route_data.get("typedistance") or route_data.get(
        "typeDistance", ""
    )
    return {
        "name": route_data.get("name", ""),
        "route": route_data.get("routeUrl", ""),
        "version": 1,
        "totalDistance": total_distance,
        "typedistance": typedistance,
    }


def _route_updated_at_iso(route_data: Dict[str, Any]) -> str:
    ts = route_data.get("updatedAt") or route_data.get("createdAt")
    if ts is None:
        return ""
    converted = convert_firestore_value(ts)
    return converted if isinstance(converted, str) else ""


def _load_checkpoints_for_route(
    db: firestore.Client, event_id: str, route_doc_id: str
) -> List[Dict[str, Any]]:
    checkpoints_ref = (
        db.collection(FirestoreCollections.EVENTS)
        .document(event_id)
        .collection(FirestoreCollections.EVENT_ROUTES)
        .document(route_doc_id)
        .collection(FirestoreCollections.EVENT_CHECKPOINTS)
    )
    docs = checkpoints_ref.get()

    def _order_key(doc: Any) -> Any:
        data = doc.to_dict() or {}
        o = data.get("order", 0)
        return o if o is not None else 0

    sorted_docs = sorted(docs, key=_order_key)
    out: List[Dict[str, Any]] = []
    for doc in sorted_docs:
        raw = doc.to_dict() or {}
        payload = dict(raw)
        item = convert_firestore_value(payload)
        if not isinstance(item, dict):
            continue
        if item.get("id") in (None, ""):
            item["id"] = doc.id
        out.append(item)
    return out


def _build_route_entry(
    db: firestore.Client,
    event_id: str,
    participant_data: Dict[str, Any],
    route_snap: Any,
    category_display_name: str = "",
) -> Dict[str, Any]:
    route_data = route_snap.to_dict() or {}
    return {
        "competitor": _competitor_payload(
            participant_data, category_display_name=category_display_name
        ),
        "route": _route_payload(route_data),
        "updatedAt": _route_updated_at_iso(route_data),
        "checkpoints": _load_checkpoints_for_route(db, event_id, route_snap.id),
    }


def _cors_headers() -> Dict[str, str]:
    return {
        "Content-Type": "application/json; charset=utf-8",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }


def _is_debug_request(req: https_fn.Request) -> bool:
    raw = (req.args.get("debug") or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _not_found(req: https_fn.Request, error: str) -> https_fn.Response:
    if _is_debug_request(req):
        return https_fn.Response(
            json.dumps(
                {"error": error, "function": "competitor_route", "status": 404},
                ensure_ascii=False,
            ),
            status=404,
            headers={"Content-Type": "application/json; charset=utf-8", "Access-Control-Allow-Origin": "*"},
        )
    return https_fn.Response("", status=404, headers={"Access-Control-Allow-Origin": "*"})


@https_fn.on_request(region="us-east4")
def competitor_route(req: https_fn.Request) -> https_fn.Response:
    """
    Lista eventos del usuario (membership) con rutas para pilotos visibles que
    coincidan con categoryIds de la categoría del participante.

    Headers:
    - Authorization: Bearer {Firebase ID token} (requerido)

    Query:
    - userId: UID del usuario (requerido)

    Returns:
    - 200: JSON array [{ eventId, eventName, routes | null }, ...]
    - 400: userId faltante
    - 401: Token inválido o faltante
    - 404: Sin documentos en membership, o ningún evento aplicable tras filtros
    - 500: Error interno
    """
    validation_response = validate_request(
        req, ["GET"], "competitor_route", return_json_error=False
    )
    if validation_response is not None:
        return validation_response

    try:
        user_id_param = (req.args.get("userId") or "").strip()
        if not user_id_param:
            logging.warning("competitor_route: userId faltante o vacío")
            return https_fn.Response(
                "",
                status=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # if not verify_bearer_token(req, "competitor_route"):
        #     logging.warning("competitor_route: Token inválido o faltante")
        #     return https_fn.Response(
        #         "",
        #         status=401,
        #         headers={"Access-Control-Allow-Origin": "*"},
        #     )

        db = firestore.client()
        membership_ref = (
            db.collection(FirestoreCollections.USERS)
            .document(user_id_param)
            .collection(FirestoreCollections.USER_MEMBERSHIP)
        )
        membership_docs = list(membership_ref.stream())
        if not membership_docs:
            logging.warning(
                "competitor_route: Sin membresías para userId=%s", user_id_param
            )
            return _not_found(req, "membership_not_found")

        result: List[Dict[str, Any]] = []

        for mdoc in membership_docs:
            event_id = mdoc.id
            event_doc = (
                db.collection(FirestoreCollections.EVENTS).document(event_id).get()
            )
            if not event_doc.exists:
                continue

            event_name = (event_doc.to_dict() or {}).get("name", "")

            participant_doc = _get_participant_doc(db, event_id, user_id_param)
            if not participant_doc.exists:
                continue

            participant_data = participant_doc.to_dict() or {}

            registration_category_id, _ = _get_registration_category_and_pilot_number(
                participant_data
            )
            category_id, category_display_name = _resolve_participant_event_category(
                db, event_id, registration_category_id
            )

            routes_col = (
                db.collection(FirestoreCollections.EVENTS)
                .document(event_id)
                .collection(FirestoreCollections.EVENT_ROUTES)
            )
            visible_query = routes_col.where(
                filter=FieldFilter("visibleForPilots", "==", True)
            )
            route_snapshots = visible_query.get()

            matching_routes: List[Any] = []
            if category_id:
                for rd in route_snapshots:
                    rdata = rd.to_dict() or {}
                    if category_id in (rdata.get("categoryIds") or []):
                        matching_routes.append(rd)

            if not matching_routes:
                result.append(
                    {
                        "eventId": event_id,
                        "eventName": event_name,
                        "routes": None,
                    }
                )
            else:
                entries = [
                    _build_route_entry(
                        db,
                        event_id,
                        participant_data,
                        rd,
                        category_display_name=category_display_name,
                    )
                    for rd in matching_routes
                ]
                result.append(
                    {
                        "eventId": event_id,
                        "eventName": event_name,
                        "routes": entries,
                    }
                )

        if not result:
            logging.warning(
                "competitor_route: Ningún evento aplicable tras procesar membership userId=%s",
                user_id_param,
            )
            return _not_found(req, "no_applicable_events")

        logging.info(
            "competitor_route: OK userId=%s eventos=%s", user_id_param, len(result)
        )
        return https_fn.Response(
            json.dumps(result, ensure_ascii=False),
            status=200,
            headers=_cors_headers(),
        )

    except ValueError as e:
        logging.error("competitor_route: Error de validación: %s", e)
        return https_fn.Response(
            "",
            status=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except (AttributeError, KeyError, RuntimeError, TypeError) as e:
        logging.error("competitor_route: Error interno: %s", e, exc_info=True)
        return https_fn.Response(
            "",
            status=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )
