# maps — SLAM Maps (rcr002)

SLAM maps generated from the rcr002 robot using SLAM Toolbox.
These are stored on the Pi at `~/repos/common_platform/` and backed up here.

## Map Files

| Map | Notes |
|---|---|
| `my_map` | Base map |
| `my_map_1501PM`, `my_map_1504PM`, `my_map_1511PM` | Timestamped variants from Nov 15 mapping session |
| `my_square_corner_map` through `my_square_corner_map4` | Corner/square room mapping runs |

Each map consists of a `.pgm` (grayscale occupancy grid) and `.yaml` (metadata: resolution, origin, thresholds).
