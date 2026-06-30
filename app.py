import json
from datetime import datetime

import requests
from shiny import App, Inputs, Outputs, Session, reactive, render, ui

BASE_URL_DEFAULT = "https://cf.nascar.com"
DEFAULT_REFRESH_SECONDS = 60.0

FLAG_STATE_LABELS = {
    0: "None",
    1: "Green",
    2: "Yellow",
    3: "Red",
    4: "White",
    5: "Checkered",
    6: "Who Knows 1",
    7: "Who Knows 2",
    8: "Hot Track",
    9: "Cold Track",
}

FLAG_COLORS = {
    1: "#0f0",
    2: "#ff0",
    3: "#f00",
    4: "#fff",
    5: "#888",
    6: "#0df",
    7: "#404"
}


RUN_TYPE_LABELS = {
    1: "Practice",
    2: "Qualifying",
    3: "Race",
}

SERIES_LABELS = {
    1: "Cup",
    2: "O'Reilly",
    3: "Trucks",
    4: "ARCA Menards",
}

HEADERS = {
    "User-Agent": "NASCARShinyDashboard/1.0",
    "Accept": "application/json",
}


def build_error_card(message: str):
    return ui.tags.div(
        ui.tags.strong("Error: "),
        message,
        style=(
            "background:#a00;border:1px solid #f00;"
            "padding:0.75rem; border-radius:0.5rem; margin-bottom:1rem;"
        ),
    )


