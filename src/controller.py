import mido

from pathlib import Path
from rtmidi.midiutil import open_midiinput, open_midioutput


def controller_name_from_port(portname):
    return (
        portname.split(":")[0].lower().replace(" ", "_")
    )


def search_controller_config(portname):
    conf_name = controller_name_from_port(portname)
    return Path("controllers").joinpath(conf_name)


def flush_controller(ctrl_or_midiout):
    if isinstance(ctrl_or_midiout, dict):
        midiout = ctrl_or_midiout["output_port"]
    else:
        midiout = ctrl_or_midiout

    for i in range(127):
        message = mido.Message(type="note_off", note=i, velocity=0)
        midiout.send_message(message.bytes())


def start_controller(controller, programmers):
    portname = controller_name_from_port(controller["input_name"])
    program = programmers.get(portname, None)
    if program is not None:
        data = bytearray.fromhex(program["start"])
        print(f"Start programming controller {portname}...")
        controller["output_port"].send_message(data)
    else:
        print("No programmer found for controller")


def finish_controller(controller, programmers):
    portname = controller_name_from_port(controller["input_name"])
    program = programmers.get(portname, None)
    if program is not None:
        data = bytearray.fromhex(program["finish"])
        print(f"Finish programming controller {portname}...")
        controller["output_port"].send_message(data)
    else:
        print("No programmer found for controller")


def open_controller(ctrl_inport=None, ctrl_outport=None):
    ctrl = {}

    if ctrl_inport is not None and ctrl_inport.strip() == "":
        ctrl_inport = None

    if ctrl_outport is not None and ctrl_outport.strip() == "":
        ctrl_outport = None

    print(f"\nOpening controller input...\n{'=' * 15}")
    ctrl["input_port"], ctrl["input_name"] = open_midiinput(ctrl_inport)
    print(f"\nOpening controller output...\n{'=' * 15}")
    ctrl["output_port"], ctrl["output_name"] = open_midioutput(ctrl_outport)
    return ctrl


def close_controller(ctrl):
    for port in [ctrl[key] for key in ["input_port", "output_port"]]:
        if port is not None and port.is_port_open():
            port.close_port()
