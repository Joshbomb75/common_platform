import serial, time

s = serial.Serial("/dev/ttyACM1", 115200, timeout=2)

# Aggressive flush
time.sleep(3)
s.reset_input_buffer()
time.sleep(1)
s.reset_input_buffer()
time.sleep(0.5)
s.reset_input_buffer()

# Double-tap J to ensure we end up ENABLED (toggle to known-off, then on)
print("Resetting encoder stream to known state...")
s.write(b"J\n")
time.sleep(0.5)
s.reset_input_buffer()  # discard the "disabled" response
s.write(b"J\n")
time.sleep(0.5)

print("Encoder stream enabled. Spin wheels by hand (10 seconds):")
end = time.time() + 10
while time.time() < end:
    data = s.read(s.in_waiting)
    if data:
        print(data.decode(errors="replace"), end="", flush=True)
    time.sleep(0.05)

# Disable stream cleanly
s.write(b"J\n")
time.sleep(0.3)
print("\nEncoder stream off.")
s.close()
