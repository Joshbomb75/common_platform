# nine_scripts — rcr002 Custom Scripts

Custom Python/shell scripts for operating and calibrating the rcr002 robot.
These live on the Pi at `~/nine_scripts/` and are the primary interface for robot control.

## Scripts

| Script | Purpose |
|---|---|
| `nine_move.py` | ROS2 cmd_vel publisher for movement commands |
| `nine_cal.py` | Calibration: straight-line, rotation, encoder-based distance |
| `nine_api.py` | Flask HTTP API for remote control (port 5000) |
| `nine_api_start.sh` | Start the Flask API service |
| `nine_status.py` | Robot status check (topics, services, TF) |
| `nine_snap.py` | Camera snapshot capture |
| `nine_camera.sh` | Camera stream startup |
| `nine_drive.sh` | Keyboard teleop wrapper |
| `encoder_stream.py` | Stream encoder tick counts from Teensy (uses `J` serial command) |
| `rev_test.py` | Motor revolution test for balance calibration |
| `right_motor_test.py` | Isolated right motor test |
| `fastdds-discovery-start.sh` | Start FastDDS discovery server |
| `microros-agent-start.sh` | Start micro-ROS agent (Teensy bridge) |

## Known Issues

- `nine_move.py` has a DDS spin bug: checks subscriber count without calling `spin_once()` → fails silently. Fix pending.
- All calibration measurements must use encoder ticks (via `encoder_stream.py`), not visual counting.
