from clock import InternalClock
from rtmidi.midiutil import open_midioutput


def main():
    port, name = open_midioutput(interactive=True)
    clock = InternalClock()
    clock.set_callback(lambda data: port.send_message(data))
    clock.start()
    clock.join()


if __name__ == "__main__":
    main()