# Initiate three APA-102 Leds
#
# Red =          ([0xFF, 0x00, 0x00, 0x20])
# Green =        ([0xFF, 0x00, 0x20, 0x00])
# Blue =         ([0xFF, 0x20, 0x00, 0x00])
# Yellow =       ([0xFF, 0x00, 0x20, 0x20])
# Magenta =      ([0xFF, 0x20, 0x00, 0x20])
# Cyan =         ([0xFF, 0x20, 0x20, 0x00])
# White/all on = ([0xFE, 0x20, 0x20, 0x20])
#
# Import leds first, after leds the rest of these slow imports is done while leds are already on!

from time import sleep
import spidev

spi = spidev.SpiDev()
spi.open(0, 1)

MIN_BRIGHTNESS = 225
MAX_BRIGHTNESS = 255

def led_color(brightness, color):
    # brightness can be set at two places. This results in a much better fading experience.
    # The first parameter (a) has a range from 225 - 255 and the second parameter (b) has a range from 1 - 255
    a = brightness
    b = 1 + (brightness-MIN_BRIGHTNESS)
    if color == "off":
        spi.xfer([a, 0, 0, 0])
    elif color == "red":
        spi.xfer([a, 0, 0, b])
    elif color == "green":
        spi.xfer([a, 0, b, 0])
    elif color == "blue":
        spi.xfer([a, b, 0, 0])
    elif color == "yellow":
        spi.xfer([a, 0, b, b])
    elif color == "magenta":
        spi.xfer([a, b, 0, b])
    elif color == "cyan":
        spi.xfer([a, b, b, 0])
    elif color == "white":
        spi.xfer([a, b, b, b])


def led_init():
    spi.xfer([0, 0, 0, 0])


def led_end():
    spi.xfer([255, 255, 255, 255])


def led_set(led_1="off", led_2="off", led_3="off", brightness=225):
    led_init()
    led_color(brightness, led_1)
    led_color(brightness, led_2)
    led_color(brightness, led_3)
    led_end()


def led_fade_in(led_1="green", led_2="green", led_3="green"):
    brightness = MIN_BRIGHTNESS
    for _ in range(MIN_BRIGHTNESS, MAX_BRIGHTNESS):
        brightness += 1
        led_set(led_1, led_2, led_3, brightness)
        sleep(0.02)


def led_fade_out(led_1="green", led_2="green", led_3="green"):
    brightness = MAX_BRIGHTNESS
    for _ in range(MIN_BRIGHTNESS, MAX_BRIGHTNESS):
        brightness -= 1
        led_set(led_1, led_2, led_3, brightness)
        sleep(0.02)
