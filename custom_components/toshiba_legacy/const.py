"""Constants for Toshiba Legacy TV."""

DOMAIN = "toshiba_legacy"
DEFAULT_PORT = 8080
KEYS = {
    "power": "40BF12",
    "volume_up": "40BF1A",
    "volume_down": "40BF1E",
    "mute": "40BF10",
    "up": "40BF82",
    "down": "40BF83",
    "left": "40BF1D",
    "right": "40BF19",
    "ok": "40BF89",
    "back": "40BFD9",
    "exit": "40BF58",
    "menu": "40BF80",
    "info": "40BF84",
    "input": "40BF0F",
    "channel_up": "40BF1B",
    "channel_down": "40BF1F",
    **{str(n): f"40BF{n:02X}" for n in range(10)},
}
