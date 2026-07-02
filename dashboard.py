from datetime import datetime
from shinywidgets import output_widget, render_plotly
import plotly.graph_objects as go
from shiny import App, Inputs, Outputs, Session, reactive, render, ui

from config import BASE_URL_DEFAULT, DEFAULT_REFRESH_SECONDS, RUN_TYPE_LABELS, SERIES_LABELS, FLAG_COLORS
from utils import fetch_json, normalize_url
import components as cmp

current_year = datetime.now().year

app_ui = ui.page_fluid(
    ui.include_css("styles.css"),
    ui.layout_sidebar(
        ui.sidebar(
            ui.tags.h1("NASCAR Dashboard"),
            ui.input_numeric("refresh_interval", "Refresh interval (s)", value=DEFAULT_REFRESH_SECONDS, min=5, max=300, step=1),
            ui.input_dark_mode(id="mode_toggle"),
        ),
        ui.navset_tab(
            ui.nav_panel("Live", ui.tags.div(
                ui.output_ui("session_card"), ui.output_ui("flag_tracker_section"),
                ui.output_ui("leaderboard_section"), ui.output_ui("points_section"),
                ui.output_ui("stage_section"), ui.output_ui("metadata_section"), class_="nav-panel-content"
            )),
            ui.nav_panel("Loop Data", ui.tags.div(
                ui.tags.div(
                    ui.input_select("loop_year", "Year", choices={str(y): str(y) for y in range(current_year, 2018, -1)}),
                    ui.input_select("loop_series", "Series", choices={"1": "Cup", "2": "Xfinity", "3": "Trucks"}),
                    ui.input_select("loop_race", "Race", choices={"0": "Loading..."}),
                    class_="loop-inputs-container",
                ),
                ui.output_ui("loop_data_section"),
                output_widget("loop_position_plot"), output_widget("loop_laptime_plot"), class_="nav-panel-content"
            )),
        ),
    ),
)

