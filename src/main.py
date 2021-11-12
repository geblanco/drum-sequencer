import time
import argparse

from rtmidi.midiutil import open_midiinput

from clock import Clock, LedClock
from router import Router
from wizard import query_yn
from modes import ClockSource, ViewMode
from midi_queue import InputQueue, OutputQueue, DisplayQueue
from views import (
    Drumpad,
    Velocity,
    Sequencer,
    TrackSelect,
    get_drumpad_view_hook
)
from utils import (
    load_config,
    load_programmers,
    save_controller_ports,
)
from controller import (
    start_controller,
    finish_controller,
    flush_controller,
    open_controller,
    close_controller,
    open_port,
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


def parse_ports(config, ctrl_inport, ctrl_outport, output_port):
    if output_port is not None and output_port.strip() == "":
        output_port = None

    if ctrl_inport is None:
        ctrl_inport = config.get("controller_input_port", None)

    if ctrl_outport is None:
        ctrl_outport = config.get("controller_output_port", None)

    if output_port is None:
        output_port = config.get("sequencer_output_port", None)

    return ctrl_inport, ctrl_outport, output_port


def init_clock_controller_and_sys_output(
    cfg_path, cfg, ctrl_inport, ctrl_outport, clock_port, output_port
):
    clock_source = setup_clock_source(ctrl_inport, clock_port)
    ctrl = open_controller(ctrl_inport, ctrl_outport)
    start_controller(ctrl, load_programmers(cfg_path))
    flush_controller(ctrl)
    clock = create_clock(cfg, ctrl["input_port"], clock_source, clock_port)
    sys_output, _ = open_port(output_port, "output", "sequencer")

    return ctrl, clock, sys_output


def create_queues(config, controller_output, sys_output):
    input_queue = InputQueue(
        note_mode=config["note_mode"],
        channel=config["input_channel"],
    )
    # Probably channel not needed here, messages should already be set
    output_queue = OutputQueue(
        midiout=sys_output,
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


def get_flush_callback(ctrl):
    def flush():
        flush_controller(ctrl)

    return flush


def setup_components(
    cfg, ctrl, clock, input_queue, display_queue, output_queue
):
    led_clock = None
    router = Router(cfg, display_queue, get_flush_callback(ctrl))
    sequencer = Sequencer(cfg, display_queue, output_queue)

    if cfg["led_config"]["led_clock"]:
        led_clock = LedClock(
            config=cfg,
            track_state_getter=sequencer.get_track_state,
            display_queue=display_queue
        )
        clock.add_clock_handler(led_clock)

    track_select = TrackSelect(
        track_controller=sequencer.track_controller,
        tracks_selector=sequencer.select_tracks
    )
    router.add_view(ViewMode.omni, track_select)

    if cfg.get("views", None) is not None:
        views = cfg["views"]
        if "drumpad" in views:
            drumpad = Drumpad(cfg, display_queue, output_queue)
            router.add_view(ViewMode.drumpad, drumpad)
            clock.add_slave(drumpad)

        if "velocity" in views:
            velocity = Velocity(
                config=cfg,
                track_controller=sequencer.track_controller,
                track_getter=sequencer.get_track,
                display_queue=display_queue,
            )
            router.add_view(ViewMode.velocity, velocity)

    router.add_view(ViewMode.sequencer, sequencer)
    on_active, on_inactive = get_drumpad_view_hook(input_queue, led_clock)
    router.add_view_event_hooks(on_active, on_inactive)
    input_queue.add_handler(router.process)
    clock.add_clock_handler(sequencer)

    if clock.clock_source == ClockSource.controller:
        # if controller provides the clock, our clock will drain
        # all non-clock events through the drain callback
        ctrl["input_port"].set_callback(clock)
        clock.add_drain_handler(input_queue)
    else:
        ctrl["input_port"].set_callback(input_queue)

    return router, (sequencer,)


def main(config, ctrl_inport, ctrl_outport, output_port, clock_port):
    cfg = load_config(config)
    ctrl_inport, ctrl_outport, output_port = parse_ports(
        cfg, ctrl_inport, ctrl_outport, output_port
    )

    ctrl, clock, sys_output = init_clock_controller_and_sys_output(
        config, cfg, ctrl_inport, ctrl_outport, clock_port, output_port,
    )

    input_queue, output_queue, led_queue, display_queue = create_queues(
        config=cfg,
        controller_output=ctrl["output_port"],
        sys_output=sys_output,
    )

    router, views = setup_components(
        cfg, ctrl, clock, input_queue, display_queue, output_queue
    )

    # start necessary threads: InputQueue, OutputQueue, clock (if internal)
    print("Starting threads...")
    for obj in [input_queue, led_queue, display_queue, output_queue, clock]:
        obj.start()

    print("Ctrl-c to stop the process")
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            clock.pause()
            if query_yn("Exit?"):
                clock.stop()
                break
            else:
                clock.start()

    print("Stopping threads...")
    for obj in [input_queue, led_queue, display_queue, output_queue, clock]:
        obj.stop()

    finish_controller(ctrl, load_programmers(config))
    close_controller(ctrl)
    sys_output.close_port()
    save_controller_ports(ctrl, config)


if __name__ == "__main__":
    main(**vars(parse_args()))
