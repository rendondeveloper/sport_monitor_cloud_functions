# Package: Catalogs - Catálogos (vehicles, years, colors, relationship_types) SPRTMNTRPP-82
from catalogs.color import catalog_color
from catalogs.relationship_type import catalog_relationship_type
from catalogs.vehicle import catalog_vehicle
from catalogs.year import catalog_year

__all__ = ["catalog_color", "catalog_relationship_type", "catalog_vehicle", "catalog_year"]
