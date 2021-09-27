import time
import argparse

from pathlib import Path
from omegaconf import OmegaConf
from rtmidi.midiutil import open_midiinput, open_midioutput

from clock.clock import Clock
from modes import TrackMode, NoteMode, LedMode, ClockSource
from sequencer import Sequencer
from midi_queue import InputQueue, OutputQueue


default_portname = "RtMidiIn Client:Midi Through"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--ctrl_inport", type=str, default=default_portname)
    parser.add_argument("--ctrl_outport", type=str, default=default_portname)
    parser.add_argument("--output_port", type=str, default=default_portname)
    parser.add_argument("--clock_port", type=str, default=None)
    return parser.parse_args()


def setup_clock(clock_source, controller_input, clock_port):
    port = None
    if clock_source == ClockSource.controller:
        port = controller_input
    elif clock_source == ClockSource.external:
        port = open_midiinput(clock_port)

    clock = Clock(clock_source=clock_source, midiin=port)

    return clock


def start_controller(controller_input, programmers, portname):
    controller_name = portname.split(:)[0].lower().replace(" ", "_")
    controller = programmers.get(portname, None)
    if controller is not None:
        data = bytearray.fromhex(controller.start)
        print(f"Programming controller {portname}...")
        controller_input.send_message(data)
    else:
        print("No programmer found for controller")


def finish_controller(controller_input, programmers, portname):
    controller_name = portname.split(:)[0].lower().replace(" ", "_")
    controller = programmers.get(portname, None)
    if controller is not None:
        data = bytearray.fromhex(controller.finish)
        print(f"Programming controller {portname}...")
        controller_input.send_message(data)
    else:
        print("No programmer found for controller")


def create_classes(
    config,
    controller_input,
    controller_output,
    sequencer_output,
    clock_source,
    clock_port,
):
    clock = setup_clock(clock_source, controller_input, clock_port)

    led_channel = config.get("led_channel", None)
    if led_channel is None:
        led_channel = config.input_channel

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
        channel=(
            config.led_channel
            if config.led_channel is not None
            else config.input_channel
        )
    )
    sequencer = Sequencer(
        track_mode=config.track_mode,
        output_channel=config.output_channel,
        output_queue=output_queue,
        nof_tracks=config.nof_tracks,
        steps_per_track=config.steps_per_track,
        track_select_map=config.get("track_select_map", None),
        note_input_map=config.note_input_map,
        note_output_map=config.note_output_map,
        note_mode=config.note_mode,
        led_config=config.led_config,
        led_queue=led_queue
    )

    return (
        clock,
        input_queue,
        output_queue,
        led_queue,
        sequencer,
    )


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
        ("clock_source", ClockSource)
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


def main(config, ctrl_inport, ctrl_outport, output_port, clock_port):
    config = load_config(config)
    if ctrl_inport is None or output_port is None:
        raise ValueError("Bad I/O ports")

    if ctrl_inport == clock_port:
        clock_source = ClockSource.controller
    elif clock_port is not None:
        clock_source = ClockSource.external
    else:
        clock_source = ClockSource.internal

    controller_input, portname = open_midiinput(
        ctrl_inport, interactive=ctrl_inport == default_portname
    )
    controller_output, _ = open_midiinput(
        ctrl_outport, interactive=ctrl_outport == default_portname
    )
    sequencer_output, _ = open_midioutput(
        output_port, interactive=output_port == default_portname
    )

    programmers_file = Path("./programmers.yaml")
    programmers = None
    if programmers_file.exists():
        programmers = OmegaConf.load(programmers_file)
        start_controller(controller_input, programmers, portname)

    clock, input_queue, output_queue, led_queue, sequencer = create_classes(
        config=config,
        controller_input=controller_input,
        controller_output=controller_output,
        sequencer_output=sequencer_output,
        clock_source=clock_source,
        clock_port=clock_port,
    )

    connect_components(clock, input_queue, controller_input, sequencer)
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
        if programmers is not None:
            finish_controller(controller_input, programmers, portname)
        controller_input.close_port()
        controller_output.close_port()
        sequencer_output.close_port()


if __name__ == "__main__":
    main(**vars(parse_args()))