def server(input: Inputs, output: Outputs, session: Session):

    @reactive.calc
    def dashboard_data():
        refresh_seconds = input.refresh_interval() or DEFAULT_REFRESH_SECONDS
        reactive.invalidate_later(max(float(refresh_seconds), 1.0))

        return {
            "feed": fetch_json(normalize_url(BASE_URL_DEFAULT, "live/feeds/live-feed.json")),
            "flag_data": fetch_json(normalize_url(BASE_URL_DEFAULT, "live/feeds/live-flag-data.json")),
            "points_data": fetch_json(normalize_url(BASE_URL_DEFAULT, "live/feeds/live-points.json")),
            "stage_data": fetch_json(normalize_url(BASE_URL_DEFAULT, "live/feeds/live-stage-points.json")),
            "updated_at": datetime.now(),
        }

    @reactive.calc
    @reactive.event(input.loop_year)
    def loop_year_resources():
        year = input.loop_year()
        if not year:
            return {}, {}
        
        race_data = fetch_json(normalize_url(BASE_URL_DEFAULT, f"cacher/{year}/race_list_basic.json"))
        drivers_data = fetch_json(normalize_url(BASE_URL_DEFAULT, "cacher/drivers.json"))
        
        driver_list = drivers_data.get("response", []) if isinstance(drivers_data, dict) and "error" not in drivers_data else (drivers_data if isinstance(drivers_data, list) else [])
        drivers_map = {int(d["Nascar_Driver_ID"]): d.get("Full_Name", "Unknown") for d in driver_list if d.get("Nascar_Driver_ID") is not None and str(d["Nascar_Driver_ID"]).isdigit()}
        return race_data, drivers_map

    @reactive.calc
    def loop_lap_data():
        race_id = input.loop_race()
        if not race_id or race_id == "0":
            return None
        url = normalize_url(BASE_URL_DEFAULT, f"cacher/{input.loop_year()}/{input.loop_series()}/{race_id}/lap-times.json")
        return fetch_json(url)

    @output
    @render.ui
    def session_card():
        feed = dashboard_data()["feed"]
        if not isinstance(feed, dict) or "error" in feed:
            return cmp.build_error_card(feed.get("error", "Unable to load live feed."))

        leader = next((v for v in feed.get("vehicles", []) if v.get("running_position") == 1), None)
        leader_name, leader_car = ((leader.get("driver") or {}).get("full_name", "—"), leader.get("vehicle_number", "—")) if leader else ("—", "—")
        flag_color = FLAG_COLORS.get(feed.get("flag_state"), "var(--flag-checkered)")

        return ui.tags.div(ui.tags.div(
            cmp.build_summary_card("Latest Race", feed.get("run_name", "Unknown"), f"{feed.get('track_name', 'Unknown')}"),
            cmp.build_summary_card("Session", RUN_TYPE_LABELS.get(feed.get("run_type"), "Unknown"), f"Series: {SERIES_LABELS.get(feed.get('series_id'), 'Unknown')}", style=f"background:{flag_color}; border:1px solid {flag_color};"),
            cmp.build_summary_card("Leader", f"#{leader_car} {leader_name}", f"Lap {feed.get('lap_number', '—')} / {feed.get('laps_in_race', '—')}"),
            class_="session-cards-container",
        ))

    @output
    @render.ui
    def flag_tracker_section():
        data = dashboard_data()
        if isinstance(data["flag_data"], dict) and "error" in data["flag_data"]:
            return cmp.build_error_card(data["flag_data"]["error"])
        
        feed = data["feed"] if isinstance(data["feed"], dict) else {}
        total_laps = max(int(feed.get("laps_in_race", 100)), 1)
        current_lap = int(feed.get("lap_number", 0)) if str(feed.get("lap_number")).isdigit() else 0
            
        return cmp.build_table_section("Live Flag Tracker", cmp.create_flag_tracker_bar(data["flag_data"], current_lap, total_laps))
    
    @output
    @render.ui
    def leaderboard_section():
        feed = dashboard_data()["feed"]
        return cmp.build_error_card(feed.get("error")) if not isinstance(feed, dict) or "error" in feed else cmp.build_table_section("Live Leaderboard", cmp.create_leaderboard_table(feed))

    @output
    @render.ui
    def points_section():
        points = dashboard_data()["points_data"]
        return cmp.build_error_card(points.get("error")) if isinstance(points, dict) and "error" in points else cmp.build_table_section("Live Standings", cmp.create_points_table(points))

    @output
    @render.ui
    def stage_section():
        stage = dashboard_data()["stage_data"]
        return cmp.build_error_card(stage["error"]) if isinstance(stage, dict) and "error" in stage else cmp.build_table_section("Live Stage Points", cmp.create_stage_points_table(stage))

    @output
    @render.ui
    def metadata_section():
        return ui.tags.div(ui.tags.p(f"Last updated {dashboard_data()['updated_at'].strftime('%Y-%m-%d %H:%M:%S')}"))
    
    @reactive.Effect
    def update_loop_races():
        race_data, _ = loop_year_resources()
        choices = {str(r.get("race_id")): r.get("race_name", f"Race {r.get('race_id')}") for r in race_data.get(f"series_{input.loop_series()}", [])} if isinstance(race_data, dict) else {}
        ui.update_select("loop_race", choices=choices or {"0": "No races available for this selection"})

    @output
    @render.ui
    def loop_data_section():
        race_id = input.loop_race()
        if not race_id or race_id == "0": 
            return ui.tags.div(ui.tags.p("Please select a valid race to view loop stats."))

        race_data, drivers_map = loop_year_resources()
        if isinstance(race_data, dict):
            valid_races = [str(r.get("race_id")) for r in race_data.get(f"series_{input.loop_series()}", [])]
            if race_id not in valid_races:
                return ui.tags.div(ui.tags.p("Loading race data...", class_="text-muted"))
                
        data = fetch_json(normalize_url(BASE_URL_DEFAULT, f"loopstats/prod/{input.loop_year()}/{input.loop_series()}/{race_id}.json"))
        
        if isinstance(data, dict) and "error" in data: 
            return cmp.build_error_card(f"Could not load loop data: {data['error']}")

        drivers = data[0].get("drivers", []) if isinstance(data, list) and data else data.get("drivers", [])
        if not drivers: 
            return ui.tags.div(ui.tags.p("No loop data drivers found for this event."))

        col_mapping = {"Driver": "driver_id", "Finish": "ps", "Closing Pos": "closing_ps", "Mid Pos": "mid_ps", "Start": "start_ps", "Best": "best_ps", "Worst": "worst_ps", "Avg": "avg_ps", "Passes": "passes_gf", "Passed": "passed_gf", "+/-": "passing_diff", "T15 Passes": "quality_passes", "T15 Laps": "top15_laps", "Led": "lead_laps", "FLaps": "fast_laps", "Laps": "laps", "Rating": "rating"}

        rows = []
        for d in drivers:
            row = {"Graph": ui.HTML(f'<input type="checkbox" class="driver-select" value="{d.get("driver_id")}" onchange="updateSelectedDrivers()">')}
            for name, key in col_mapping.items():
                val = d.get(key, "—")
                row[name] = drivers_map.get(int(val), f"Unknown ID ({val})") if name == "Driver" and val != "—" and str(val).isdigit() else val
            rows.append(row)
            
        rows.sort(key=lambda x: float(x.get("Finish", 999)) if str(x.get("Finish")).isdigit() else 999)
        return cmp.build_table_section("Loop Statistics", cmp.make_sortable_table(["Graph"] + list(col_mapping.keys()), rows, table_id="loop-stats-table"))

    def get_base_layout(is_dark):
        return dict(template="plotly_dark" if is_dark else "plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=40, r=40, t=40, b=40))

    @output
    @render_plotly
    def loop_position_plot():
        selected = input.selected_loop_drivers()
        is_dark = input.mode_toggle() == "dark"
        fig, base_layout = go.Figure(), get_base_layout(is_dark)

        if not selected:
            fig.add_annotation(text="Select drivers to view their running positions.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=14, color="white" if is_dark else "black"))
            return fig.update_layout(**base_layout, xaxis=dict(visible=False), yaxis=dict(visible=False))

        data = loop_lap_data()
        if not data or "error" in data:
            return None

        _, drivers_map = loop_year_resources()
        plot_data = {did: {"laps": [], "positions": [], "name": drivers_map.get(int(did), did)} for did in selected}

        for d_entry in data.get("laps", []):
            v_id = str(d_entry.get("NASCARDriverID", ""))
            if v_id in plot_data:
                for lap in d_entry.get("Laps", []):
                    if lap.get("Lap") is not None and lap.get("RunningPos") is not None:
                        plot_data[v_id]["laps"].append(int(lap["Lap"]))
                        plot_data[v_id]["positions"].append(int(lap["RunningPos"]))

        for _, d_data in plot_data.items():
            if d_data["laps"]:
                laps, poses = zip(*sorted(zip(d_data["laps"], d_data["positions"])))
                fig.add_trace(go.Scatter(x=laps, y=poses, mode='lines', name=d_data["name"], hovertemplate="P%{y}<extra></extra>"))

        if not fig.data:
            fig.add_annotation(text="No running position data found.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig.update_layout(**base_layout, xaxis=dict(visible=False), yaxis=dict(visible=False))

        fig.update_layout(**base_layout, xaxis_title="Lap Number", yaxis_title="Running Position", hovermode="x unified", hoverlabel=dict(bgcolor="black" if is_dark else "white", font_size=13), legend=dict(yanchor="top", y=1, xanchor="left", x=1.02, bgcolor="rgba(0,0,0,0)"))
        return fig.update_yaxes(autorange="reversed", tickformat="d")

    @output
    @render_plotly
    def loop_laptime_plot():
        selected = input.selected_loop_drivers()
        is_dark = input.mode_toggle() == "dark"
        fig, base_layout = go.Figure(), get_base_layout(is_dark)

        if not selected:
            fig.add_annotation(text="Select drivers to view their lap times.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=14, color="white" if is_dark else "black"))
            return fig.update_layout(**base_layout, xaxis=dict(visible=False), yaxis=dict(visible=False))

        data = loop_lap_data()
        if not data or "error" in data:
            return None

        _, drivers_map = loop_year_resources()
        plot_data = {did: {"laps": [], "times": [], "name": drivers_map.get(int(did), did)} for did in selected}
        all_times = []

        for d_entry in data.get("laps", []):
            v_id = str(d_entry.get("NASCARDriverID", ""))
            if v_id in plot_data:
                for lap in d_entry.get("Laps", []):
                    if lap.get("Lap") is not None and lap.get("LapTime") is not None:
                        try:
                            t = float(lap["LapTime"])
                            plot_data[v_id]["laps"].append(int(lap["Lap"]))
                            plot_data[v_id]["times"].append(t)
                            all_times.append(t)
                        except ValueError:
                            pass

        for _, d_data in plot_data.items():
            if d_data["laps"]:
                laps, times = zip(*sorted(zip(d_data["laps"], d_data["times"])))
                fig.add_trace(go.Scatter(x=laps, y=times, mode='lines', name=d_data["name"], hovertemplate="%{y:.3f}s<extra></extra>"))

        if not fig.data:
            fig.add_annotation(text="No lap time data found.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig.update_layout(**base_layout, xaxis=dict(visible=False), yaxis=dict(visible=False))

        fig.update_layout(**base_layout, xaxis_title="Lap Number", yaxis_title="Lap Time (Seconds)", hovermode="x unified", hoverlabel=dict(bgcolor="#222" if is_dark else "#fff", font_size=13), legend=dict(yanchor="top", y=1, xanchor="left", x=1.02, bgcolor="rgba(0,0,0,0)"))
        if all_times:
            fig.update_yaxes(range=[min(all_times) * 0.98, min(all_times) * 1.25])
            
        return fig

app = App(app_ui, server)

if __name__ == "__main__":
    app.run()