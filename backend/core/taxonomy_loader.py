import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_CACHED_TAXONOMY: Optional[Dict[str, Any]] = None
_TAXONOMY_PATH = Path(__file__).parent / "topic_taxonomy.json"


def get_topic_taxonomy(force_reload: bool = False) -> Optional[Dict[str, Any]]:
    """Load and cache the topic taxonomy JSON.

    Returns None if the file is missing or invalid. Callers should handle fallback behavior.
    """
    global _CACHED_TAXONOMY

    if _CACHED_TAXONOMY is not None and not force_reload:
        return _CACHED_TAXONOMY

    try:
        if not _TAXONOMY_PATH.exists():
            logger.info("Topic taxonomy file not found; using built-in fallbacks")
            _CACHED_TAXONOMY = None
            return None

        with _TAXONOMY_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict) or "categories" not in data:
                logger.warning("Invalid taxonomy format; expected top-level 'categories'")
                _CACHED_TAXONOMY = None
                return None
            _CACHED_TAXONOMY = data
            logger.info("Topic taxonomy loaded")
            return _CACHED_TAXONOMY
    except Exception as e:
        logger.warning(f"Failed to load topic taxonomy: {e}")
        _CACHED_TAXONOMY = None
        return None
