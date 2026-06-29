# NASCAR Dashboard

[Link to deploy coming Q3 2026]

A real-time data visualization dashboard for NASCAR. This project consumes various NASCAR JSON endpoints to provide real-time race updates, advanced lap-by-lap analytics, and potentially a historical database.

*Thanks to ooohfascinating for API documentation*

---

## Roadmap

### Main Feed:
Initial live feed containing a full race leaderboard and live standings, already running nicely. Will expand with an option to show live loop data and potentially live qualifying results and pit data. Stage points currently revert to 2022 Pocono (huh??).
- **Live Feed**: Driven by `https://cf.nascar.com/live/feeds/live-feed.json`.
- **Live Points**: Driven by `https://cf.nascar.com/live/feeds/live-points.json`.

### Historical Loop Data
A second dashboard tab to incorporate graphical and text analyses of all drivers' loop data per race, searchable by user.

### Historical Data?
Considering the addition of complete, searchable historical race and loop data, depending on the scope of endpoint data. May integrate into loop data.

---