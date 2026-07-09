"""
D40 Run Manager

This module manages long-running task state for the Zemax-Agent workflow.

D40 goal:
- Create a unique run_id for each run.
- Create a run directory under results/runs/.
- Maintain a status.json file.
- Maintain an events.jsonl file.
- Track progress, current step, success, and failure.

Python compatibility:
- Written for Python 3.8.
"""

from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
import json
import traceback
import uuid


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNS_ROOT = PROJECT_ROOT / "results" / "runs"


# ----------------------------------------------------------------------
# Basic helpers
# ----------------------------------------------------------------------

def now_iso() -> str:
    """
    Return current local time in ISO-like format.

    Example:
        2026-07-07T15:30:12
    """
    return datetime.now().isoformat(timespec="seconds")


def generate_run_id(prefix: str = "D40") -> str:
    """
    Generate a unique run_id.

    Format:
        D40_YYYYMMDD_HHMMSS_xxxxxxxx
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    return "{}_{}_{}".format(prefix, timestamp, short_uuid)


def get_run_dir(run_id: str) -> Path:
    """
    Return the directory for a given run_id.
    """
    return RUNS_ROOT / run_id


def get_status_file(run_id: str) -> Path:
    """
    Return the status.json path for a run.
    """
    return get_run_dir(run_id) / "status.json"


def get_events_file(run_id: str) -> Path:
    """
    Return the events.jsonl path for a run.
    """
    return get_run_dir(run_id) / "events.jsonl"


def save_json(path: Path, data: Dict[str, Any]) -> None:
    """
    Save a dictionary as a JSON file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(path: Path) -> Dict[str, Any]:
    """
    Load a JSON file as a dictionary.
    """
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


# ----------------------------------------------------------------------
# Run lifecycle functions
# ----------------------------------------------------------------------

def create_run(
    task_name: str,
    tool_name: str,
    args: Optional[Dict[str, Any]] = None,
    total_steps: int = 1,
    prefix: str = "D40"
) -> Dict[str, Any]:
    """
    Create a new run directory and initial status.json.

    Returns:
        status dictionary containing run_id and run_dir.
    """
    if args is None:
        args = {}

    run_id = generate_run_id(prefix=prefix)
    run_dir = get_run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    status = {
        "run_id": run_id,
        "task_name": task_name,
        "tool_name": tool_name,
        "state": "created",
        "created_at": now_iso(),
        "started_at": None,
        "ended_at": None,
        "progress": {
            "total_steps": total_steps,
            "completed_steps": 0,
            "percent": 0.0,
            "current_step": "not_started"
        },
        "args": args,
        "last_message": "Run created.",
        "error": None,
        "run_dir": str(run_dir.relative_to(PROJECT_ROOT))
    }

    save_json(get_status_file(run_id), status)
    append_event(run_id, "info", "Run created.", {"task_name": task_name})

    return status


def read_status(run_id: str) -> Dict[str, Any]:
    """
    Read status.json for a run.
    """
    status_file = get_status_file(run_id)

    if not status_file.exists():
        raise FileNotFoundError("status.json not found for run_id: {}".format(run_id))

    return load_json(status_file)


def update_status(
    run_id: str,
    state: Optional[str] = None,
    current_step: Optional[str] = None,
    completed_steps: Optional[int] = None,
    total_steps: Optional[int] = None,
    message: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Update status.json.

    Common states:
        created, running, success, failed
    """
    status = read_status(run_id)

    if state is not None:
        old_state = status.get("state")
        status["state"] = state

        if old_state != "running" and state == "running" and status.get("started_at") is None:
            status["started_at"] = now_iso()

        if state in ["success", "failed", "cancelled"]:
            status["ended_at"] = now_iso()

    progress = status.get("progress", {})

    if total_steps is not None:
        progress["total_steps"] = total_steps

    if completed_steps is not None:
        progress["completed_steps"] = completed_steps

    if current_step is not None:
        progress["current_step"] = current_step

    total = progress.get("total_steps", 0)
    completed = progress.get("completed_steps", 0)

    if total and total > 0:
        progress["percent"] = round(completed / total * 100.0, 2)
    else:
        progress["percent"] = 0.0

    status["progress"] = progress

    if message is not None:
        status["last_message"] = message

    if extra:
        status.update(extra)

    save_json(get_status_file(run_id), status)

    return status


def append_event(
    run_id: str,
    level: str,
    message: str,
    data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Append one event to events.jsonl.

    JSONL means one JSON object per line.
    It is convenient for logs because new events can be appended.
    """
    if data is None:
        data = {}

    event = {
        "time": now_iso(),
        "run_id": run_id,
        "level": level,
        "message": message,
        "data": data
    }

    events_file = get_events_file(run_id)
    events_file.parent.mkdir(parents=True, exist_ok=True)

    with events_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def mark_success(run_id: str, message: str = "Run completed successfully.") -> Dict[str, Any]:
    """
    Mark a run as success.
    """
    status = read_status(run_id)
    total_steps = status.get("progress", {}).get("total_steps", 1)

    updated = update_status(
        run_id,
        state="success",
        completed_steps=total_steps,
        current_step="completed",
        message=message
    )

    append_event(run_id, "info", message)
    return updated


def mark_failed(
    run_id: str,
    message: str = "Run failed.",
    error: Optional[BaseException] = None
) -> Dict[str, Any]:
    """
    Mark a run as failed and save error information.
    """
    error_info = None

    if error is not None:
        error_info = {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc()
        }

    updated = update_status(
        run_id,
        state="failed",
        message=message,
        extra={"error": error_info}
    )

    append_event(run_id, "error", message, {"error": error_info})
    return updated


def list_recent_runs(limit: int = 10) -> List[Dict[str, Any]]:
    """
    List recent run statuses.
    """
    if not RUNS_ROOT.exists():
        return []

    statuses = []

    for status_file in RUNS_ROOT.glob("*/status.json"):
        try:
            statuses.append(load_json(status_file))
        except Exception:
            continue

    statuses.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return statuses[:limit]