# Census geography in Kepler.gl

Public geometry only: no opportunity, sales or model output.

## View

With Tailscale connected, open:

- Regions: https://m5-studio.tail133394.ts.net/?view=regions
- Divisions: https://m5-studio.tail133394.ts.net/?view=divisions

Both include state and division outlines. The top-right buttons change preset; the top-left
arrow opens Kepler's full editor (layers, tooltips, colours, filters and exports).

The page loads pinned Kepler/React libraries and Carto basemap tiles over the internet; it is
not an offline bundle. No Mapbox account/token is needed for the default basemap. Data stays in
the browser apart from fetching these public files; external CDNs/tile services receive normal
network requests.

`census_regions.kepler.gl.json` and `census_divisions.kepler.gl.json` contain all three datasets
and styling. They can also be loaded into https://kepler.gl/demo using its From URL interface.

## Source and scope

GeoJSON extracts derive from the hub's `data/public/tl_2025_us_state.zip`, grouping by its
`REGION` and `DIVISION` codes. Names match Census's official region/division classification:
https://www.census.gov/programs-surveys/economic-census/guidance-geographies/levels.html

- 4 regions, 9 divisions, 51 state/DC features.
- Alaska and Hawaii included at actual coordinates; no insets.
- Territories (REGION 9 / DIVISION 0) excluded.
- NAD83 source converted to WGS84 longitude/latitude.
- Display geometry simplified with tolerance 0.002 degrees, preserving each geometry's topology.
  This is not exact TIGER linework or a model/M1 geometry; independent layer simplification may
  show small boundary differences when zoomed in.

## Rebuild and serve

From the worktree root:

```bash
python3 tools/kepler/build.py
python3 tests/test_kepler_maps.py
python3 tools/kepler/serve.py 8765 data/kepler
```

With Serve enabled, in another terminal:

```bash
sudo tailscale serve --bg --https=443 http://127.0.0.1:8765
```

The existing server must be stopped before starting another on port 8765. It binds all interfaces
and exposes only this public directory (also reachable on LAN); HTTPS Serve is tailnet-only.
It is not a boot-persistent service.

Kepler page adapted from its official UMD example, pinned to 3.3.0-alpha.6:
https://github.com/keplergl/kepler.gl/blob/master/examples/umd-client/index.html

Saved-map structure follows its v1 dataset/config schemas:
https://github.com/keplergl/kepler.gl/blob/master/src/schemas/src/dataset-schema.ts

## Checks

- Stdlib saved-map test verifies 4/9/51 rows, unchanged source features, valid field/layer bindings
  and the intended filled layer for each preset.
- Chromium smoke test (temporary Playwright install outside the repo) loaded both presets through
  tailnet HTTPS at 1024×768 and 768×1024, verified layer/dataset state and no JavaScript page errors,
  and captured screenshots. Actual iPad Safari remains an owner check.
