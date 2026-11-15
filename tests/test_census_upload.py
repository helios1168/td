"""tools/snowflake/census_upload.py: the rows it would load from the state outlines in the repo.  Snowflake itself
is not reached."""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("census_upload", ROOT / "tools" / "snowflake" / "census_upload.py")
cu = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cu)


def test_the_state_file_gives_56_rows_in_the_census_table_layout():
    meta = cu.CENSUS_LAYERS["states"]
    df = cu.frame(str(ROOT / "tools" / "snowflake" / "geo" / meta["zip"]), meta)
    assert list(df.columns) == ["GEO_ID", "FULLY_QUALIFIED_ID", "GEO_NAME", "STUSPS", "WKT_GEOM"]
    assert len(df) == 56 and df["GEO_ID"].is_unique
    al = df[df["GEO_ID"] == "01"].iloc[0]
    assert (al["FULLY_QUALIFIED_ID"], al["GEO_NAME"], al["STUSPS"]) == ("0400000US01", "Alabama", "AL")
    assert df["WKT_GEOM"].str.match(r"(MULTI)?POLYGON \(").all()
