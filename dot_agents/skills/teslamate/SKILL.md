---
name: teslamate
description: Use when the user asks about their Tesla's history or statistics recorded by TeslaMate, such as drives, trips, distance, efficiency or consumption, charging sessions, energy and cost, battery health or degradation, range, locations, sleep and online states, or software updates, or wants to query TeslaMate data or its Grafana dashboards.
---

# TeslaMate

TeslaMate logs one Tesla (Model Y, `car_id = 1`) to PostgreSQL. The only way in is the Grafana HTTP API, which runs SQL against the `TeslaMate` datasource. The token belongs to a Viewer service account: it can query and read dashboards, and cannot change Grafana.

## Access

Use the bundled scripts for every request. They load `TESLAMATE_GRAFANA_URL` and `TESLAMATE_GRAFANA_TOKEN` even when the current shell lacks them. Never print the token or read the files that define it (`~/.zshenv`); to diagnose access, run a script and read its error.

```bash
bash ~/.agents/skills/teslamate/scripts/query.sh "SELECT id, start_date, distance FROM drives ORDER BY start_date DESC LIMIT 5"
bash ~/.agents/skills/teslamate/scripts/query.sh < query.sql   # multi-line SQL, e.g. a heredoc
bash ~/.agents/skills/teslamate/scripts/api.sh '/api/search?type=dash-db'   # any Grafana GET, prints JSON
```

`query.sh` prints TSV with a header row, prints `(0 rows)` on stderr for an empty result, and prints the database error and exits 1 on failure. The datasource logs in as `grafana_ro`, a PostgreSQL role with only `SELECT`, and the script also wraps the query in a `READ ONLY` transaction.

## Conventions

- Timestamps are `timestamp without time zone` in UTC, and `query.sh` prints them as `YYYY-MM-DD HH:MM:SS` with no zone. The user is in Asia/Tokyo. Filter a JST period with `(start_date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Tokyo') >= '2026-08-01'`, and display JST with `to_char(start_date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Tokyo', 'YYYY-MM-DD HH24:MI') AS start_jst`. Apply that pattern only to table columns; `now()` is `timestamptz`, so use `now() AT TIME ZONE 'Asia/Tokyo'` for it.
- Units: distance and range in km (`*_km` columns, `drives.distance`), energy in kWh, temperature in °C, power in kW, `cost` in JPY. The preferred range is `rated`, so use `rated_*` columns, not `ideal_*`.
- Logging began on 2026-09-01 JST. When a period returns no rows, check `min(start_date)` before reporting zero usage, and say that the data does not cover the period.
- `end_date IS NULL` marks a drive or charge still in progress; exclude it from totals.
- Drives under 0.5 km are parking moves. List them when asked for drives, marked as such, and exclude them from efficiency figures.
- The car usually rests in `offline`, not `asleep`. Treat both as parked standby, as the Vampire Drain dashboard does.

## Schema

| Table | Key columns |
|---|---|
| `drives` | `start_date`, `end_date`, `distance`, `duration_min`, `start_km`/`end_km` (odometer), `start_rated_range_km`/`end_rated_range_km`, `speed_max`, `outside_temp_avg`, `start_address_id`/`end_address_id`, `start_geofence_id`/`end_geofence_id`, `ascent`/`descent` |
| `charging_processes` | `start_date`, `end_date`, `charge_energy_added` (into the battery), `charge_energy_used` (from the grid), `cost`, `duration_min`, `start_battery_level`/`end_battery_level`, `start_rated_range_km`/`end_rated_range_km`, `address_id`, `geofence_id` |
| `charges` | Samples within a session (`charging_process_id`): `date`, `charger_power`, `charger_phases`, `fast_charger_present` (true = DC), `fast_charger_brand`, `battery_level`, `usable_battery_level`, `rated_battery_range_km` |
| `positions` | Samples: `date`, `latitude`, `longitude`, `speed`, `power`, `odometer`, `battery_level`, `usable_battery_level`, `rated_battery_range_km`, `inside_temp`, `outside_temp`, `drive_id`, `tpms_pressure_*` |
| `states` | `state` (enum `states_status`: `online`, `offline`, `asleep`; cast with `state::text` for text operations), `start_date`, `end_date`. `online` includes driving and charging |
| `updates` | `version`, `start_date`, `end_date`. The first row, recorded when logging began with `start_date = end_date`, holds the version already installed, not an install time |
| `addresses` | `name`, `road`, `house_number`, `city`, `display_name` |
| `geofences` | `name` (user labels such as `Home`), `cost_per_unit`, `session_fee` |

