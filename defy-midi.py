#!/usr/bin/env python3

from evdev import InputDevice, ecodes
import rtmidi
import sys

DEVICE_PATH = "/dev/input/by-id/usb-DYGMA_DEFY_235779CEB34CC05D-if02-event-kbd"

START_NOTE = 36      # C2
VELOCITY_DEFAULT = 75
MIDI_CHANNEL = 0     # MIDI channel 1

# 12 columns = one chromatic octave.
# Rows are listed from low to high.
LAYOUT_ROWS = [
    # C2 ... B2
    [
        "KEY_F4", "KEY_Z", "KEY_X", "KEY_C",
        "KEY_V", "KEY_B", "KEY_N", "KEY_M",
        "KEY_COMMA", "KEY_DOT", "KEY_MINUS", "KEY_F8",
    ],

    # C3 ... B3
    [
        "KEY_F3", "KEY_A", "KEY_S", "KEY_D",
        "KEY_F", "KEY_G", "KEY_H", "KEY_J",
        "KEY_K", "KEY_L", "KEY_SEMICOLON", "KEY_F7",
    ],

    # C4 ... B4
    [
        "KEY_F2", "KEY_Q", "KEY_W", "KEY_E",
        "KEY_R", "KEY_T", "KEY_Y", "KEY_U",
        "KEY_I", "KEY_O", "KEY_P", "KEY_F6",
    ],

    # C5 ... B5
    [
        "KEY_F1", "KEY_1", "KEY_2", "KEY_3",
        "KEY_4", "KEY_5", "KEY_6", "KEY_7",
        "KEY_8", "KEY_9", "KEY_0", "KEY_F5",
    ],
]

KEY_TO_NOTE = {}

for row_idx, row in enumerate(LAYOUT_ROWS):
    for col_idx, key_name in enumerate(row):
        key_code = getattr(ecodes, key_name)
        note = START_NOTE + row_idx * 12 + col_idx
        KEY_TO_NOTE[key_code] = note

SHIFT_KEYS = {
    ecodes.KEY_LEFTSHIFT,
    ecodes.KEY_RIGHTSHIFT,
}

CTRL_KEYS = {
    ecodes.KEY_LEFTCTRL,
    ecodes.KEY_RIGHTCTRL,
}

LEFT_ALT = ecodes.KEY_LEFTALT
RIGHT_ALT = ecodes.KEY_RIGHTALT  # AltGr

def required_modifiers_are_held(held_modifiers):
    has_shift = bool(held_modifiers & SHIFT_KEYS)
    has_ctrl = bool(held_modifiers & CTRL_KEYS)
    has_left_alt = LEFT_ALT in held_modifiers
    has_right_alt = RIGHT_ALT in held_modifiers

    return has_shift and has_ctrl and has_left_alt and has_right_alt

def note_on(out, note, velocity=VELOCITY_DEFAULT):
    out.send_message([0x90 | MIDI_CHANNEL, note, velocity])

def note_off(out, note):
    out.send_message([0x80 | MIDI_CHANNEL, note, 0])

def main():
    dev = InputDevice(DEVICE_PATH)
    print(f"Reading from: {dev.path} | {dev.name}")

    midiout = rtmidi.MidiOut()
    midiout.open_virtual_port("Defy MIDI")

    print("Created virtual MIDI port: Defy MIDI")
    print("Only Ctrl+Shift+Alt+AltGr modified keys will emit MIDI.")
    print("Press Ctrl+C from a normal/non-MIDI layer to quit.")
    print()

    held_modifiers = set()

    # Key code -> note. This ensures note-off matches the original note
    # even if modifiers are released/change before the key release.
    active_notes_by_key = {}

    try:
        for event in dev.read_loop():
            if event.type != ecodes.EV_KEY:
                continue

            code = event.code

            if code in SHIFT_KEYS or code in CTRL_KEYS or code in {LEFT_ALT, RIGHT_ALT}:
                if event.value == 1:
                    held_modifiers.add(code)
                elif event.value == 0:
                    held_modifiers.discard(code)
                continue

            if code not in KEY_TO_NOTE:
                continue

            # 0 = release, 1 = press, 2 = autorepeat
            if event.value == 1:
                if not required_modifiers_are_held(held_modifiers):
                    continue

                note = KEY_TO_NOTE[code]

                if code not in active_notes_by_key:
                    note_on(midiout, note, VELOCITY_DEFAULT)
                    active_notes_by_key[code] = note
                    print(f"NOTE ON  {note}")

            elif event.value == 0:
                note = active_notes_by_key.pop(code, None)

                if note is not None:
                    note_off(midiout, note)
                    print(f"NOTE OFF {note}")

            # ignore autorepeat

    except KeyboardInterrupt:
        print("\nStopping. Sending note-off for any stuck notes.")
        for note in set(active_notes_by_key.values()):
            note_off(midiout, note)
        sys.exit(0)

if __name__ == "__main__":
    main()
