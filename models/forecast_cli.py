"""CLI for Phase 3 — build dataset, train, forecast, verify.

Usage:
    python -m models.forecast_cli build-dataset [--years 5]
    python -m models.forecast_cli train --model lstm --name lstm-real-v2
    python -m models.forecast_cli list
    python -m models.forecast_cli forecast --model-name lstm-real-v2 --loc KA-BLR-001
    python -m models.forecast_cli verify
"""

import argparse
import json
import logging
import sys
import time
import uuid
from pathlib import Path

import torch

from models.build_dataset import build_dataset, verify_dataset
from models.data_loader import load_config, load_data, load_scalers, needs_scaling, save_scalers
from models.evaluator import evaluate_model
from models.forecast_provenance import ForecastResult, ForecastStore
from models.registry import ModelRegistry
from models.trainer import get_device, train_model

logger = logging.getLogger(__name__)

TARGET_NAMES = ["Rainfall", "MaxTemp", "MinTemp"]
_STD_RATIO_THRESHOLD = 0.1


def cmd_build_dataset(args: argparse.Namespace) -> int:
    manifest = build_dataset(
        lat=args.lat,
        lon=args.lon,
        name=args.name,
        years=args.years,
        output_dir=args.output,
    )
    ok = verify_dataset(args.output)
    logger.info("Dataset built: %s records, verified=%s", manifest["total_records"], ok)
    return 0 if ok else 1


def _invalidate_broken_lstm():
    registry = ModelRegistry()
    try:
        entry = registry.get("lstm-real-v1")
        if entry.get("status") != "REJECTED":
            registry.update_status(
                "lstm-real-v1", "REJECTED", reason="MODEL_COLLAPSE / TRAINING_PREPROCESSING_BUG"
            )
            logger.info("Invalidated lstm-real-v1 (MODEL_COLLAPSE)")
    except KeyError:
        pass


def cmd_train(args: argparse.Namespace) -> int:
    _invalidate_broken_lstm()

    config = load_config()
    data_dir = args.data_dir or "data/real"
    should_scale = needs_scaling(args.model)

    train_loader, val_loader, test_loader, feat_scaler, tgt_scaler = load_data(
        config,
        data_dir=data_dir,
        require_real=True,
        scale=should_scale,
    )
    n_features = len(config["data"]["feature_columns"])
    n_targets = len(config["data"]["target_columns"])

    from models.predictor import create_model

    model = create_model(args.model, n_features, n_targets, config)
    model_name = args.name or f"{args.model}-real-{uuid.uuid4().hex[:8]}"

    train_model(
        model,
        train_loader,
        val_loader,
        config,
        checkpoint_dir="models/checkpoints",
        model_name=model_name,
        model_type=args.model,
    )

    device = get_device(config["training"].get("device", "auto"))
    ckpt_path = Path("models/checkpoints") / f"{model_name}_best.pt"
    model.load_state_dict(torch.load(ckpt_path, map_location="cpu", weights_only=True))
    model = model.to(device)

    eval_result = evaluate_model(
        model,
        test_loader,
        device,
        target_scaler=tgt_scaler if should_scale else None,
        target_names=TARGET_NAMES,
        std_ratio_threshold=_STD_RATIO_THRESHOLD,
    )

    collapse = eval_result["collapse_check"]

    manifest = json.loads((Path(data_dir) / "dataset_manifest.json").read_text())
    training_run_id = uuid.uuid4().hex[:12]
    registry = ModelRegistry()

    status = "EXPERIMENTAL"
    reason = ""
    if collapse["collapsed"]:
        status = "REJECTED"
        reason = "MODEL_COLLAPSE targets: " + ",".join(collapse["collapsed_targets"])
        logger.error("Model collapsed on targets: %s", collapse["collapsed_targets"])
    elif args.model == "baseline" or args.model == "lstm":
        status = "VALIDATED"

    registry.register(
        name=model_name,
        architecture=type(model).__name__,
        checkpoint_path=str(ckpt_path),
        metrics=eval_result["metrics"],
        config=config,
        dataset_id=manifest.get("source_url", ""),
        training_run_id=training_run_id,
        authenticity="REAL",
        data_provenance={
            "source": manifest.get("source", ""),
            "location": manifest.get("location", {}),
            "date_range": manifest.get("date_range", {}),
            "total_records": manifest.get("total_records", 0),
        },
        status=status,
    )

    if should_scale:
        save_scalers(feat_scaler, tgt_scaler, model_name)

    if reason:
        registry.update_status(model_name, status, reason=reason)

    per_target = eval_result["per_target_metrics"]
    logger.info("Training complete: %s", model_name)
    logger.info(
        "  Aggregate RMSE=%.4f R2=%.4f",
        eval_result["metrics"]["rmse"],
        eval_result["metrics"]["r2"],
    )
    for tname, tm in per_target.items():
        logger.info("  %s: RMSE=%.4f MAE=%.4f R2=%.4f", tname, tm["rmse"], tm["mae"], tm["r2"])
    logger.info("  Status: %s%s", status, f" ({reason})" if reason else "")
    logger.info("  Model registered with training_run_id=%s", training_run_id)
    return 0


