from __future__ import annotations

import pandas as pd
import pytest

from scripts.export_aug9_vapor_area_fraction import read_values_workbook


def test_read_values_workbook_exports_the_expected_37_states(tmp_path):
    state_counts = {"5gs_22C": 12, "10gs_22C": 8, "15gs_20C": 9, "25gs_20C": 8}
    width = max(state_counts.values()) + 1
    rows = [["vf", *range(1, width)]]
    for case, count in state_counts.items():
        rows.append([case, *[index / 100 for index in range(1, count + 1)]])
    rows.append(["total_bc", *([None] * (width - 1))])
    path = tmp_path / "values.csv"
    pd.DataFrame(rows).to_csv(path, header=False, index=False)

    result = read_values_workbook(path)

    assert len(result) == 37
    assert set(result["case_label"]) == set(state_counts)
    assert result.loc[
        (result["case_label"] == "25gs_20C") & (result["state_voltage"] == 8.0),
        "vapor_area_fraction",
    ].iloc[0] == pytest.approx(0.08)
