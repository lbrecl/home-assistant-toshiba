"""Constants for Toshiba Legacy TV (CT-90405 remote profile)."""

DOMAIN = "toshiba_legacy"
DEFAULT_PORT = 8080
# CT-90405 NEC command bytes; the IPC API uses address + inverse + command.
# Reference: Linux drivers/media/rc/keymaps/rc-ct-90405.c.
# MENU 40bf5b was confirmed visually on the 46TL938K.
KEYS = {
    "power": "40bf12",
    "volume_up": "40bf1a",
    "volume_down": "40bf1e",
    "mute": "40bf10",
    "up": "40bf19",
    "down": "40bf1d",
    "left": "40bf42",
    "right": "40bf40",
    "ok": "40bf21",
    "back": "40bf64",
    "exit": "40bf43",
    "menu": "40bf5b",
    "info": "40bf16",
    "input": "40bf14",
    "channel_up": "40bf1b",
    "channel_down": "40bf1f",
    **{str(n): f"40bf{n:02x}" for n in range(10)},
}
