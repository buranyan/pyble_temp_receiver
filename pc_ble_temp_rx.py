import asyncio
from bleak import BleakClient, BleakScanner
import struct
import time

ENV_SENSE_UUID = "181A"
TEMP_CHAR_UUID = "2A6E"
INACTIVITY_TIMEOUT = 30

def temperature_notify_handler(sender: int, data: bytearray, last_notify_time):
    try:
        temp_celsius = struct.unpack("<h", data)[0] / 100.0
        print(f"Received Temperature: {temp_celsius:.2f} °C")
        last_notify_time[0] = time.time()
    except Exception as e:
        print(f"Error in notify handler: {e}")

async def run():
    try:
        devices = await BleakScanner.discover(timeout=5)
        print("Found devices:")
        for device in devices:
            print(f"{device.name} ({device.address})")

        # target_device = next((d for d in devices if d.name and d.name.startswith("MPY BTSTACK")), None) #picow to macbookair
        # target_device = next((d for d in devices if d.name and d.name.startswith("ESP_SPEAKER")), None) #ESP32 to macbookair
        target_device = next((d for d in devices if d.name and d.name.startswith("Pico")), None) #Picow to mac mini
        # target_device = next((d for d in devices if d.name and d.name.startswith("MPY ESP32")), None) #ESP32 to mac mini

        if not target_device:
            print("Target device not found.")
            return

        print(f"Connecting to {target_device.name} ({target_device.address})...")

        async with BleakClient(target_device.address) as client:
            print(f"Connected to {target_device.name}")

            try:
                services = client.services
                print(f"Discovered services: {[service.uuid for service in services]}")

                last_notify_time = [time.time()]

                await client.start_notify(
                    TEMP_CHAR_UUID,
                    lambda sender, data: temperature_notify_handler(sender, data, last_notify_time)
                )

                while True:
                    time_since_last_notify = time.time() - last_notify_time[0]
                    if time_since_last_notify >= INACTIVITY_TIMEOUT:
                        print(f"No notification for {INACTIVITY_TIMEOUT} seconds. Disconnecting...")
                        await client.stop_notify(TEMP_CHAR_UUID)
                        break
                    await asyncio.sleep(1)
            except Exception as e:
                print(f"Error during BLE operations: {e}")
    except Exception as e:
        print(f"Error in run function: {e}")

# メインの処理でイベントループが閉じられる場合のエラーハンドリング
try:
    asyncio.run(run())
except KeyboardInterrupt:
    print("Program interrupted by user.")
except RuntimeError as e:
    if 'Event loop is closed' in str(e):
        print("Event loop is closed. The program has terminated.")
    else:
        print(f"Unhandled RuntimeError: {e}")
except Exception as e:
    print(f"Unhandled exception: {e}")
