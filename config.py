BASE_URL_DEFAULT = "https://cf.nascar.com"
DEFAULT_REFRESH_SECONDS = 60.0

HEADERS = {
    "User-Agent": "NASCARShinyDashboard/1.0",
    "Accept": "application/json",
}

FLAG_STATE_LABELS = {
    0: "None", 1: "Green", 2: "Yellow", 3: "Red", 4: "White",
    5: "Checkered", 6: "Who Knows 1", 7: "Who Knows 2",
    8: "Hot Track", 9: "Cold Track",
}

FLAG_COLORS = {
    1: "var(--flag-green)", 2: "var(--flag-yellow)", 3: "var(--flag-red)",
    4: "var(--flag-white)", 5: "var(--flag-checkered)", 6: "var(--flag-checkered)",
    7: "var(--flag-checkered)", 8: "var(--flag-checkered)", 9: "var(--flag-checkered)",
}

RUN_TYPE_LABELS = {1: "Practice", 2: "Qualifying", 3: "Race"}

SERIES_LABELS = {1: "Cup", 2: "O'Reilly", 3: "Trucks", 4: "ARCA Menards"}