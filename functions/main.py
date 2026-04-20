# Configurar logging para que se vea en consola (emulador y local).
# Sin esto, logging.warning/info/error puede no aparecer en el terminal del emulador.
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,
    force=True,
)

# Importar funciones de competitors
from competitors import (
    competitor_api_route,
    competitor_route,
    create_competitor,
    create_competitor_user,
    delete_competitor,
    delete_competitor_user,
    get_competitor_by_email,
    get_competitor_by_id,
    get_event_competitor_by_email,
    get_event_competitor_by_id,
    get_competitors_by_event,
    list_competitors_by_event,
)

# Importar funciones de staff
from staff import create_staff_user, staff_route

# Importar funciones de checkpoints
from checkpoints import (
    all_competitor_tracking,
    change_competitor_status,
    checkpoint,
    checkpoint_route,
    competitor_tracking,
    day_of_race_active,
    days_of_race,
    update_competitor_status,
)

# Importar funciones de events
from events import event_categories, event_detail, event_route, events
import os
from firebase_admin import initialize_app
from firebase_functions.options import set_global_options

# Importar funciones de tracking
from tracking import tracking_route
from tracking.tracking_checkpoint import track_event_checkpoint
from tracking.tracking_competitors import track_competitors, track_competitors_off

# Importar funciones de users (una sola función: user_route; despacha por path a read/create/update)
from users import user_route

# Importar funciones de vehicles (una sola funcion: vehicle_route; despacha por path+metodo)
from vehicles import vehicle_route

# Importar funciones de catalogs (una sola función: catalog_route; despacha por path)
from catalogs import catalog_route

# For cost control, you can set the maximum number of containers that can be
# running at the same time. This helps mitigate the impact of unexpected
# traffic spikes by instead downgrading performance. This limit is a per-function
# limit. You can override the limit for each function using the max_instances
# parameter in the decorator, e.g. @https_fn.on_request(max_instances=5).
set_global_options(max_instances=10)

# Initialize Firebase Admin
# Realtime Database (track_competitor_position) requiere databaseURL.
# Opcional: setear FIREBASE_DATABASE_URL, ej. https://PROJECT_ID-default-rtdb.firebaseio.com
_options = {}
if os.environ.get("FIREBASE_DATABASE_URL"):
    _options["databaseURL"] = os.environ["FIREBASE_DATABASE_URL"]
initialize_app(options=_options if _options else None)

# Las funciones están definidas en sus respectivos módulos:
# - track_event_checkpoint: tracking/tracking_checkpoint.py
# - track_competitors: tracking/tracking_competitors.py
# - track_competitors_off: tracking/tracking_competitors.py
# - events: events/events_customer.py
# - event_detail: events/events_detail_customer.py
# - event_categories: events/event_categories.py
# - event_route: events/event_route.py (router: /api/events, /api/events/detail, /api/event/event-categories/**)
# - user_route: users/user_route.py (router: /api/users/read, /api/users/profile, /api/users/create, /api/users/update)
# - day_of_race_active: checkpoints/day_of_race_active.py
# - checkpoint: checkpoints/checkpoint.py
# - competitor_tracking: checkpoints/competitor_tracking.py
# - days_of_race: checkpoints/days_of_race.py
# - all_competitor_tracking: checkpoints/all_competitor_tracking.py
# - change_competitor_status: checkpoints/change_competitor_status.py
# - update_competitor_status: checkpoints/update_competitor_status.py
# - competitor_route: competitors/competitor_route.py
# - track_competitor_position: tracking/track_competitor_position.py
# - vehicle_route: vehicles/vehicle_route.py (router: /api/vehicles, /api/vehicles/search, /api/vehicles/{id})
# - catalog_route: catalogs/catalog_route.py (router: /api/catalogs/vehicle, year, color, relationship-type)
# - create_competitor: competitors/create_competitor.py
# - create_competitor_user: competitors/create_competitor_user.py
# - delete_competitor_user: competitors/delete_competitor_user.py
# - get_event_competitor_by_id: competitors/get_event_competitor_by_id.py
# - get_competitor_by_id: competitors/get_competitor_by_id.py
# - get_competitors_by_event: competitors/get_competitors_by_event.py
# - create_staff_user: staff/create_staff_user.py
# - staff_route: staff/staff_route.py (router: /api/create_staff_user)