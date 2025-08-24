"""
Admin refresh endpoint for the main backend.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class RefreshRequest(BaseModel):
    force_reindex: bool = True


@router.post("/admin/refresh")
async def trigger_refresh(request: RefreshRequest) -> Dict:
    """
    Trigger a knowledge base refresh.

    This endpoint is called by the admin interface to trigger re-indexing
    of the knowledge base. It sets a flag that will be checked on next startup.
    """
    try:
        # Create refresh flag file
        backend_dir = Path(__file__).parent.parent
        flag_file = backend_dir / ".refresh_required"

        flag_content = f"""refresh_requested_at={datetime.now().isoformat()}
force_reindex={request.force_reindex}
requested_by=admin_interface
"""

        flag_file.write_text(flag_content)

        logger.info(f"Refresh flag set: force_reindex={request.force_reindex}")

        return {
            "message": "Refresh flag set successfully",
            "force_reindex": request.force_reindex,
            "timestamp": datetime.now().isoformat(),
            "note": "Changes will take effect on next server restart",
        }

    except Exception as e:
        logger.error(f"Failed to set refresh flag: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to set refresh flag: {str(e)}")


@router.get("/admin/refresh/status")
async def get_refresh_status() -> Dict:
    """Get the current refresh status."""
    try:
        backend_dir = Path(__file__).parent.parent
        flag_file = backend_dir / ".refresh_required"

        if flag_file.exists():
            flag_content = flag_file.read_text()
            return {
                "refresh_pending": True,
                "flag_content": flag_content,
                "note": "Refresh will occur on next server restart",
            }
        else:
            return {"refresh_pending": False, "note": "No refresh currently pending"}

    except Exception as e:
        logger.error(f"Failed to check refresh status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to check refresh status: {str(e)}")
