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
                *[ui.tags.td(format_value(row.get(col, []))) for col in columns]
            )
        )

    return ui.tags.table(
        ui.tags.thead(ui.tags.tr(*header_cells)),
        ui.tags.tbody(*body_rows),
    )


def build_summary_card(
    title: str,
    value: str,
    subtitle: str = "",
    style: str = "",
):
    card_style = (
        "border-radius:1rem;"
        "padding:1rem; min-width:12rem; flex:1 1 180px;"
    )
    if style:
        card_style = f"{card_style} {style}"
    return ui.tags.div(
        ui.tags.h6(title, class_="summary-title"),
        ui.tags.h3(value, class_="summary-value"),
        ui.tags.h6(subtitle, class_="summary-subtitle"),
        class_="summary-card",
        style=card_style,
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
                "Position": vehicle.get("running_position", []),
                "Car": vehicle.get("vehicle_number", []),
                "Driver": driver.get("full_name", []),
                "Gap": vehicle.get("delta", []),
                "Laps": vehicle.get("laps_completed", []),
                "Led": sum(lap.get("end_lap", 0) - lap.get("start_lap", 0) for lap in (vehicle.get("laps_led") or [])),
                "Best Lap": vehicle.get("best_lap_time", []),
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
                "Pos": item.get("points_position", []),
                "Car": item.get("car_number", item.get("vehicle_number", [])),
                "Driver": full_name or item.get("full_name", []),
                "Points": item.get("points", []),
                "To Leader": item.get("delta_leader", []),
                "To Next": item.get("delta_next", []),
                "Wins": item.get("wins", []),
                "Top 5": item.get("top_5", []),
                "Top 10": item.get("top_10", []),
                "Poles": item.get("poles", []),
                "Last Race Pts": item.get("points_earned_this_race", []),
                "Stage 1 Pts": item.get("stage_1_points", []),
                "Stage 2 Pts": item.get("stage_2_points", []),
                "Stage 3 Pts": item.get("stage_3_points", []),
                "Fastest Lap": item.get("is_fastest_lap_point", []),
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
            "Stage 3 Pts",
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
        for result in stage.get("results", [])[:10]:
            rows.append(
                {
                    "Stage": stage_num,
                    "Pos": result.get("position", []),
                    "Car": result.get("vehicle_number", []),
                    "Driver": result.get("full_name", []),
                    "Points": result.get("stage_points", []),
                }
            )
    if not rows:
        return ui.tags.div("No stage points results found.")
    return make_table(["Stage", "Pos", "Car", "Driver", "Points"], rows)


def create_flag_table(flag_data):
    if not flag_data:
        return ui.tags.div("No flag event data available.")
    if not isinstance(flag_data, list):
        return ui.tags.div("No flag event data available.")

    rows = []
    for item in flag_data[:20]:
        rows.append(
            {
                "Lap": item.get("lap", []),
                "Type": item.get("flag_type", item.get("flag", [])),
                "Info": item.get("description", item.get("details", [])),
                "Time": item.get("timestamp", []),
            }
        )
    return make_table(["Lap", "Type", "Info", "Time"], rows)

def server(input: Inputs, output: Outputs, session: Session):
    @reactive.calc
    def race_list_basic():
        year = input.weekend_year() or datetime.now().year
        return fetch_json(normalize_url(BASE_URL_DEFAULT, f"cacher/{year}/race_list_basic.json"))

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

    @output
    @render.ui
    def session_card():
        data = dashboard_data()
        feed = data["feed"]
        if not isinstance(feed, dict) or "error" in feed:
            return build_error_card(feed.get("error", "Unable to load live feed."))

        run_name = feed.get("run_name", "Unknown")
        track_name = feed.get("track_name", "Unknown")
        series_id = feed.get("series_id")
        run_type = feed.get("run_type")
        flag_state = feed.get("flag_state")
        lap_number = feed.get("lap_number", [])
        laps_in_race = feed.get("laps_in_race", [])
        leader = None
        vehicles = feed.get("vehicles") or []
        if isinstance(vehicles, list):
            leader = next((v for v in vehicles if v.get("running_position") == 1), vehicles[0] if vehicles else None)

        leader_name = []
        leader_car = []
        if isinstance(leader, dict):
            driver = leader.get("driver") or {}
            leader_name = driver.get("full_name", [])
            leader_car = leader.get("vehicle_number", [])

        flag_color = {
#            1: "#cfc",
#            2: "#ffc",
#            3: "#fcc",
#            4: "#fff",
#            5: "#888",
            1: "#0f0",
            2: "#ff0",
            3: "#f00",
            4: "#fff",
            5: "#888",
            6: "#0df",
            7: "#404"
        }.get(flag_state, "#888")

        return ui.tags.div(
            ui.tags.div(
                build_summary_card(
                    "Latest Race",
                    run_name,
                    f"{track_name}",
                ),
                build_summary_card(
                    "Session",
                    RUN_TYPE_LABELS.get(run_type, "Unknown"),
                    f"Series: {SERIES_LABELS.get(series_id, f'Series {series_id}')}",
                    style=f"background:{flag_color}; border:1px solid {flag_color};",
                ),
                build_summary_card(
                    "Leader",
                    f"#{leader_car} {leader_name}",
                    f"Lap {lap_number} / {laps_in_race}",
                ),
                style="display:flex; gap:1rem; flex-wrap:wrap; margin-bottom:1rem;",
            ),
        )

    @output
    @render.ui
    def leaderboard_section():
        data = dashboard_data()
        feed = data["feed"]
        if not isinstance(feed, dict) or "error" in feed:
            return build_error_card(feed.get("error", "Unable to load leaderboard."))

        return build_table_section("Live Leaderboard", create_leaderboard_table(feed))

    @output
    @render.ui
    def points_section():
        data = dashboard_data()
        points = data["points_data"]
        if not isinstance(points, list) and isinstance(points, dict) and "error" in points:
            return build_error_card(points.get("error", "Unable to load points data."))

        if isinstance(points, dict) and "error" in points:
            return build_error_card(points["error"])

        return build_table_section("Live Standings", create_points_table(points))

    @output
    @render.ui
    def stage_section():
        data = dashboard_data()
        stage = data["stage_data"]
        if isinstance(stage, dict) and "error" in stage:
            return build_error_card(stage["error"])
        return build_table_section("Live Stage Points", create_stage_points_table(stage))

    @output
    @render.ui
    def metadata_section():
        data = dashboard_data()
        refreshed = data["updated_at"].strftime("%Y-%m-%d %H:%M:%S")
        return ui.tags.div(
            ui.tags.h2("Status", style="margin-top:0;"),
            ui.tags.div(
                ui.tags.p(f"Refresh interval: {input.refresh_interval() or DEFAULT_REFRESH_SECONDS} seconds"),
                ui.tags.p(f"Last update: {refreshed}"),
            ),
        )


app_ui = ui.page_fluid(
    ui.include_css("styles.css"),
    
    ui.layout_sidebar(
        ui.sidebar(
            ui.tags.h1("NASCAR Dashboard!", style="margin-top:0;"),
            ui.input_numeric(
                "refresh_interval",
                "Refresh interval",
                value=DEFAULT_REFRESH_SECONDS,
                min=1,
                max=30,
                step=1,
            ),
            ui.input_dark_mode(id="mode_toggle"),
        ),
        ui.navset_tab(
            ui.nav_panel(
                "Live",
                ui.tags.div(
                    ui.output_ui("session_card"),
                    ui.output_ui("leaderboard_section"),
                    ui.output_ui("points_section"),
                    ui.output_ui("stage_section"),
                    ui.output_ui("metadata_section"),
                    style="padding:1rem;",
                ),
            ),
            ui.nav_panel(
                "Coming Soon!",
                ui.tags.div(
                    ui.output_ui("weekend_feed_section"),
                ),
            ),
        ),
    ),
)

app = App(app_ui, server)

if __name__ == "__main__":
    app.run()