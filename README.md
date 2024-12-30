# AquariumPi
Monitor and control an aquarium with a Raspberry Pi via MQTT.

## Temperature Measurement
- Using `DS18B20` Sensor via one-wire bus
- Setup instructions: https://www.laub-home.de/wiki/Raspberry_Pi_DS18B20_Temperatur_Sensor

## Underwater webcam streaming
- Using `Arducam 12MP IMX708 HDR 120°(H) Wide Angle Camera Module with M12 Lens` and `Entaniya Waterproof Case`
- Provides a video stream via [mediamtx server](https://github.com/bluenviron/mediamtx)

## Setup:
- Activate 1-wire interface via `sudo raspi-config`
- Add `dtoverlay=imx708` to `/boot/firmware/config.txt`
- Set environment variables in `.env`
- Check if `aquarium.service` has the correct path for `mqtt_aquarium.py` and environment file
- Copy `aquarium.servive` to `/etc/systemd/system/`
- `sudo systemctl daemon-reload && sudo systemctl enable aquarium.service && sudo systemctl start aquarium.service`