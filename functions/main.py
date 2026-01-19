# Importar funciones de checkpoints
from checkpoints import checkpoint, competitor_tracking, day_of_race_active

# Importar funciones de events
from events import event_detail, events
from firebase_admin import initialize_app
from firebase_functions.options import set_global_options

# Importar funciones de tracking
from tracking.tracking_checkpoint import track_event_checkpoint
from tracking.tracking_competitors import track_competitors, track_competitors_off

# Importar funciones de users
from users import user_profile

# For cost control, you can set the maximum number of containers that can be
# running at the same time. This helps mitigate the impact of unexpected
# traffic spikes by instead downgrading performance. This limit is a per-function
# limit. You can override the limit for each function using the max_instances
# parameter in the decorator, e.g. @https_fn.on_request(max_instances=5).
set_global_options(max_instances=10)

# Initialize Firebase Admin
initialize_app()

# Las funciones están definidas en sus respectivos módulos:
# - track_event_checkpoint: tracking/tracking_checkpoint.py
# - track_competitors: tracking/tracking_competitors.py
# - track_competitors_off: tracking/tracking_competitors.py
# - events: events/events_customer.py
# - event_detail: events/events_detail_customer.py
# - user_profile: users/user_profile.py
# - day_of_race_active: checkpoints/day_of_race_active.py
# - get_checkpoint: checkpoints/get_checkpoint.py
# - competitor_tracking: checkpoints/competitor_tracking.py