def fetch_json(url: str, timeout: int = 10):
    try:
        response = requests.get(url, timeout=timeout, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        return {"error": str(exc)}
    except json.JSONDecodeError as exc:
        return {"error": f"Invalid JSON response: {exc}"}


def normalize_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def format_value(value):
    if value is None:
        return []
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


def make_table(columns, rows, max_rows=40):
    if not rows:
        return ui.tags.div("No data available.")

    header_cells = [ui.tags.th(col) for col in columns]
    body_rows = []
    for row in rows[:max_rows]:
        body_rows.append(
            ui.tags.tr(
                *[ui.tags.td(format_value(row.get(col, "—"))) for col in columns]
            )
        )

    return ui.tags.table(
        ui.tags.thead(ui.tags.tr(*header_cells)),
        ui.tags.tbody(*body_rows),
    )

def make_sortable_table(columns, rows, table_id="sortable-table", max_rows=50):
    if not rows:
        return ui.tags.div("No data available.")

    # Create headers with pointer cursors and click events
    header_cells = [
        ui.tags.th(
            col,
            style="cursor: pointer; user-select: none;",
            onclick=f"sortTable('{table_id}', {i})",
            title="Click to sort"
        )
        for i, col in enumerate(columns)
    ]
    
    body_rows = []
    for row in rows[:max_rows]:
        body_rows.append(
            ui.tags.tr(
                *[ui.tags.td(format_value(row.get(col, "—"))) for col in columns]
            )
        )

    # Injecting vanilla JS to handle the sorting behavior dynamically
    js_script = ui.tags.script(ui.HTML("""
    function sortTable(tableId, n) {
        var table = document.getElementById(tableId);
        var rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
        switching = true;
        dir = "asc"; 
        
        // Clear old visual arrow indicators
        var headers = table.rows[0].getElementsByTagName("TH");
        for (var j = 0; j < headers.length; j++) {
            headers[j].innerHTML = headers[j].innerHTML.replace(' ▲', '').replace(' ▼', '');
        }

        while (switching) {
            switching = false;
            rows = table.rows;
            for (i = 1; i < (rows.length - 1); i++) {
                shouldSwitch = false;
                x = rows[i].getElementsByTagName("TD")[n];
                y = rows[i + 1].getElementsByTagName("TD")[n];
                
                var xVal = x.textContent || x.innerText;
                var yVal = y.textContent || y.innerText;
                
                var xNum = parseFloat(xVal);
                var yNum = parseFloat(yVal);
                
                // Allow numeric sorting for actual numbers, fallback to string
                var isXNum = !isNaN(xNum) && xVal.trim() !== "—";
                var isYNum = !isNaN(yNum) && yVal.trim() !== "—";
                
                var cmpX = isXNum ? xNum : xVal.toLowerCase();
                var cmpY = isYNum ? yNum : yVal.toLowerCase();
                
                if (dir == "asc") {
                    if (cmpX > cmpY) { shouldSwitch = true; break; }
                } else if (dir == "desc") {
                    if (cmpX < cmpY) { shouldSwitch = true; break; }
                }
            }
            if (shouldSwitch) {
                rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                switching = true;
                switchcount++;
            } else {
                if (switchcount == 0 && dir == "asc") {
                    dir = "desc";
                    switching = true;
                }
            }
        }
        
        // Add visual arrow indicator to the active sorted column
        headers[n].innerHTML += (dir == "asc") ? " ▲" : " ▼";
    }
    """))

    return ui.tags.div(
        js_script,
        ui.tags.table(
            ui.tags.thead(ui.tags.tr(*header_cells)),
            ui.tags.tbody(*body_rows),
            id=table_id
        )
    )

def build_summary_card(
    title: str,
    value: str,
    subtitle: str = "",
    style: str = "",
):
    return ui.tags.div(
        ui.tags.h6(title, class_="summary-title"),
        ui.tags.h3(value, class_="summary-value"),
        ui.tags.h6(subtitle, class_="summary-subtitle"),
        class_="summary-card",
        style=style,
    )

def build_table_section(title: str, table_ui, caption: str = ""):
    return ui.tags.section(
        ui.tags.h2(title, style="margin-bottom:1 rem;"),
        table_ui,
    )


def create_leaderboard_table(feed):
    vehicles = feed.get("vehicles") or []
    if not isinstance(vehicles, list):
        return ui.tags.div("No leaderboard data available.")

    vehicles = sorted(vehicles, key=lambda v: v.get("running_position", 999))
    rows = []
    for vehicle in vehicles[:40]:
        driver = vehicle.get("driver") or {}
        rows.append(
            {
                "Position": vehicle.get("running_position", "—"),
                "Car": vehicle.get("vehicle_number", "—"),
                "Driver": driver.get("full_name", "—"),
                "Gap": vehicle.get("delta", "—"),
                "Laps": vehicle.get("laps_completed", "—"),
                "Led": sum(lap.get("end_lap", 0) - lap.get("start_lap", 0) for lap in (vehicle.get("laps_led") or [])),
                "Best Lap": vehicle.get("best_lap_time", "—"),
            }
        )
    return make_table(
        ["Position", "Car", "Driver", "Gap", "Laps", "Led", "Best Lap"],
        rows,
        max_rows=40,
    )


def create_points_table(points):
    if not isinstance(points, list):
        return ui.tags.div("No points standings data available.")
    rows = []
    for item in points[:40]:
        full_name = " ".join(
            [item.get("first_name", ""), item.get("last_name", "")]
        ).strip()
        rows.append(
            {
                "Pos": item.get("points_position", "—"),
                "Car": item.get("car_number", item.get("vehicle_number", "—")),
                "Driver": full_name or item.get("full_name", "—"),
                "Points": item.get("points", "—"),
                "To Leader": item.get("delta_leader", "—"),
                "To Next": item.get("delta_next", "—"),
                "Wins": item.get("wins", "—"),
                "Top 5": item.get("top_5", "—"),
                "Top 10": item.get("top_10", "—"),
                "Poles": item.get("poles", "—"),
                "Last Race Pts": item.get("points_earned_this_race", "—"),
                "Stage 1 Pts": item.get("stage_1_points", "—"),
                "Stage 2 Pts": item.get("stage_2_points", "—"),
                "Fastest Lap": item.get("is_fastest_lap_point", "—"),
            }
        )
    return make_table(
        [
            "Pos",
            "Car",
            "Driver",
            "Points",
            "To Leader",
            "To Next",
            "Wins",
            "Top 5",
            "Top 10",
            "Poles",
            "Last Race Pts",
            "Stage 1 Pts",
            "Stage 2 Pts",
            "Fastest Lap",
        ],
        rows,
    )


def create_stage_points_table(stage_data):
    if not stage_data:
        return ui.tags.div("No stage points data available.")

    if isinstance(stage_data, dict) and "results" in stage_data:
        stage_data = [stage_data]

    rows = []
    for stage in stage_data:
        stage_num = stage.get("stage_number")
        for result in stage.get("results", "—")[:10]:
            rows.append(
                {
                    "Stage": stage_num,
                    "Pos": result.get("position", "—"),
                    "Car": result.get("vehicle_number", "—"),
                    "Driver": result.get("full_name", "—"),
                    "Points": result.get("stage_points", "—"),
                }
            )
    if not rows:
        return ui.tags.div("No stage points results found.")
    return make_table(["Stage", "Pos", "Car", "Driver", "Points"], rows)


def create_flag_tracker_bar(flag_data, current_lap: int, total_laps: int):
    if not flag_data or not isinstance(flag_data, list):
        return ui.tags.div("No flag event data available.")

    flags = []
    for f in flag_data:
        try:
            lap = int(f.get("lap_number", 0))
            state = int(f.get("flag_state", 1))
            desc = f.get("comment", "")
            flags.append({"lap": lap, "state": state, "desc": desc})
        except (ValueError, TypeError):
            continue
    
    flags = sorted(flags, key=lambda x: x["lap"])
    
    if not flags:
         return ui.tags.div("No race segments to display yet.")

    segments = []
    for i, flag in enumerate(flags):
        start_lap = flag["lap"]
        end_lap = flags[i + 1]["lap"] if i + 1 < len(flags) else max(start_lap, current_lap)
        
        length = max(end_lap - start_lap, 0.5)
        width_pct = (length / max(total_laps, current_lap, 1)) * 100
        
        bg_color = FLAG_COLORS.get(flag["state"], "transparent")
        tooltip_text = f"Lap {start_lap}: {flag['desc']}"

        pointer = ui.tags.div(f"{start_lap}",
            style="position: absolute; bottom: 100%; left: 0; transform: translateX(-50%); font-size: 0.65rem; color: var(--text-color); white-space: nowrap; margin-bottom: 4px;"
        )

        segment = ui.tags.div(
            pointer,
            title=tooltip_text,
            style=f"width: {width_pct}%; background-color: {bg_color}; height: 12px; position: relative; border-right: 1px solid #222;"
        )
        segments.append(segment)

    return ui.tags.div(
        ui.tags.p("Hover over flag segments to view notes."),
        ui.tags.div(
            *segments,
            style="display: flex; width: 100%; height: 36px; background: transparent; margin-top: 1.5rem; margin-bottom: 1rem; border-radius: 2px;"
        ),
        style = "margin-bottom: 2rem;"
    )

def server(input: Inputs, output: Outputs, session: Session):

    @reactive.calc
    def dashboard_data():
        refresh_seconds = input.refresh_interval() or DEFAULT_REFRESH_SECONDS
        base_url = BASE_URL_DEFAULT
        reactive.invalidate_later(max(float(refresh_seconds), 1.0))

        feed = fetch_json(normalize_url(base_url, "live/feeds/live-feed.json"))
        flag_data = fetch_json(normalize_url(base_url, "live/feeds/live-flag-data.json"))
        pit_data = fetch_json(normalize_url(base_url, "live/feeds/live-pit-data.json"))
        points_data = fetch_json(normalize_url(base_url, "live/feeds/live-points.json"))
        stage_data = fetch_json(normalize_url(base_url, "live/feeds/live-stage-points.json"))

        return {
            "feed": feed,
            "flag_data": flag_data,
            "pit_data": pit_data,
            "points_data": points_data,
            "stage_data": stage_data,
            "updated_at": datetime.now(),
            "base_url": base_url,
        }

    # Centralized assignment calculation isolated strictly to Year selections
    @reactive.calc
    @reactive.event(input.loop_year)
    def loop_year_resources():
        year = input.loop_year()
        if not year:
            return {}, {}

        race_url = normalize_url(BASE_URL_DEFAULT, f"cacher/{year}/race_list_basic.json")
        drivers_url = normalize_url(BASE_URL_DEFAULT, "cacher/drivers.json")
        
        race_data = fetch_json(race_url)
        drivers_data = fetch_json(drivers_url)
        
        drivers_map = {}
        if isinstance(drivers_data, dict) and "error" not in drivers_data:
            driver_list = drivers_data.get("response", [])
        elif isinstance(drivers_data, list):
            driver_list = drivers_data
        else:
            driver_list = []

        for d in driver_list:
            d_id = d.get("Nascar_Driver_ID")
            name = d.get("Full_Name") or "Unknown Driver"
            if d_id:
                try:
                    drivers_map[int(d_id)] = name
                except ValueError:
                    continue
                    
        return race_data, drivers_map

    @output
    @render.ui
    def session_card():
        try:
            data = dashboard_data()
            feed = data["feed"]
            if not isinstance(feed, dict) or "error" in feed:
                return build_error_card(feed.get("error", "Unable to load live feed."))

            run_name = feed.get("run_name", "Unknown")
            track_name = feed.get("track_name", "Unknown")
            series_id = feed.get("series_id")
            run_type = feed.get("run_type")
            flag_state = feed.get("flag_state")
            lap_number = feed.get("lap_number", "—")
            laps_in_race = feed.get("laps_in_race", "—")

            vehicles = feed.get("vehicles") or []
            leader = next((v for v in vehicles if v.get("running_position") == 1), vehicles[0] if vehicles else None)

            leader_name, leader_car = "—", "—"
            if isinstance(leader, dict):
                driver = leader.get("driver") or {}
                leader_name = driver.get("full_name", "—")
                leader_car = leader.get("vehicle_number", "—")

            flag_color = FLAG_COLORS.get(flag_state, "#888")

            return ui.tags.div(
                ui.tags.div(
                    build_summary_card("Latest Race", run_name, f"{track_name}"),
                    build_summary_card(
                        "Session",
                        RUN_TYPE_LABELS.get(run_type, "Unknown"),
                        f"Series: {SERIES_LABELS.get(series_id, f'Series {series_id}')}",
                        style=f"background:{flag_color}; border:1px solid {flag_color};",
                    ),
                    build_summary_card("Leader", f"#{leader_car} {leader_name}", f"Lap {lap_number} / {laps_in_race}"),
                    style="display:flex; gap:1rem; flex-wrap:wrap; margin-bottom:1rem;",
                ),
            )
        except Exception as e:
            return build_error_card(f"Error rendering session card: {str(e)}")

    @output
    @render.ui
    def flag_tracker_section():
        try:
            data = dashboard_data()
            flag_data = data["flag_data"]
            feed = data["feed"]
            
            if isinstance(flag_data, dict) and "error" in flag_data:
                return build_error_card(flag_data["error"])
                
            try:
                total_laps = int(feed.get("laps_in_race", 100)) if isinstance(feed, dict) else 100
                if total_laps <= 0:
                    total_laps = 100
            except (ValueError, TypeError):
                total_laps = 100

            try:
                current_lap = int(feed.get("lap_number", 0)) if isinstance(feed, dict) else 0
            except (ValueError, TypeError):
                current_lap = 0
                
            return build_table_section("Live Flag Tracker", create_flag_tracker_bar(flag_data, current_lap, total_laps))
        except Exception as e:
            return build_error_card(f"Error rendering flag tracker: {str(e)}")
    
    @output
    @render.ui
    def leaderboard_section():
        try:
            data = dashboard_data()
            feed = data["feed"]
            if not isinstance(feed, dict) or "error" in feed:
                return build_error_card(feed.get("error", "Unable to load leaderboard."))

            return build_table_section("Live Leaderboard", create_leaderboard_table(feed))
        except Exception as e:
            return build_error_card(f"Error rendering leaderboard: {str(e)}")

    @output
    @render.ui
    def points_section():
        try:
            data = dashboard_data()
            points = data["points_data"]
            if not isinstance(points, list) and isinstance(points, dict) and "error" in points:
                return build_error_card(points.get("error", "Unable to load points data."))

            return build_table_section("Live Standings", create_points_table(points))
        except Exception as e:
            return build_error_card(f"Error rendering standings: {str(e)}")

    @output
    @render.ui
    def stage_section():
        try:
            data = dashboard_data()
            stage = data["stage_data"]
            if isinstance(stage, dict) and "error" in stage:
                return build_error_card(stage["error"])
            return build_table_section("Live Stage Points", create_stage_points_table(stage))
        except Exception as e:
            return build_error_card(f"Error rendering stage points: {str(e)}")

    @output
    @render.ui
    def metadata_section():
        data = dashboard_data()
        refreshed = data["updated_at"].strftime("%Y-%m-%d %H:%M:%S")
        return ui.tags.div(
                ui.tags.p(f"Last updated {refreshed}"),
            )
    
    @reactive.Effect
    def update_loop_races():
        series = input.loop_series()
        race_data, _ = loop_year_resources()
        
        choices = {}
        if isinstance(race_data, dict) and "error" not in race_data:
            series_key = f"series_{series}"
            races = race_data.get(series_key, [])
            
            for r in races:
                rid = str(r.get("race_id"))
                name = r.get("race_name", f"Race {rid}")
                choices[rid] = name
                
        if not choices:
            choices = {"0": "No races available for this selection"}
            
        ui.update_select("loop_race", choices=choices)

    @output
    @render.ui
    def loop_data_section():
        year = input.loop_year()
        series = input.loop_series()
        race_id = input.loop_race()
        
        if not race_id or race_id == "0":
            return ui.tags.div(ui.tags.p("Please select a valid race to view loop stats."))
            
        url = normalize_url(BASE_URL_DEFAULT, f"loopstats/prod/{year}/{series}/{race_id}.json")
        data = fetch_json(url)
        
        drivers = []
        if isinstance(data, list) and len(data) > 0:
            if "drivers" in data[0]:
                drivers = data[0]["drivers"]
            else:
                drivers = data
        elif isinstance(data, dict):
            drivers = data.get("drivers", [])
            
        if not drivers:
            return ui.tags.div(ui.tags.p("No loop data drivers found for this event."))

        _, drivers_map = loop_year_resources()

        col_mapping = {
            "Driver": ["driver_id"],
            "Finish": ["ps"],
            "Closing Diff": ["closing_laps_diff"],
            "Closing Pos": ["closing_ps"],
            "Mid Pos": ["mid_ps"],
            "Start": ["start_ps"],
            "Best": ["best_ps"],
            "Worst": ["worst_ps"],
            "Avg": ["avg_ps"],
            "Passes": ["passes_gf"],
            "Passed": ["passed_gf"],
            "Pass +/-": ["passing_diff"],
            "T15 Passes": ["quality_passes"],
            "T15 Laps": ["top15_laps"],
            "Led": ["lead_laps"],
            "FLaps": ["fast_laps"],
            "Laps": ["laps"],
            "Rating": ["rating"]
        }

        def get_stat(item, keys, default="—"):
            for k in keys:
                if k in item:
                    return item[k]
            return default

        rows = []
        for d in drivers:
            row = {}
            for display_name, keys in col_mapping.items():
                val = get_stat(d, keys)
                
                if display_name == "Driver" and val != "—":
                    try:
                        val = drivers_map.get(int(val), f"Unknown ID ({val})")
                    except ValueError:
                        pass
                
                row[display_name] = val
            rows.append(row)
            
        try:
            rows = sorted(rows, key=lambda x: float(x.get("Finish Pos", 999) if x.get("Finish Pos") != "—" else 999))
        except ValueError:
            pass
        
        if isinstance(data, dict) and "error" in data:
            return build_error_card(f"Could not load loop data: {data['error']}")
            
        return build_table_section("Loop Statistics", make_sortable_table(list(col_mapping.keys()), rows, table_id="loop-stats-table", max_rows=50))

current_year = datetime.now().year

app_ui = ui.page_fluid(
    ui.include_css("styles.css"),
    
    ui.layout_sidebar(
        ui.sidebar(
            ui.tags.h1("NASCAR Dashboard", style="margin-top:0;"),
            ui.input_numeric(
                "refresh_interval",
                "Refresh interval (s)",
                value=DEFAULT_REFRESH_SECONDS,
                min=5,
                max=300,
                step=1,
            ),
            ui.input_dark_mode(id="mode_toggle"),
        ),
        ui.navset_tab(
            ui.nav_panel(
                "Live",
                ui.tags.div(
                    ui.output_ui("session_card"),
                    ui.output_ui("flag_tracker_section"),
                    ui.output_ui("leaderboard_section"),
                    ui.output_ui("points_section"),
                    ui.output_ui("stage_section"),
                    ui.output_ui("metadata_section"),
                    style="padding:1rem;",
                ),
            ),
            ui.nav_panel(
                "Loop Data",
                ui.tags.div(
                    ui.tags.div(
                        ui.input_select(
                            "loop_year", 
                            "Year", 
                            choices={str(y): str(y) for y in range(current_year, 2018, -1)}
                        ),
                        ui.input_select(
                            "loop_series", 
                            "Series", 
                            choices={"1": "Cup", "2": "Xfinity", "3": "Trucks"}
                        ),
                        ui.input_select(
                            "loop_race", 
                            "Race", 
                            choices={"0": "Loading..."}
                        ),
                        style="display:flex; gap:1.5rem; margin-bottom:2rem; align-items:flex-end;"
                    ),
                    ui.output_ui("loop_data_section"),
                    style="padding:1rem;",
                ),
            ),
        ),
    ),
)

app = App(app_ui, server)

if __name__ == "__main__":
    app.run()