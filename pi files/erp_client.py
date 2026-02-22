# ─────────────────────────────────────────────
# erp_client.py  —  Sends attendance punches to your ERP
#
# Makes a single POST request per attendance event.
# Handles:
#   • Punch-in vs punch-out logic (server-side preferred, but
#     we also track locally as fallback)
#   • Retry on network failure
#   • Cooldown tracking so the same person can't double-punch
#
# Your ERP just needs ONE endpoint:
#   POST /api/attendance/punch
#   Headers: X-Api-Key: <your key>
#   Body:    { employee_id, device_id, timestamp, event_type }
#   Returns: { success, action, employee_name }
#
# "action" in the response should be "punch_in" or "punch_out"
# so the Pi can show the right message / LED colour.
# ─────────────────────────────────────────────

import time
import requests
from datetime import datetime, timezone
from typing import Optional
from loguru import logger
from dataclasses import dataclass

import config


@dataclass
class PunchResult:
    success: bool
    action: str          # "punch_in" | "punch_out" | "error"
    message: str         # human-readable, shown on display / LED
    employee_name: str


class ERPClient:
    """
    Handles all communication with the ERP portal API.

    Also manages the local cooldown state — after a successful
    punch, the same employee is ignored for COOLDOWN_SECONDS.
    This prevents someone standing in front of the camera from
    flooding the system with duplicate punches.
    """

    def __init__(self):
        # cooldown_map: employee_id → unix timestamp of last successful punch
        self._cooldown_map: dict[str, float] = {}
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "X-Api-Key": config.ERP_API_KEY,
        })

    def is_in_cooldown(self, employee_id: str) -> bool:
        last_punch = self._cooldown_map.get(employee_id)
        if last_punch is None:
            return False
        elapsed = time.time() - last_punch
        return elapsed < config.COOLDOWN_SECONDS

    def punch(self, employee_id: str, employee_name: str) -> PunchResult:
        """
        Send a punch event to the ERP.

        The ERP server determines whether this is punch-in or punch-out
        based on the employee's current state in its own database.
        We just send the event and let the server decide.

        Returns PunchResult with the outcome.
        """
        # ── Cooldown check ────────────────────────────────────────────────────
        if self.is_in_cooldown(employee_id):
            elapsed = int(time.time() - self._cooldown_map[employee_id])
            remaining = config.COOLDOWN_SECONDS - elapsed
            logger.debug(f"Cooldown active for {employee_name} — {remaining}s remaining")
            return PunchResult(
                success=False,
                action="cooldown",
                message=f"Please wait {remaining}s",
                employee_name=employee_name,
            )

        # ── Build payload ─────────────────────────────────────────────────────
        payload = {
            "employee_id": employee_id,
            "device_id": config.DEVICE_ID,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # ── Send with simple retry ─────────────────────────────────────────────
        for attempt in range(1, 4):   # 3 attempts
            try:
                response = self._session.post(
                    config.ERP_PUNCH_ENDPOINT,
                    json=payload,
                    timeout=config.ERP_TIMEOUT_SEC,
                )

                if response.status_code == 200:
                    data = response.json()
                    action = data.get("action", "punch_in")
                    self._cooldown_map[employee_id] = time.time()

                    logger.info(
                        f"ERP punch successful: {employee_name} → {action} "
                        f"(device: {config.DEVICE_ID})"
                    )
                    return PunchResult(
                        success=True,
                        action=action,
                        message=f"{action.replace('_', ' ').title()} — {employee_name}",
                        employee_name=employee_name,
                    )

                elif response.status_code == 401:
                    logger.error("ERP API key rejected — check ERP_API_KEY in .env")
                    return PunchResult(success=False, action="error",
                                       message="Auth error", employee_name=employee_name)

                elif response.status_code == 404:
                    logger.error(f"Employee {employee_id} not found in ERP")
                    return PunchResult(success=False, action="error",
                                       message="Employee not found in ERP",
                                       employee_name=employee_name)

                else:
                    logger.warning(f"ERP returned {response.status_code} on attempt {attempt}")

            except requests.Timeout:
                logger.warning(f"ERP request timeout (attempt {attempt}/{3})")
            except requests.ConnectionError:
                logger.warning(f"ERP connection error (attempt {attempt}/{3}) — is the server up?")
            except Exception as exc:
                logger.error(f"ERP punch error: {exc}")
                break

            if attempt < 3:
                time.sleep(0.5 * attempt)   # brief backoff between retries

        # All attempts failed — log locally as fallback
        logger.error(
            f"OFFLINE PUNCH FAILED: {employee_name} ({employee_id}) at "
            f"{datetime.now().isoformat()} — manual entry may be needed"
        )
        return PunchResult(
            success=False,
            action="error",
            message="Network error — punch not recorded",
            employee_name=employee_name,
        )
