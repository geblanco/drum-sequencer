import time
import argparse

from pathlib import Path
from omegaconf import OmegaConf
from rtmidi.midiutil import open_midiinput, open_midioutput

from sequencer import Sequencer
from clock.clock import Clock
from midi_queue import InputQueue, OutputQueue
from controller import (
    flush_controller,
    open_controller,
    close_controller,
)
from modes import (
    TrackMode,
    TrackSelectMode,
    NoteMode,
    LedMode,
    ClockSource,
)


default_portname = "RtMidiIn Client:Midi Through"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--ctrl_inport", type=str, default=default_portname)
    parser.add_argument("--ctrl_outport", type=str, default=default_portname)
    parser.add_argument("--output_port", type=str, default=default_portname)
    parser.add_argument("--clock_port", type=str, default=None)
    return parser.parse_args()


def start_controller(controller_input, programmers, portname):
    controller = programmers.get(portname, None)
    if controller is not None:
        data = bytearray.fromhex(controller.start)
        print(f"Programming controller {portname}...")
        controller_input.send_message(data)
    else:
        print("No programmer found for controller")


def finish_controller(controller_input, programmers, portname):
    controller = programmers.get(portname, None)
    if controller is not None:
        data = bytearray.fromhex(controller.finish)
        print(f"Programming controller {portname}...")
        controller_input.send_message(data)
    else:
        print("No programmer found for controller")


def create_clock(controller_input, clock_source, clock_port):
    port = None
    if clock_source == ClockSource.controller:
        port = controller_input
    elif clock_source == ClockSource.external:
        port = open_midiinput(clock_port)

    clock = Clock(clock_source=clock_source, midiin=port)

    return clock


def setup_clock_source(controller_inport, clock_port):
    if controller_inport == clock_port:
        clock_source = ClockSource.controller
    elif clock_port is not None:
        clock_source = ClockSource.external
    else:
        clock_source = ClockSource.internal

    return clock_source


def create_queues(config, controller_output, sequencer_output):
    input_queue = InputQueue(
        note_mode=config.note_mode,
        channel=config.input_channel,
    )
    # Probably channel not needed here, messages should already be set
    output_queue = OutputQueue(
        midiout=sequencer_output,
        channel=config.output_channel
    )
    led_queue = OutputQueue(
        midiout=controller_output,
        channel=config.led_config.get("led_channel", config.input_channel)
    )
    return (input_queue, output_queue, led_queue)


def connect_components(clock, input_queue, controller_input, sequencer):
    input_queue.add_handler(sequencer.process)
    clock.add_clock_handler(sequencer)

    if clock.clock_source == ClockSource.controller:
        controller_input.set_callback(clock)
        clock.add_drain_handler(input_queue)
    else:
        controller_input.set_callback(input_queue)


def load_config(config):
    conf = OmegaConf.load(config)
    enums = [
        ("note_mode", NoteMode),
        ("track_mode", TrackMode),
        ("track_select_mode", TrackSelectMode),
        ("clock_source", ClockSource),
    ]
    for key, class_ in enums:
        conf[key] = class_(conf[key])

    # ToDo := I/O channels indexed in 1, 0
    conf.led_config.led_mode = LedMode(conf.led_config.led_mode)
    if conf.led_config.led_map_out is None:
        conf.led_config.led_map_out = conf.note_input_map

    if conf.note_output_map is None:
        conf.note_output_map = [35 + i for i in range(conf.nof_tracks)]

    return conf


def load_programmers():
    programmers = {}
    programmers_file = Path("./programmers.yaml")
    if programmers_file.exists():
        programmers = OmegaConf.load(programmers_file)

    return programmers


def main(config, ctrl_inport, ctrl_outport, output_port, clock_port):
    config = load_config(config)
    if ctrl_inport is None or output_port is None:
        raise ValueError("Bad I/O ports")

    if output_port is not None and output_port.strip() == "":
        output_port = None

    clock_source = setup_clock_source(ctrl_inport, clock_port)
    ctrl = open_controller(ctrl_inport, ctrl_outport)
    sequencer_output, _ = open_midioutput(output_port)
    start_controller(ctrl, load_programmers())
    flush_controller(ctrl)

    clock = create_clock(ctrl["input_port"], clock_source, clock_port)
    input_queue, output_queue, led_queue = create_queues(
        config=config,
        controller_output=ctrl["output_port"],
        sequencer_output=sequencer_output,
    )
    sequencer = Sequencer(config, output_queue, led_queue)
    connect_components(clock, input_queue, ctrl["input_port"], sequencer)
    # start necessary threads: InputQueue, OutputQueue, clock (if internal)
    try:
        print("Starting threads...")
        input_queue.start()
        output_queue.start()
        clock.start()
        print("Ctrl-c to stop the process")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        print("Stopping threads...")
        input_queue.stop()
        output_queue.stop()
        clock.stop()

        finish_controller(ctrl, load_programmers())
        close_controller(ctrl)
        sequencer_output.close_port()


if __name__ == "__main__":
    main(**vars(parse_args()))
