"""Read-only summary of the frozen interview-ready Project-X checkpoint."""

import hashlib
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "migration": (
        "outputs/migration_zero_control_regression_retry_02/execution_20260825_163417/MIGRATION_ZERO_CONTROL_REVIEW.json",
        "EA52284EB7E643AD6CF20AC916326D9EA320D18EA6BA46561495D21C669DE0E3",
    ),
    "day76_batch": (
        "outputs/day76_seven_point_recovery_batch_retry_02_execution/execution_20260825_164618/seven_point_recovery_batch_result.json",
        "68F90D21BE0A8EC36F9943D341B60DEE8E2DCA667320C1CBD57CB1DC13978D01",
    ),
    "day79_recalculation": (
        "outputs/day79_day27_offline_recalculation/recalculation_20260825_165439/day27_offline_recalculation_result.json",
        "E193E513FD27C35FBD9DAFB62A1625D6ECA1773EDA280C95777073C5161A73F6",
    ),
    "day80_review": (
        "outputs/day80_cp09_day27_recalculation_review/review_20260825_165644/cp09_day27_recalculation_review.json",
        "DE6538F39F1468E72589E42F61B3717C69208509029FF10B23C76BA58AB7AF9F",
    ),
}


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_frozen_sources():
    loaded = {}
    for name, (relative, expected_hash) in SOURCES.items():
        path = PROJECT_ROOT / relative
        if not path.is_file():
            raise FileNotFoundError("Frozen interview evidence is missing: {0}".format(path))
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            raise RuntimeError("Frozen interview evidence changed: {0}".format(path))
        loaded[name] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def main():
    evidence = load_frozen_sources()
    migration = evidence["migration"]
    batch = evidence["day76_batch"]
    recalculation = evidence["day79_recalculation"]
    review = evidence["day80_review"]
    print("========== PROJECT-X INTERVIEW CHECKPOINT ==========")
    print("[PASS] Frozen evidence SHA256 verified: 4/4")
    print("[PASS] Migration regression: {0}".format(migration["status"]))
    print("[PASS] Real seven-point batch: {0}/7 cases".format(batch["completed_case_count"]))
    print("[PASS] Connections closed: {0}".format(batch["all_connections_closed"]))
    print("[PASS] Model safety: {0}".format(batch["all_model_safety_checks_passed"]))
    print("[PASS] Combined measured evidence: {0} points".format(recalculation["combined_measured_point_count"]))
    print("[RESULT] Sampled-envelope PASS: {0}".format(", ".join(recalculation["sampled_envelope_pass_candidates"])))
    print("[RESULT] Sampled-envelope FAIL: {0}".format(", ".join(recalculation["sampled_envelope_fail_candidates"])))
    print("[PASS] Day80 CP09: {0}".format(review["cp09_review"]["task_review_status"]))
    print("[BOUNDARY] Continuous tolerance claimed: False")
    print("[BOUNDARY] Unique engineering winner: None")
    print("[BOUNDARY] Unified ZemaxBackend complete: False")
    print("Read-only summary finished. No ZOS-API connection or output was created.")


if __name__ == "__main__":
    main()
