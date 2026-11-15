from pathlib import Path
import importlib.util

import pandas as pd


def load_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "analyze_optical_thermal_association.py"
    spec = importlib.util.spec_from_file_location("optical_thermal_association", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_fold_metrics_preserve_case_level_errors():
    module = load_module()
    predictions = pd.DataFrame(
        {
            "cross_validation": ["leave-one-case-out"] * 4,
            "model": ["thermal baseline"] * 4,
            "case_label": ["case_a", "case_a", "case_b", "case_b"],
            "residual_c": [1.0, -1.0, 2.0, 2.0],
        }
    )
    result = module.cross_validated_fold_metrics(predictions)
    assert result["held_out_case"].tolist() == ["case_a", "case_b"]
    assert result["rmse_c"].tolist() == [1.0, 2.0]
    assert result["mae_c"].tolist() == [1.0, 2.0]
