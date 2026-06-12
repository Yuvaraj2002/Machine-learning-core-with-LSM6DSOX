import socket
import csv
import os
from datetime import datetime
import time

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
UDP_IP       = "0.0.0.0"          # listen on all interfaces
UDP_PORT     = 5005
DATA_DIR     = "imu_data"
DURATION_S   = 180                # recording duration in seconds
COUNTDOWN_S  = 5                  # countdown before recording starts
# ─────────────────────────────────────────────

os.makedirs(DATA_DIR, exist_ok=True)

# Filename uses only a timestamp — rename it to the activity name later
filename  = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
filepath  = os.path.join(DATA_DIR, filename)

# ── Countdown ────────────────────────────────
print(f"\nRecording will start in {COUNTDOWN_S} seconds ...")
for i in range(COUNTDOWN_S, 0, -1):
    print(f"  {i}")
    time.sleep(1)

# ── Open UDP socket ──────────────────────────
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.settimeout(2.0)   # so the loop can check elapsed time even if no packet arrives

print(f"\nRecording START  ({DURATION_S}s)")
print(f"Saving to: {filepath}")
print("Press Ctrl+C to stop early.\n")

# ── Unico-ready CSV header (exact STM column names) ──────────────────
# HEADER = ["ACC_X [mg]", "ACC_Y [mg]", "ACC_Z [mg]",
#           "GY_X [mdps]", "GY_Y [mdps]", "GY_Z [mdps]"]
HEADER = ["ACC_X [g]", "ACC_Y [g]", "ACC_Z [g]",
          "GY_X [dps]", "GY_Y [dps]", "GY_Z [dps]"]

sample_count = 0
start_time   = time.time()

with open(filepath, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(HEADER)

    try:
        while (time.time() - start_time) < DURATION_S:

            try:
                data, addr = sock.recvfrom(1024)
            except socket.timeout:
                continue   # no packet yet — loop back and re-check timer

            decoded = data.decode("utf-8", errors="ignore").strip()
            if not decoded:
                continue

            # ── Parse the incoming row from Nicla Vision ─────────────
            # Expected format from board:  "ax_g, ay_g, az_g, gx_dps, gy_dps, gz_dps"
            # (raw floats in g and dps, as sent by lsm.accel() / lsm.gyro())
            parts = decoded.split(",")
            if len(parts) < 6:
                continue   # malformed packet — skip

            try:
                ax_g,  ay_g,  az_g  = float(parts[0]), float(parts[1]), float(parts[2])
                gx_dps, gy_dps, gz_dps = float(parts[3]), float(parts[4]), float(parts[5])
            except ValueError:
                # First packet is often the header line from the board — skip it
                continue

            # ── Convert to Unico units ────────────────────────────────
            # Accelerometer: g  →  mg   (multiply × 1000, round to int)
            # Gyroscope:     dps → mdps (multiply × 1000, round to int)
            # row = [
            #     int(round(ax_g   * 1000)),
            #     int(round(ay_g   * 1000)),
            #     int(round(az_g   * 1000)),
            #     int(round(gx_dps * 1000)),
            #     int(round(gy_dps * 1000)),
            #     int(round(gz_dps * 1000)),
            # ]
            row = [
                ax_g, ay_g, az_g,
                gx_dps, gy_dps, gz_dps,
            ]

            writer.writerow(row)
            f.flush()          # write to disk immediately — never lose data
            sample_count += 1
            print(",".join(map(str, row)))

    except KeyboardInterrupt:
        print("\nStopped early by user.")

sock.close()

elapsed = time.time() - start_time
print(f"\n── Recording complete ────────────────────────")
print(f"   Samples collected : {sample_count}")
print(f"   Duration          : {elapsed:.1f} s")
print(f"   Approx. sample rate: {sample_count / elapsed:.1f} Hz")
print(f"   File saved to     : {filepath}")
print(f"\nRename the file to your activity label when ready.")
print(f"  e.g.  mv {filepath}  imu_data/walking_01.csv")