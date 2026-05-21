import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = PROJECT_ROOT / "dataset"
MODEL_PATH = PROJECT_ROOT / "trained_model" / "lbph_model.yml"
LABEL_MAP_PATH = PROJECT_ROOT / "trained_model" / "label_map.json"
RECORDS_DIR = PROJECT_ROOT / "attendance_records"
DB_PATH = PROJECT_ROOT / "backend" / "attendance.db"

# Lower LBPH distance = better match; reject above this threshold
LBPH_CONFIDENCE_THRESHOLD = 82.0

SECRET_KEY = os.environ.get("FRAS_SECRET_KEY", "dev-change-me-in-production-use-env")

for d in (DATASET_DIR, MODEL_PATH.parent, RECORDS_DIR):
    d.mkdir(parents=True, exist_ok=True)
