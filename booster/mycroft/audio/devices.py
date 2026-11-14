"""Pick the microphone by name. Run `python -m mycroft.audio.devices` to list what is available."""


def input_device_index(pa, name: str) -> int | None:
    """Index of the first input device whose name contains `name`. None = system default."""
    if not name:
        return None
    if name.isdigit():
        return int(name)
    wanted = name.lower()
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if info.get("maxInputChannels", 0) > 0 and wanted in str(info.get("name", "")).lower():
            return i
    print(f"[audio] No microphone matching '{name}', using the system default.", flush=True)
    return None


class NoMicrophone(RuntimeError):
    pass


def open_input(pa, rate: int, chunk: int):
    """Open a 16-bit mono input stream on the configured microphone.

    If that one cannot be opened (Windows has no default recording device, or the chosen one
    is unplugged), every other microphone is tried before giving up.
    """
    import pyaudio
    from mycroft.config import get_config

    def try_open(index):
        return pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=rate,
            input=True,
            frames_per_buffer=chunk,
            input_device_index=index,
        )

    first_error = None
    try:
        return try_open(input_device_index(pa, get_config().input_device))
    except Exception as e:
        first_error = e

    names = []
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if info.get("maxInputChannels", 0) <= 0:
            continue
        names.append(str(info.get("name", i)))
        try:
            return try_open(i)
        except Exception:
            continue

    if names:
        raise NoMicrophone(
            f"None of the microphones Windows lists could be opened ({', '.join(names)}). "
            f"Check Settings > Privacy & security > Microphone. First error: {first_error}"
        )
    raise NoMicrophone(
        "Windows reports no microphone at all. Plug one in or switch it on, and check "
        "Settings > System > Sound > Input."
    )


def _main():
    import pyaudio

    pa = pyaudio.PyAudio()
    try:
        default_in = pa.get_default_input_device_info().get("index")
    except Exception:
        default_in = None
    print("Microphones (put part of the name in config.yaml under audio.input_device):")
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if info.get("maxInputChannels", 0) > 0:
            mark = "  <- default" if i == default_in else ""
            print(f"  {i}: {info.get('name')}{mark}")
    pa.terminate()

    try:
        import sounddevice as sd
        print("\nSpeakers (audio.output_device):")
        for i, dev in enumerate(sd.query_devices()):
            if dev["max_output_channels"] > 0:
                print(f"  {i}: {dev['name']}")
    except Exception as e:
        print(f"\nCould not list speakers: {e}")


if __name__ == "__main__":
    _main()
