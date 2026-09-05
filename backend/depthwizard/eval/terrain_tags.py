"""Terrain tag classifier and mapping."""

from typing import Dict

TERRAIN_CLASSES = ["urban", "sparse", "hilly", "forested"]


def get_terrain_tag(scene_id: str, tags_map: Dict[str, str]) -> str:
    """Lookup terrain category for scene."""
    return tags_map.get(scene_id, "urban")