def cmd_list(_args: argparse.Namespace) -> int:
    registry = ModelRegistry()
    models = registry.list_models()
    if not models:
        print("No models registered.")
        return 0
    header = f"{'Name':25s} {'Architecture':20s} {'Auth':8s} {'Status':12s} {'RMSE':8s} {'R²':8s}"
    print(header)
    print("-" * len(header))
    for m in sorted(models, key=lambda x: x.get("name", "")):
        auth = m.get("authenticity", "UNKNOWN")
        status = m.get("status", "?")
        rmse = m.get("metrics", {}).get("rmse", float("nan"))
        r2 = m.get("metrics", {}).get("r2", float("nan"))
        rmse_s = f"{rmse:.4f}" if not isinstance(rmse, float) or rmse == rmse else "N/A"
        r2_s = f"{r2:.4f}" if not isinstance(r2, float) or r2 == r2 else "N/A"
        print(
            f"  {m['name']:25s} {m['architecture']:20s} {auth:8s} {status:12s} {rmse_s:8s} {r2_s:8s}"
        )
    return 0


_ARCH_TO_MODEL = {
    "BaselineModel": "baseline",
    "LSTMModel": "lstm",
    "TransformerModel": "transformer",
}


def cmd_forecast(args: argparse.Namespace) -> int:
    registry = ModelRegistry()
    entry = registry.get(args.model_name)
    if entry.get("authenticity") != "REAL":
        logger.warning(
            "Model '%s' authenticity is '%s' - not REAL-trained",
            args.model_name,
            entry.get("authenticity"),
        )

    config = load_config()
    n_features = len(config["data"]["feature_columns"])
    n_targets = len(config["data"]["target_columns"])

    arch = entry.get("architecture", "")
    model_type = _ARCH_TO_MODEL.get(arch)
    if not model_type:
        logger.error("Unknown architecture '%s' for model '%s'", arch, args.model_name)
        return 1

    from models.predictor import load_model, predict

    model = load_model(
        model_type,
        entry["checkpoint_path"],
        n_features,
        n_targets,
        config,
    )

    should_scale = needs_scaling(model_type)
    feat_scaler, tgt_scaler = load_scalers(args.model_name)

    data_dir = Path(args.data_dir or "data/real")
    import pandas as pd

    train_df = pd.read_csv(data_dir / "training.csv")
    test_df = pd.read_csv(data_dir / "testing.csv")
    feat_cols = config["data"]["feature_columns"]
    config["data"]["target_columns"]
    seq_len = config["data"]["sequence_length"]

    cat_cols = [
        c
        for c in feat_cols
        if pd.api.types.is_string_dtype(test_df[c]) or test_df[c].dtype == "object"
    ]
    for df in [train_df, test_df]:
        for c in cat_cols:
            df[c] = pd.Categorical(df[c]).codes

    if should_scale and (feat_scaler is None or tgt_scaler is None):
        logger.error(
            "Model '%s' requires scaling but no scalers found. Re-train with scaling enabled.",
            args.model_name,
        )
        return 1

    test_feat = torch.tensor(test_df[feat_cols].values, dtype=torch.float32)
    input_seq = test_feat[-seq_len:].unsqueeze(0)

    if should_scale and feat_scaler is not None:
        input_seq = feat_scaler.transform(input_seq)

    result = predict(model, input_seq, target_scaler=tgt_scaler if should_scale else None)

    preds = result["predictions"][0]
    fr = ForecastResult(
        location_id=args.loc,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
        rainfall=preds[0],
        max_temp=preds[1],
        min_temp=preds[2],
        confidence=1.0 - (entry.get("metrics", {}).get("rmse", 1.0) / 50.0),
        model_id=args.model_name,
        training_run_id=entry.get("training_run_id", ""),
        model_architecture=entry.get("architecture", ""),
        dataset_id=entry.get("dataset_id", ""),
        authenticity=entry.get("authenticity", ""),
        horizon_days=1,
        source_twin_version=0,
        physics_validated=True,
    )
    store = ForecastStore()
    store.save(fr)
    print(
        f"Forecast for {args.loc}: Rain={preds[0]:.1f}mm "
        f"MaxT={preds[1]:.1f}C MinT={preds[2]:.1f}C "
        f"(model={args.model_name}, id={fr.forecast_id})"
    )
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    ok = verify_dataset(args.data_dir)
    logger.info("Dataset verification: %s", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


def cmd_history(args: argparse.Namespace) -> int:
    store = ForecastStore()
    results = store.list_recent(args.limit)
    if not results:
        print("No forecast history.")
        return 0
    for r in results:
        print(
            f"  {r.forecast_id} | {r.location_id} | {r.timestamp} | "
            f"Rain={r.rainfall:.1f} Tmax={r.max_temp:.1f} Tmin={r.min_temp:.1f} | "
            f"model={r.model_id}"
        )
    return 0


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    parser = argparse.ArgumentParser(description="Phase 3 - Forecasting CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build-dataset", help="Fetch real data from Open-Meteo")
    p_build.add_argument("--lat", type=float, default=12.97)
    p_build.add_argument("--lon", type=float, default=77.59)
    p_build.add_argument("--name", type=str, default="Bengaluru")
    p_build.add_argument("--years", type=int, default=5)
    p_build.add_argument("--output", type=str, default="data/real")
    p_build.set_defaults(func=cmd_build_dataset)

    p_train = sub.add_parser("train", help="Train a model on real data")
    p_train.add_argument(
        "--model", type=str, default="lstm", choices=["baseline", "lstm", "transformer"]
    )
    p_train.add_argument(
        "--name", type=str, default=None, help="Registry name (default: auto-generated)"
    )
    p_train.add_argument("--data-dir", type=str, default="data/real")
    p_train.set_defaults(func=cmd_train)

    p_list = sub.add_parser("list", help="List registered models")
    p_list.set_defaults(func=cmd_list)

    p_fc = sub.add_parser("forecast", help="Generate forecast")
    p_fc.add_argument("--model-name", type=str, required=True)
    p_fc.add_argument("--loc", type=str, default="KA-BLR-001")
    p_fc.add_argument("--data-dir", type=str, default="data/real")
    p_fc.set_defaults(func=cmd_forecast)

    p_ver = sub.add_parser("verify", help="Verify dataset integrity")
    p_ver.add_argument("--data-dir", type=str, default="data/real")
    p_ver.set_defaults(func=cmd_verify)

    p_hist = sub.add_parser("history", help="Show recent forecasts")
    p_hist.add_argument("--limit", type=int, default=10)
    p_hist.set_defaults(func=cmd_history)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
