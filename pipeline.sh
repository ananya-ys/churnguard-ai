#!/usr/bin/env bash
# pipeline.sh — Phase 1: One command = full automated ML pipeline
#
# Usage:
#   ./pipeline.sh                         # default: rf, auto-version, 0.75 AUC gate
#   ./pipeline.sh --estimator gbm         # use gradient boosting
#   ./pipeline.sh --min-auc 0.80          # stricter AUC gate
#   ./pipeline.sh --output v2             # manual version tag (overrides auto-tagging)
#
# What this does:
#   1. Waits for the API to be healthy
#   2. Runs training inside the app container (auto-versioned)
#   3. Auto-registers the model via /api/v1/models
#   4. Auto-promotes if new AUC >= current best
#   5. Logs result

set -euo pipefail

ESTIMATOR=${ESTIMATOR:-rf}
MIN_AUC=${MIN_AUC:-0.75}
DATA_PATH=${DATA_PATH:-data/train.csv}
OUTPUT=${OUTPUT:-}         # empty = auto-version
API_URL=${API_URL:-http://localhost:8000}
MAX_WAIT_SECS=60

# ── Parse args ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --estimator) ESTIMATOR="$2"; shift 2 ;;
    --min-auc)   MIN_AUC="$2";   shift 2 ;;
    --data-path) DATA_PATH="$2"; shift 2 ;;
    --output)    OUTPUT="$2";    shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ChurnGuard AI — Automated Pipeline          ║"
echo "║  Phase 1: One Command = Full MLOps Pipeline  ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "  Estimator : $ESTIMATOR"
echo "  Min AUC   : $MIN_AUC"
echo "  Data      : $DATA_PATH"
echo "  Version   : ${OUTPUT:-<auto>}"
echo ""

# ── Step 1: Wait for API ───────────────────────────────────────────────────────
echo "[1/4] Waiting for API health..."
WAITED=0
until curl -sf "${API_URL}/health" > /dev/null 2>&1; do
  if [ $WAITED -ge $MAX_WAIT_SECS ]; then
    echo "  [ERROR] API not ready after ${MAX_WAIT_SECS}s. Is docker compose up?"
    exit 1
  fi
  echo "  ... waiting (${WAITED}s)"
  sleep 5
  WAITED=$((WAITED + 5))
done
echo "  [OK] API is healthy"

# ── Step 2: Run training ───────────────────────────────────────────────────────
echo ""
echo "[2/4] Running training pipeline..."

OUTPUT_ARG=""
if [ -n "$OUTPUT" ]; then
  OUTPUT_ARG="--output $OUTPUT"
fi

docker compose exec -T app python app/ml/train.py \
  --data-path "$DATA_PATH" \
  --estimator "$ESTIMATOR" \
  --min-auc "$MIN_AUC" \
  $OUTPUT_ARG

TRAIN_EXIT=$?
if [ $TRAIN_EXIT -ne 0 ]; then
  echo ""
  echo "  [GATE FAILED] Training failed or AUC gate not met."
  echo "  No model registered or promoted. Existing production model unchanged."
  exit $TRAIN_EXIT
fi

# ── Step 3: Verify active model ───────────────────────────────────────────────
echo ""
echo "[3/4] Verifying active model..."
ACTIVE=$(curl -sf "${API_URL}/api/v1/models/active" \
  -H "Authorization: Bearer ${ADMIN_TOKEN:-}" \
  2>/dev/null || echo '{"version_tag":"unknown"}')
VERSION=$(echo "$ACTIVE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('version_tag','unknown'))" 2>/dev/null || echo "unknown")
AUC=$(echo "$ACTIVE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('auc_roc','?'))" 2>/dev/null || echo "?")
echo "  Active model : $VERSION  (AUC=$AUC)"

# ── Step 4: Summary ───────────────────────────────────────────────────────────
echo ""
echo "[4/4] Pipeline complete!"
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  PIPELINE COMPLETE                           ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  Active Model : $VERSION"
echo "║  AUC-ROC      : $AUC"
echo "║  Endpoints    :                              ║"
echo "║    Predictions  → POST /api/v1/predict      ║"
echo "║    Model list   → GET  /api/v1/models       ║"
echo "║    Experiments  → GET  /api/v1/experiments  ║"
echo "║    Drift check  → POST /api/v1/drift/check  ║"
echo "║    Metrics      → GET  /metrics             ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
