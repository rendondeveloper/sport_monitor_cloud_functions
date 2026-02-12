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
from competitors import competitor_route

# Importar funciones de checkpoints
from checkpoints import (
    all_competitor_tracking,
    change_competitor_status,
    checkpoint,
    competitor_tracking,
    day_of_race_active,
    days_of_race,
    update_competitor_status,
)

# Importar funciones de events
from events import event_categories, event_detail, events
import os
from firebase_admin import initialize_app
from firebase_functions.options import set_global_options

# Importar funciones de tracking
from tracking.track_competitor_position import track_competitor_position
from tracking.tracking_checkpoint import track_event_checkpoint
from tracking.tracking_competitors import track_competitors, track_competitors_off

# Importar funciones de users
from users import user_profile, create_user

# Importar funciones de vehicles
from vehicles import delete_vehicle, get_vehicles, update_vehicle

# Importar funciones de catalogs
from catalogs import catalog_vehicle, catalog_year, catalog_color

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
# - user_profile: users/user_profile.py
# - create_user: users/user_create.py
# - day_of_race_active: checkpoints/day_of_race_active.py
# - checkpoint: checkpoints/checkpoint.py
# - competitor_tracking: checkpoints/competitor_tracking.py
# - days_of_race: checkpoints/days_of_race.py
# - all_competitor_tracking: checkpoints/all_competitor_tracking.py
# - change_competitor_status: checkpoints/change_competitor_status.py
# - update_competitor_status: checkpoints/update_competitor_status.py
# - competitor_route: competitors/competitor_route.py
# - track_competitor_position: tracking/track_competitor_position.py
# - get_vehicles: vehicles/get_vehicles.py
# - update_vehicle: vehicles/update_vehicle.py
# - delete_vehicle: vehicles/delete_vehicle.py
# - catalog_vehicle: catalogs/catalog_vehicle.py
# - catalog_year: catalogs/catalog_year.py
# - catalog_color: catalogs/catalog_color.py