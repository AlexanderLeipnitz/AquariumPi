import paho.mqtt.client as mqtt
import subprocess
import sys
import os
import time
from thermometer import read_temp


def get_environment_variable(name):
    try:
        return os.environ[name]
    except KeyError:
        print(f"Please set the environment variable {name}")
        sys.exit(1)


MQTT_SERVER_IP = get_environment_variable("MQTT_SERVER_IP")
MQTT_SERVER_PORT = int(get_environment_variable("MQTT_SERVER_PORT"))
MQTT_USERNAME = get_environment_variable("MQTT_USERNAME")
MQTT_PASSWORD = get_environment_variable("MQTT_PASSWORD")
MQTT_TOPIC_TEMPERATURE = get_environment_variable("MQTT_TOPIC_TEMPERATURE")
MQTT_TOPIC_WEBCAM = get_environment_variable("MQTT_TOPIC_WEBCAM")


# Variables for ongoing recording and pipeline processes
process_libcamera = None
process_ffmpeg = None
process_server = None


# Callback for received MQTT messages
def on_message(client, userdata, msg):
    global process_libcamera, process_ffmpeg, process_server
    command = msg.payload.decode("utf-8")
    print(f"Received command: {command}")

    if command == "on":
        if (
            process_libcamera is None
            and process_ffmpeg is None
            and process_server is None
        ):
            print("Starting the video stream pipeline...")
            try:
                process_libcamera = subprocess.Popen(
                    [
                        "/usr/bin/libcamera-vid",
                        "-t",
                        "0",
                        "--width",
                        "1920",
                        "--height",
                        "1080",
                        "--mode",
                        "2304:1296",
                        "--inline",
                        "--framerate",
                        "30",
                        "-b",
                        "3000000",
                        "--vflip",
                        "--hflip",
                        "--flush",
                        "--nopreview",
                        "-o",
                        "-",
                    ],
                    stdout=subprocess.PIPE,
                )
                process_ffmpeg = subprocess.Popen(
                    [
                        "/usr/bin/ffmpeg",
                        "-f",
                        "h264",
                        "-thread_queue_size",
                        "4096",
                        "-vsync",
                        "drop",
                        "-i",
                        "-",
                        "-vcodec",
                        "copy",
                        "-f",
                        "fifo",
                        "-fifo_format",
                        "rtsp",
                        "-map",
                        "0:v",
                        "-drop_pkts_on_overflow",
                        "1",
                        "-attempt_recovery",
                        "1",
                        "-recovery_wait_time",
                        "1",
                        "-rtsp_transport",
                        "typ",
                        "rtsp://localhost:8554/mystream",
                        "-loglevel",
                        "error",
                        "-stats",
                    ],
                    stdin=process_libcamera.stdout,
                )
                cwd = os.path.dirname(os.path.realpath(__file__))
                process_server = subprocess.Popen(
                    ["/usr/bin/mediamtx", f"{cwd}/mediamtx.yml"]
                )
                print("Video stream pipeline started.")
            except Exception as e:
                print(f"Error starting the pipeline: {e}")
        else:
            print("Pipeline already running.")

    elif command == "off":
        if (
            process_libcamera is not None
            and process_ffmpeg is not None
            and process_server is not None
        ):
            print("Stopping the video stream pipeline...")
            try:
                # Beende beide Prozesse
                process_libcamera.terminate()
                process_ffmpeg.terminate()
                process_server.terminate()
                process_libcamera = None
                process_ffmpeg = None
                process_server = None
                print("Video stream pipeline stopped.")
            except Exception as e:
                print(f"Error stopping the pipeline: {e}")
        else:
            print("No running pipeline to stop found.")
    else:
        print(f"Unknown command: {command}")


# Callback for succesful MQTT connection
def on_connect(client, userdata, flags, rc, properties):
    print(f"Connected with MQTT broker. Returning: {rc}")
    client.subscribe(MQTT_TOPIC_WEBCAM)


# Initialization of the MQTT client
client = mqtt.Client(
    client_id="AquariumPi", callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(username=MQTT_USERNAME, password=MQTT_PASSWORD)

# Connect to broker
client.connect(MQTT_SERVER_IP, MQTT_SERVER_PORT, 60)

# Main process loop
try:
    print("MQTT client started. Waiting for commands.")
    client.loop_start()
    while True:
        temperature = read_temp()
        client.publish(
            MQTT_TOPIC_TEMPERATURE, payload=f"{temperature:3.3f}", qos=0, retain=True
        )
        print(f"Temperature: {temperature:3.3f}")
        time.sleep(100)

except Exception as e:
    print(f"Quiting MQTT client. Reason: {e}")
    if (
        process_libcamera is not None
        and process_ffmpeg is not None
        and process_server is not None
    ):
        process_libcamera.terminate()
        process_ffmpeg.terminate()
        process_server.terminate()
    client.loop_stop()
    client.disconnect()
