## API ENDPOINTS SUMMARY

# fix full ui blinking if possible?
# security: cache static data + build rate-limiter for live data; xss (scan json payloads)

### Live Data (Real-time)
| Endpoint | URL |
|----------|-----|

## dashboard tab: main feed--shiny select categories or toggle for live loop data
| Live Feed | `https://cf.nascar.com/live/feeds/live-feed.json` |
| Live Points | `https://cf.nascar.com/live/feeds/live-points.json` |
| Live Stage Points | `https://cf.nascar.com/live/feeds/live-stage-points.json` |
### fox style flag tracker; integrate lap count text
| Live Flag Data | `https://cf.nascar.com/live/feeds/live-flag-data.json` |
### consider:
| Live Qualifying | `https://cf.nascar.com/live/feeds/live-qualifying-data.json` |
| Live Pit Data | `https://cf.nascar.com/live/feeds/live-pit-data.json` |

#### Static/Cached Data
| Endpoint | URL Pattern |
|----------|-------------|

## dashboard tab: search fullname + race or by track; lap time + position line graphs; merge with lap-notes to identify caution periods as yellow sections in said line graph; notes on hover?; provide tabular driver loop stats below graph
## historical loop data
### search could be a fat task
| Lap Times | `https://cf.nascar.com/cacher/{year}/{series}/{race_id}/lap-times.json` |
| Lap Notes | `https://cf.nascar.com/cacher/{year}/{series}/{race_id}/lap-notes.json` |
| Loop Stats | `https://cf.nascar.com/loopstats/prod/{year}/{series}/{race_id}.json` |

## merge with above? search by race for complete historical data
| Weekend Feed | `https://cf.nascar.com/cacher/{year}/{series}/{race_id}/weekend-feed.json` |



## reference when building
| Race List | `https://cf.nascar.com/cacher/{year}/race_list_basic.json` |
| Drivers | `https://cf.nascar.com/cacher/drivers.json` |
| Tracks | `https://cf.nascar.com/cacher/tracks.json` |