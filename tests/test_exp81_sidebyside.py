"""tools/exp81/sidebyside.py (td#81): the legend line of one district."""
from __future__ import annotations

import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "exp81_sidebyside", os.path.join(HERE, "..", "tools", "exp81", "sidebyside.py"))
sidebyside = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sidebyside)


def test_legend_label_lists_states_with_opportunity_and_the_first_metro():
    import pandas as pd
    name = "FI New York-Newark-Jersey City, NY-NJ / Hartford-West Hartford-East Hartford, CT"
    sel = pd.DataFrame({"state": ["NY", "CT", "VT", "NJ"], "m_rel": ["2.5", "1", "0.0", "0.25"],
                        "district_name": [name] * 4, "model_channel": ["FI"] * 4})
    assert sidebyside.legend_label("FI_07", sel) == "FI_07  CT NJ NY  New York-Newark-Jersey City"
