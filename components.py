from shiny import ui
from config import FLAG_COLORS

def build_error_card(message: str):
    return ui.tags.div(ui.tags.strong("Error: "), message, class_="error-card")

def format_value(value):
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if type(value).__name__ in ("HTML", "Tag") or hasattr(value, "tagify"):
        return value
    return str(value)

def make_table(columns, rows, max_rows=40):
    if not rows:
        return ui.tags.div("No data available.")
    header_cells = [ui.tags.th(col) for col in columns]
    body_rows = [
        ui.tags.tr(*[ui.tags.td(format_value(row.get(col, "—"))) for col in columns])
        for row in rows[:max_rows]
    ]
    return ui.tags.table(ui.tags.thead(ui.tags.tr(*header_cells)), ui.tags.tbody(*body_rows))

def make_sortable_table(columns, rows, table_id="sortable-table", max_rows=50):
    if not rows:
        return ui.tags.div("No data available.")

    header_cells = [
        ui.tags.th(col, class_="sortable-header", onclick=f"sortTable('{table_id}', {i})", title="Click to sort")
        for i, col in enumerate(columns)
    ]
    
    body_rows = [
        ui.tags.tr(*[ui.tags.td(format_value(row.get(col, "—"))) for col in columns])
        for row in rows[:max_rows]
    ]

    js_script = ui.tags.script(ui.HTML("""
    function sortTable(tableId, n) {
        var table = document.getElementById(tableId);
        var rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
        switching = true; dir = "asc"; 
        var headers = table.rows[0].getElementsByTagName("TH");
        for (var j = 0; j < headers.length; j++) headers[j].innerHTML = headers[j].innerHTML.replace(' ▲', '').replace(' ▼', '');
        while (switching) {
            switching = false; rows = table.rows;
            for (i = 1; i < (rows.length - 1); i++) {
                shouldSwitch = false;
                x = rows[i].getElementsByTagName("TD")[n]; y = rows[i + 1].getElementsByTagName("TD")[n];
                var xVal = x.textContent || x.innerText; var yVal = y.textContent || y.innerText;
                if (n === 0 && x.querySelector('input[type="checkbox"]')) {
                    xVal = x.querySelector('input').checked ? "1" : "0";
                    yVal = y.querySelector('input').checked ? "1" : "0";
                }
                var xNum = parseFloat(xVal); var yNum = parseFloat(yVal);
                var isXNum = !isNaN(xNum) && xVal.trim() !== "—"; var isYNum = !isNaN(yNum) && yVal.trim() !== "—";
                var cmpX = isXNum ? xNum : xVal.toLowerCase(); var cmpY = isYNum ? yNum : yVal.toLowerCase();
                if ((dir == "asc" && cmpX > cmpY) || (dir == "desc" && cmpX < cmpY)) { shouldSwitch = true; break; }
            }
            if (shouldSwitch) { rows[i].parentNode.insertBefore(rows[i + 1], rows[i]); switching = true; switchcount++; } 
            else if (switchcount == 0 && dir == "asc") { dir = "desc"; switching = true; }
        }
        headers[n].innerHTML += (dir == "asc") ? " ▲" : " ▼";
    }
    function updateSelectedDrivers() {
        var checkboxes = document.querySelectorAll('.driver-select:checked');
        var values = Array.from(checkboxes).map(cb => cb.value);
        Shiny.setInputValue('selected_loop_drivers', values);
    }
    """))
    return ui.tags.div(js_script, ui.tags.table(ui.tags.thead(ui.tags.tr(*header_cells)), ui.tags.tbody(*body_rows), id=table_id))

def build_summary_card(title: str, value: str, subtitle: str = "", style: str = ""):
    return ui.tags.div(
        ui.tags.h6(title, class_="summary-title"),
        ui.tags.h3(value, class_="summary-value"),
        ui.tags.h6(subtitle, class_="summary-subtitle"),
        class_="summary-card", style=style,
    )

def build_table_section(title: str, table_ui, caption: str = ""):
    return ui.tags.section(ui.tags.h2(title, class_="section-title"), table_ui)

def create_leaderboard_table(feed):
    vehicles = sorted(feed.get("vehicles", []) or [], key=lambda v: v.get("running_position", 999))
    rows = [{
        "Position": v.get("running_position", "—"),
        "Car": v.get("vehicle_number", "—"),
        "Driver": (v.get("driver") or {}).get("full_name", "—"),
        "Gap": v.get("delta", "—"),
        "Laps": v.get("laps_completed", "—"),
        "Led": sum(lap.get("end_lap", 0) - lap.get("start_lap", 0) for lap in (v.get("laps_led") or [])),
        "Best Lap": v.get("best_lap_time", "—"),
    } for v in vehicles[:40]]
    return make_table(["Position", "Car", "Driver", "Gap", "Laps", "Led", "Best Lap"], rows)

def create_points_table(points):
    if not isinstance(points, list):
        return ui.tags.div("No points standings data available.")
    rows = [{
        "Pos": item.get("points_position", "—"),
        "Car": item.get("car_number", item.get("vehicle_number", "—")),
        "Driver": " ".join([item.get("first_name", ""), item.get("last_name", "")]).strip() or item.get("full_name", "—"),
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
    } for item in points[:40]]
    cols = ["Pos", "Car", "Driver", "Points", "To Leader", "To Next", "Wins", "Top 5", "Top 10", "Poles", "Last Race Pts", "Stage 1 Pts", "Stage 2 Pts", "Fastest Lap"]
    return make_table(cols, rows)

def create_stage_points_table(stage_data):
    if not stage_data:
        return ui.tags.div("No stage points data available.")
    stage_data = [stage_data] if isinstance(stage_data, dict) and "results" in stage_data else stage_data
    rows = []
    for stage in stage_data:
        for result in stage.get("results", "—")[:10]:
            rows.append({
                "Stage": stage.get("stage_number"),
                "Pos": result.get("position", "—"),
                "Car": result.get("vehicle_number", "—"),
                "Driver": result.get("full_name", "—"),
                "Points": result.get("stage_points", "—"),
            })
    return make_table(["Stage", "Pos", "Car", "Driver", "Points"], rows) if rows else ui.tags.div("No stage points results found.")

def create_flag_tracker_bar(flag_data, current_lap: int, total_laps: int):
    if not flag_data or not isinstance(flag_data, list):
        return ui.tags.div("No flag event data available.")
    
    flags = []
    for f in flag_data:
        try:
            flags.append({"lap": int(f.get("lap_number", 0)), "state": int(f.get("flag_state", 1)), "desc": f.get("comment", "")})
        except (ValueError, TypeError): continue
    
    flags = sorted(flags, key=lambda x: x["lap"])
    if not flags:
        return ui.tags.div("No race segments to display yet.")

    segments = []
    for i, flag in enumerate(flags):
        start_lap, end_lap = flag["lap"], flags[i + 1]["lap"] if i + 1 < len(flags) else max(flag["lap"], current_lap)
        width_pct = (max(end_lap - start_lap, 0.5) / max(total_laps, current_lap, 1)) * 100
        
        pointer = ui.tags.div(f"{start_lap}", class_="flag-pointer")
        segments.append(ui.tags.div(pointer, title=f"Lap {start_lap}: {flag['desc']}", class_="flag-segment", style=f"width: {width_pct}%; background-color: {FLAG_COLORS.get(flag['state'], 'transparent')};"))

    return ui.tags.div(ui.tags.p("Hover over flag segments to view notes."), ui.tags.div(*segments, class_="flag-container"), class_="flag-wrapper")