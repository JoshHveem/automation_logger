from __future__ import annotations

import json
import os
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from syncforge import WarehouseClient

from ._config import load_automation_config
from ._host import get_host_context
from ._json import jsonable
from ._paths import resolve_entry_script_path, resolve_path


@dataclass
class AutomationRunLogger:
    """
    Context-manager logger for any automation.

    Typical usage:
        from automation_logger import AutomationRunLogger

        with AutomationRunLogger.from_config(script_path=__file__) as log:
            log.add_output("rows_inserted", 10)
            ...
    """

    automation_id: int
    schema_name: str = "automations"
    table_name: str = "run_log"

    # If provided, can be stored in context and used for path_mode="script"
    script_path: Optional[str] = None

    # Arbitrary debug payload stored as jsonb (results/metrics)
    output: Dict[str, Any] = field(default_factory=dict)

    # Run context stored as jsonb (paths + host info)
    context: Dict[str, Any] = field(default_factory=dict)

    flags: Dict[str, Any] = field(default_factory=dict)

    # internal
    _t0: float = field(default_factory=time.time, init=False)
    _success: bool = field(default=True, init=False)
    _run_time: Optional[datetime] = field(default=None, init=False)

    @classmethod
    def from_config(
        cls,
        config_path: str = "automation.config",
        automation_id: Optional[int] = None,
        schema_name: Optional[str] = None,
        table_name: Optional[str] = None,
        script_path: Optional[str] = None,
        path_mode: Optional[str] = None,
    ) -> "AutomationRunLogger":
        """Create logger from config file, with optional overrides."""
        cfg = load_automation_config(config_path)

        cfg_id = cfg.get("automation_id")
        env_id = os.getenv("AUTOMATION_ID")
        env_id = int(env_id) if env_id and env_id.isdigit() else None

        final_id = (
            automation_id
            if automation_id is not None
            else cfg_id
            if cfg_id is not None
            else env_id
        )

        if final_id is None:
            raise ValueError("automation_id is required (arg, config, or AUTOMATION_ID env var).")

        final_schema = schema_name or cfg.get("schema_name") or "automations"
        final_table = table_name or cfg.get("table_name") or "run_log"

        entry_script_path = resolve_entry_script_path(script_path)

        final_path_mode = (path_mode or cfg.get("path_mode") or "script").strip().lower()

        # If they asked for script mode but we couldn't detect the script, fall back to cwd
        if final_path_mode == "script" and not entry_script_path:
            final_path_mode = "cwd"

        resolved_path = resolve_path(final_path_mode, entry_script_path)

        logger = cls(
            automation_id=final_id,
            schema_name=final_schema,
            table_name=final_table,
            script_path=entry_script_path,
        )

        # --- context payload (goes to jsonb context column) ---
        logger.context["config_path"] = config_path
        logger.context["path_mode"] = final_path_mode
        logger.context["cwd"] = os.getcwd()
        logger.context["resolved_path"] = resolved_path  # what you *used* given path_mode

        if entry_script_path:
            logger.context["entry_script_path"] = entry_script_path
            logger.context["entry_script_dir"] = os.path.dirname(entry_script_path)

        logger.context.update(get_host_context())

        return logger

    def set_output(self, payload: Dict[str, Any]) -> None:
        self.output = {k: jsonable(v) for k, v in payload.items()}

    def add_output(self, key: str, value: Any) -> None:
        self.output[key] = jsonable(value)

    def mark_failure(self) -> None:
        self._success = False

    def add_flag(self, name: str, **meta: Any) -> None:
        """
        Add a non-fatal flag for the run.
        - Idempotent: calling repeatedly won't duplicate.
        - If meta provided, merges/overwrites into flag's dict.
        """
        if not name or not isinstance(name, str):
            raise ValueError("flag name must be a non-empty string")

        name = name.strip()
        if not name:
            raise ValueError("flag name must be a non-empty string")

        if not meta:
            self.flags.setdefault(name, True)
            return

        existing = self.flags.get(name)
        if existing is True or existing is None:
            existing = {}
        elif not isinstance(existing, dict):
            existing = {"value": jsonable(existing)}

        for k, v in meta.items():
            existing[k] = jsonable(v)

        self.flags[name] = existing

    def _insert_row(self, success: bool, run_time: datetime, duration_ms: int) -> None:
        output_json_str = json.dumps(self.output or {}, ensure_ascii=False)
        context_json_str = json.dumps(self.context or {}, ensure_ascii=False)
        flags_json_str = json.dumps(self.flags or {}, ensure_ascii=False)

        sql = f"""
            INSERT INTO {self.schema_name}.{self.table_name}
                (automation_id, run_time, context, output, flags, success, duration_ms)
            VALUES
                (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s);
        """

        params = (
            self.automation_id,
            run_time,
            context_json_str,
            output_json_str,
            flags_json_str,
            success,
            duration_ms,
        )

        with WarehouseClient() as wh:
            wh.execute_query(sql, params, fetch=False, commit=True)

    def __enter__(self) -> "AutomationRunLogger":
        self._t0 = time.time()
        self._run_time = datetime.now(timezone.utc)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        duration_ms = int((time.time() - self._t0) * 1000)
        run_time = self._run_time or datetime.now(timezone.utc)

        if exc is not None:
            self._success = False
            self.output.setdefault("error", {})
            self.output["error"] = {
                "type": getattr(exc_type, "__name__", str(exc_type)),
                "message": str(exc),
                "traceback": "".join(traceback.format_exception(exc_type, exc, tb)),
            }

        try:
            self._insert_row(success=self._success, run_time=run_time, duration_ms=duration_ms)
        except Exception as log_exc:
            print(f"[AutomationRunLogger] Failed to log run: {log_exc}")

        # False => re-raise original exception (your current behavior)
        return False
