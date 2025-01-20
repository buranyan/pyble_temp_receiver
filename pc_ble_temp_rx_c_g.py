import asyncio
from bleak import BleakClient, BleakScanner
import struct
import time
import csv
import os
import matplotlib.pyplot as plt  # グラフ描画用ライブラリをインポート

ENV_SENSE_UUID = "181A"
TEMP_CHAR_UUID = "2A6E"
INACTIVITY_TIMEOUT = 30
CSV_FILE_PATH = "temperature_data.csv"
PLOT_FILE_PATH = "temperature_plot.png"  # グラフを保存するファイル名

# グローバル変数としてtemperature_dataを定義
temperature_data = []

# CSVファイルにデータを書き込む関数
def write_to_csv(timestamp, temperature):
    # ファイルが存在しない場合はヘッダーを書き込む
    file_exists = os.path.exists(CSV_FILE_PATH)
    with open(CSV_FILE_PATH, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Timestamp", "Temperature (°C)"])  # ヘッダー
        writer.writerow([time.ctime(timestamp), temperature])

# 温度通知を処理するハンドラー
def temperature_notify_handler(sender: int, data: bytearray, last_notify_time):
    try:
        # 温度データの解釈
        temp_celsius = struct.unpack("<h", data)[0] / 100.0
        timestamp = time.time()  # タイムスタンプを取得
        print(f"Received Temperature: {temp_celsius:.2f} °C at {time.ctime(timestamp)}")
        
        # 温度データとタイムスタンプを保存
        temperature_data.append((timestamp, temp_celsius))
        
        # 最後に通知を受けた時刻を更新
        last_notify_time[0] = timestamp
    except Exception as e:
        print(f"Error in notify handler: {e}")

# プログラムの終了時に温度データをCSVファイルに保存し、グラフを表示する
def save_on_exit():
    print("\nProgram interrupted. Saving data to CSV...")
    # CSVファイルにデータを書き込み
    for timestamp, temp_celsius in temperature_data:
        write_to_csv(timestamp, temp_celsius)
    
    # 時刻の差（相対時間）を計算してグラフを表示
    if temperature_data:
        # 最初のタイムスタンプを基準に相対時間を計算
        base_time = temperature_data[0][0]
        relative_times = [ts - base_time for ts, _ in temperature_data]
        temperatures = [temp for _, temp in temperature_data]
        
        # グラフを描画
        plt.figure(figsize=(10, 6))
        plt.plot(relative_times, temperatures, label='Temperature (°C)', color='blue', marker='o')
        plt.title('Temperature vs Time')
        plt.xlabel('Time (relative to first timestamp)')
        plt.ylabel('Temperature (°C)')
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        
        # 最初のタイムスタンプを注釈としてグラフに表示
        first_timestamp = time.ctime(temperature_data[0][0])  # 最初のタイムスタンプ
        plt.annotate(f"Start Time: {first_timestamp}",
                     xy=(0.05, 0.95), xycoords='axes fraction',
                     fontsize=12, color='red', ha='left', va='top',
                     bbox=dict(facecolor='white', edgecolor='red', boxstyle='round,pad=0.3'))
        
        # グラフを表示
        plt.show()

        # グラフを画像として保存
        plt.savefig(PLOT_FILE_PATH)
        print(f"Graph saved to {PLOT_FILE_PATH}")
    
    print("Data saved successfully.")

async def run():
    global temperature_data  # グローバル変数temperature_dataを使用
    try:
        devices = await BleakScanner.discover(timeout=5)
        print("Found devices:")
        for device in devices:
            print(f"{device.name} ({device.address})")

        target_device = next((d for d in devices if d.name and d.name.startswith("Pico")), None) #Picow to mac mini

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
if __name__ == "__main__":
    try:
        # CSVファイルを初期化
        if os.path.exists(CSV_FILE_PATH):
            os.remove(CSV_FILE_PATH)

        # プログラム実行
        asyncio.run(run())

    except KeyboardInterrupt:
        # Ctrl+Cでプログラムが中断されるとここに来る
        print("Program interrupted by user.")
    except RuntimeError as e:
        if 'Event loop is closed' in str(e):
            print("Event loop is closed. The program has terminated.")
        else:
            print(f"Unhandled RuntimeError: {e}")
    except Exception as e:
        print(f"Unhandled exception: {e}")
    finally:
        save_on_exit()  # プログラム終了時にデータを保存







 