Every table except `addresses`, `geofences`, and `settings` has `car_id`. Name a place with `COALESCE(g.name, a.name, a.road, a.city)` after joining the geofence and address.

## Recipes

AC or DC per session (a session with no samples counts as AC):

```sql
SELECT cp.id, cp.start_date, cp.charge_energy_added, cp.cost,
       CASE WHEN bool_or(c.fast_charger_present) THEN 'DC' ELSE 'AC' END AS type
FROM charging_processes cp LEFT JOIN charges c ON c.charging_process_id = cp.id
WHERE cp.end_date IS NOT NULL
GROUP BY cp.id
```

`cars.efficiency` is NULL, so derive efficiency, in kWh per rated km, from charging sessions. This matches the dashboards, which store it multiplied by 100 (kWh per 100 km) in the Battery Health `aux` variable. Report how many sessions it came from:

```sql
SELECT mode() WITHIN GROUP (ORDER BY e) AS kwh_per_rated_km, count(*) AS sessions
FROM (SELECT round((charge_energy_added / NULLIF(end_rated_range_km - start_rated_range_km, 0))::numeric, 3) AS e
      FROM charging_processes
      WHERE duration_min > 10 AND end_battery_level <= 95 AND charge_energy_added > 0) s
WHERE e IS NOT NULL
```

A drive's consumption is `(start_rated_range_km - end_rated_range_km) * kwh_per_rated_km` kWh, and Wh/km is that × 1000 / `distance`. Usable capacity is `rated_battery_range_km * kwh_per_rated_km / usable_battery_level * 100` over charge samples. The "original" capacity on Battery Health is the maximum observed since logging began, not a factory figure.

## Dashboards

For a question a TeslaMate dashboard answers (battery health, efficiency, vampire drain, projected range, statistics), reuse the dashboard's SQL instead of inventing a formula:

```bash
bash ~/.agents/skills/teslamate/scripts/api.sh '/api/search?type=dash-db' | jq -r '.[] | "\(.uid)\t\(.title)"'
bash ~/.agents/skills/teslamate/scripts/api.sh /api/dashboards/uid/<uid> |
  jq -r '.dashboard | (.panels[]?, .panels[]?.panels[]?) | select(.targets) | "## \(.title)\n\(.targets[].rawSql // empty)"'
bash ~/.agents/skills/teslamate/scripts/api.sh /api/dashboards/uid/<uid> |
  jq -r '.dashboard.templating.list[] | "\(.name) = \(.current.value // "") :: \(.query | if type == "object" then .query else . end)"'
```

Substitute Grafana variables, in both `$name` and `${name}` forms, before running panel SQL:

| Variable | Value |
|---|---|
| `$car_id` | `1` |
| `$length_unit` | `km` |
| `$temp_unit` | `C` |
| `$preferred_range` | `rated` |
| `$__timezone` | `Asia/Tokyo` |
| `$__timeFrom()`, `$__timeTo()` | quoted UTC timestamps |
| `$__timeFilter(col)` | `col BETWEEN <from> AND <to>` |
| Anything else | the variable's `current.value` from `templating.list` |

Dashboard-specific variables change results, so state the value used. For example, Vampire Drain's `$duration` (minimum parked hours, default 6) and Battery Health's `aux` (a shared CTE). Lag-based SQL, such as Vampire Drain's, drops intervals that cross the time range edges; widen the range or account for them. `convert_km`, `convert_celsius`, and `convert_m` exist in the database.

## Reporting

State the period and timezone used, the dashboard variables and thresholds applied, the drives or sessions excluded, and the sample count behind derived figures (efficiency, capacity), labeled as estimates.
