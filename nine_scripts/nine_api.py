#!/usr/bin/env python3
import os
import shlex
import subprocess
from flask import Flask, jsonify, request, send_file

app = Flask(__name__)

API_KEY = "nine-robot-key"
VALID_DIRECTIONS = {"forward", "backward", "left", "right", "stop"}
DRIVE_SCRIPT = os.path.expanduser("~/nine_scripts/nine_drive.sh")
CAMERA_SCRIPT = os.path.expanduser("~/nine_scripts/nine_camera.sh")
SNAP_PATH = "/tmp/nine_snap.jpg"
SERVICES = ["fastdds-discovery.service", "microros-agent.service"]


def run_with_profile(command: str):
    return subprocess.run(
        ["bash", "-c", f"source ~/.profile && {command}"],
        capture_output=True,
        text=True,
    )


def check_service_active(service: str):
    first = subprocess.run(
        ["systemctl", "is-active", service],
        capture_output=True,
        text=True,
    )
    if first.returncode == 0:
        return first.stdout.strip() or "active"

    sudo_cmd = f"echo siliconforest | sudo -S systemctl is-active {shlex.quote(service)}"
    second = subprocess.run(
        ["bash", "-c", sudo_cmd],
        capture_output=True,
        text=True,
    )
    if second.returncode == 0:
        return second.stdout.strip() or "active"

    status = (first.stdout or first.stderr or second.stdout or second.stderr).strip()
    return status if status else "unknown"


@app.before_request
def require_api_key_for_post():
    if request.method == "POST":
        provided = request.headers.get("X-API-Key", "")
        if provided != API_KEY:
            return jsonify({"ok": False, "error": "unauthorized"}), 401


@app.get("/status")
def status():
    return jsonify({"status": "ok", "robot": "rcr002"}), 200


@app.post("/move")
def move():
    data = request.get_json(silent=True) or {}
    direction = data.get("direction")

    if direction not in VALID_DIRECTIONS:
        return jsonify({
            "ok": False,
            "error": "invalid direction",
            "allowed": sorted(list(VALID_DIRECTIONS))
        }), 400

    cmd = f"bash {shlex.quote(DRIVE_SCRIPT)} {shlex.quote(direction)}"
    result = run_with_profile(cmd)

    if result.returncode != 0:
        return jsonify({
            "ok": False,
            "error": "drive command failed",
            "direction": direction,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "code": result.returncode,
        }), 500

    return jsonify({"ok": True, "direction": direction}), 200


@app.post("/snap")
def snap():
    cmd = f"bash {shlex.quote(CAMERA_SCRIPT)}"
    result = run_with_profile(cmd)

    if result.returncode != 0:
        return jsonify({
            "ok": False,
            "error": "camera command failed",
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "code": result.returncode,
        }), 500

    if not os.path.exists(SNAP_PATH):
        return jsonify({
            "ok": False,
            "error": "snapshot not found",
            "path": SNAP_PATH,
            "script_output": result.stdout.strip(),
        }), 500

    return send_file(SNAP_PATH, mimetype="image/jpeg")


@app.get("/health")
def health():
    service_states = {svc: check_service_active(svc) for svc in SERVICES}
    overall_ok = all(state == "active" for state in service_states.values())
    return jsonify({
        "status": "ok" if overall_ok else "degraded",
        "services": service_states,
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
