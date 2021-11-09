import os
import yaml
import time
import argparse

from pathlib import Path
from rtmidi.midiutil import open_midiinput, open_midioutput

from clock import Clock, LedClock
from utils import ImmutableDict
from utils import serialize_dict
from router import Router
from wizard import query_yn
from sequencer import Sequencer
from midi_queue import InputQueue, OutputQueue, DisplayQueue
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


def create_clock(config, controller_input, clock_source, clock_port):
    port = None
    if clock_source == ClockSource.controller:
        port = controller_input
    elif clock_source == ClockSource.external:
        port, _ = open_midiinput(clock_port, interactive=True)

    print(
        f"Using clock source: {clock_source}, "
        f"signature: 1/{config['nof_steps']}"
    )
    clock = Clock(
        clock_source=clock_source,
        midiin=port,
        bpm=config.get("bpm", 120),
        signature=config["nof_steps"]
    )

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
        channel=config["led_config"].get(
            "led_channel", config["input_channel"]
        )
    )
    display_queue = DisplayQueue(
        config=config,
        led_queue=led_queue,
    )
    return (input_queue, output_queue, led_queue, display_queue)


def connect_components(
    clock, input_queue, controller_input, sequencer, router
):
    router.set_sequencer_handler(sequencer.process_step_event)
    router.set_track_handler(sequencer.process_track_event)
    input_queue.add_handler(router.process)
    clock.add_clock_handler(sequencer)

    if clock.clock_source == ClockSource.controller:
        controller_input.set_callback(clock)
        clock.add_drain_handler(input_queue)
    else:
        controller_input.set_callback(input_queue)


def load_config(config_path):
    config = yaml.safe_load(open(config_path))
    print(f"Load config from {config_path}")
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
        config["note_output_map"] = [
            35 + i for i in range(config["nof_tracks"])
        ]

    config["all_track_controls"] = config.get("track_select_map").copy()
    if config.get("track_controls_map", None) is not None:
        solos = config.get("track_controls_map")["solo"].copy()
        mutes = config.get("track_controls_map")["mute"].copy()
        config["all_track_controls"].extend([*solos, *mutes])

    return ImmutableDict(config)


def load_programmers(config_path):
    programmers = {}
    programmer_name = os.path.dirname(config_path)
    programmers_file = Path(programmer_name).joinpath("programmers.yaml")
    if programmers_file.exists():
        programmers = yaml.safe_load(open(programmers_file))
        print(f"Load programmers file from {programmers_file}")

    return programmers


def save_controller_ports(ctrl, config_path):
    config = yaml.safe_load(open(config_path))
    config["controller_input_port"] = ctrl["input_name"]
    config["controller_output_port"] = ctrl["output_name"]
    config = serialize_dict(config)
    with open(config_path, "w") as fout:
        fout.write(yaml.dump(config))


def parse_ports(config, ctrl_inport, ctrl_outport, output_port):
    if output_port is not None and output_port.strip() == "":
        output_port = None

    if ctrl_inport is None:
        ctrl_inport = config.get("controller_input_port", None)

    if ctrl_outport is None:
        ctrl_outport = config.get("controller_output_port", None)

    return ctrl_inport, ctrl_outport, output_port


def main(config, ctrl_inport, ctrl_outport, output_port, clock_port):
    cfg = load_config(config)
    ctrl_inport, ctrl_outport, output_port = parse_ports(
        cfg, ctrl_inport, ctrl_outport, output_port
    )

    clock_source = setup_clock_source(ctrl_inport, clock_port)
    ctrl = open_controller(ctrl_inport, ctrl_outport)
    print(f"\nOpening Sequencer port\n{'=' * 15}")
    sequencer_output, _ = open_midioutput(output_port)
    start_controller(ctrl, load_programmers(config))
    flush_controller(ctrl)

    clock = create_clock(cfg, ctrl["input_port"], clock_source, clock_port)
    input_queue, output_queue, led_queue, display_queue = create_queues(
        config=cfg,
        controller_output=ctrl["output_port"],
        sequencer_output=sequencer_output,
    )
    router = Router(cfg, display_queue)
    sequencer = Sequencer(cfg, display_queue, output_queue)
    connect_components(
        clock, input_queue, ctrl["input_port"], sequencer, router
    )
    if cfg["led_config"]["led_clock"]:
        clock.add_clock_handler(LedClock(cfg, sequencer, display_queue))

    # start necessary threads: InputQueue, OutputQueue, clock (if internal)
    print("Starting threads...")
    input_queue.start()
    led_queue.start()
    display_queue.start()
    output_queue.start()
    clock.start()
    print("Ctrl-c to stop the process")
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            clock.stop()
            if query_yn("Exit?"):
                break
            else:
                clock.start()

    print("Stopping threads...")
    input_queue.stop()
    led_queue.stop()
    display_queue.stop()
    output_queue.stop()
    clock.stop()

    finish_controller(ctrl, load_programmers(config))
    close_controller(ctrl)
    sequencer_output.close_port()
    save_controller_ports(ctrl, config)


if __name__ == "__main__":
    main(**vars(parse_args()))
