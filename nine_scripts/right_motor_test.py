import serial, time

s = serial.Serial("/dev/ttyACM1", 115200, timeout=2)
time.sleep(2)
s.reset_input_buffer()
time.sleep(0.5)
s.reset_input_buffer()

print("Enabling encoder stream...")
s.write(b"J\n")
time.sleep(0.3)

print("Running RIGHT motor only at 0.3 m/s for 4 seconds...")
s.write(b"Z0.3\n")

end = time.time() + 4
while time.time() < end:
    data = s.read(s.in_waiting)
    if data:
        print(data.decode(errors="replace"), end="", flush=True)
    time.sleep(0.05)

print("\nStopping...")
s.write(b"Z0.0\n")
time.sleep(0.5)
s.write(b"J\n")
print("Done.")
s.close()
