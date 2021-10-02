import yaml
import time
import argparse

from pathlib import Path
from omegaconf import OmegaConf
from rtmidi.midiutil import open_midiinput, open_midioutput

from sequencer import Sequencer
from clock.clock import Clock
from midi_queue import InputQueue, OutputQueue
from controller import (
    start_controller,
    finish_controller,
    flush_controller,
    open_controller,
    close_controller,
)
from modes import (
    TrackMode,
    TrackSelectMode,
    NoteMode,
    LedMode,
    LedColors,
    ClockSource,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--ctrl_inport", type=str, default=None)
    parser.add_argument("--ctrl_outport", type=str, default=None)
    parser.add_argument("--output_port", type=str, default=None)
    parser.add_argument("--clock_port", type=str, default=None)
    return parser.parse_args()


def create_clock(controller_input, clock_source, clock_port):
    port = None
    if clock_source == ClockSource.controller:
        port = controller_input
    elif clock_source == ClockSource.external:
        port = open_midiinput(clock_port)

    print(f"Using clock source: {clock_source}")
    clock = Clock(clock_source=clock_source, midiin=port)

    return clock


def setup_clock_source(controller_inport, clock_port):
    if controller_inport is not None and controller_inport == clock_port:
        clock_source = ClockSource.controller
    elif clock_port is not None:
        clock_source = ClockSource.external
    else:
        clock_source = ClockSource.internal

    return clock_source


def create_queues(config, controller_output, sequencer_output):
    input_queue = InputQueue(
        note_mode=config["note_mode"],
        channel=config["input_channel"],
    )
    # Probably channel not needed here, messages should already be set
    output_queue = OutputQueue(
        midiout=sequencer_output,
        channel=config["output_channel"]
    )
    led_queue = OutputQueue(
        midiout=controller_output,
        channel=config["led_config"].get("led_channel", config["input_channel"])
    )
    return (input_queue, output_queue, led_queue)


def connect_components(clock, input_queue, controller_input, sequencer):
    input_queue.add_handler(sequencer.process)
    # clock.add_clock_handler(sequencer)

    if clock.clock_source == ClockSource.controller:
        controller_input.set_callback(clock)
        clock.add_drain_handler(input_queue)
    else:
        controller_input.set_callback(input_queue)


def load_config(config_path):
    config = yaml.safe_load(open(config_path))
    enums = [
        ("note_mode", NoteMode),
        ("track_mode", TrackMode),
        ("track_select_mode", TrackSelectMode),
    ]
    for key, class_ in enums:
        config[key] = class_(config[key])

    # ToDo := I/O channels indexed in 1, 0
    config["led_config"]["led_mode"] = LedMode(
        config["led_config"].get("led_mode", LedMode.handled)
    )
    config["led_config"]["led_color_mode"] = LedColors(
        config["led_config"].get("led_color_mode", LedColors.default)
    )
    if config["led_config"].get("led_map_out", None) is None:
        config["led_config"]["led_map_out"] = config["note_input_map"]

    if config.get("note_output_map", None) is None:
        config["note_output_map"] = [35 + i for i in range(config["nof_tracks"])]

    return config


def load_programmers():
    programmers = {}
    programmers_file = Path("./programmers.yaml")
    if programmers_file.exists():
        programmers = yaml.safe_load(open(programmers_file))

    return programmers


def main(config, ctrl_inport, ctrl_outport, output_port, clock_port):
    config = load_config(config)

    if output_port is not None and output_port.strip() == "":
        output_port = None

    clock_source = setup_clock_source(ctrl_inport, clock_port)
    ctrl = open_controller(ctrl_inport, ctrl_outport)
    print(f"\nOpening Sequencer port\n{'=' * 15}")
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
        led_queue.start()
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
        led_queue.stop()
        output_queue.stop()
        clock.stop()

        finish_controller(ctrl, load_programmers())
        close_controller(ctrl)
        sequencer_output.close_port()


if __name__ == "__main__":
    main(**vars(parse_args()))
