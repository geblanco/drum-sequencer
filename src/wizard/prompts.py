import mido


_HELP_STR_ = """
This wizard will help you configure your controller. It will guide you through
the process step by step, if any of the requested options is not clear, you
can hit `h` in any of the prompts to get a description of each option.

The wizard will do it's best to guess your setup, but it may fail, you can
always complete or fix your configuration in the `user_config.yaml` file.

This is an Open Source initiative, if you created a nice setup for your
controller, please share it at: # ToDo := share url so others can use it too.

Thanks! (:

You can always exit the wizard by hitting Ctrl-c
"""

_OPTS_STR_ = """
Options:
------------------------------------------------------------------------------
* Number of tracks
------------------------------------------------------------------------------
This is the number of tracks you want the sequencer to handle. Typically, any
number between 1 and 8 tracks.

------------------------------------------------------------------------------
* Number of steps per track
------------------------------------------------------------------------------
This is the number of subdivisions per bar. Quarter note (1/4 = 4), half note
(1/2 = 2) and so on.

------------------------------------------------------------------------------
* Track Mode
------------------------------------------------------------------------------
This option has to do with your controller, options are `all_tracks`,
`select_tracks`, choose the first one if your controller can display all the
`number of tracks` at once. If your controller cannot handle all tracks at
once (either) too small controller or too much tracks for the controller, you
will have to choose the amount of displayed tracks and some buttons to toggle
between one track and another inside the controller.

------------------------------------------------------------------------------
* Number of displayed tracks
------------------------------------------------------------------------------
The number of tracks your controller can display at once.

------------------------------------------------------------------------------
* Select track mode
------------------------------------------------------------------------------
Arrows mode:  With two pads you roll between displayed tracks contiguously
Select track: You use one button to select each track (your controller must
              have one free button for each track).

------------------------------------------------------------------------------
* Track selection pads
------------------------------------------------------------------------------
Buttons to select the displayed tracks. Works with `select track mode` mode
to handle how tracks will be selected.
"""


def check_constraints(reply, type_, constraints):
    ret = None
    try:
        ret = type_(reply)
        if constraints is not None:
            if ret < constraints[0] or ret > constraints[-1]:
                ret = None
    except Exception:
        pass
    finally:
        return ret


def query_yn(text):
    ans = False
    reply = input(f"{text} (Y/n): ")
    reply = reply.strip().lower()
    if reply in ["h", "help"]:
        print(_OPTS_STR_)
        ans = query_yn(text)
    elif reply == "":
        ans = query_yn(text)
    elif reply in ["y", "yes"]:
        ans = True

    return ans


def query_choices(text, choices):
    ans = None
    valid = [ch[0].lower() for ch in choices] + [ch.lower() for ch in choices]
    short_ch = "/".join([
        f"[{ch[0].upper()}]{ch[1:].replace('_', ' ')}" for ch in choices
    ])

    while ans is None:
        reply = input(f"{text} ({short_ch}): ")
        reply = reply.strip().lower()
        if reply in ["h", "help"]:
            print(_OPTS_STR_)
        elif reply != "" and reply in valid:
            ans = reply

    return ans


def query_num(text, type_=None, sample=None, constraints=None):
    ans = None
    if sample is not None:
        if not isinstance(sample, list):
            sample = [sample]

        if len(sample) > 4:
            sample[4:] = "."
            sample[4] += ".."

        text += f" ({', '.join([str(s) for s in sample])}): "

    if not text.endswith(": "):
        text += ": "

    while ans is None:
        reply = input(text)
        reply = reply.strip().lower()
        if reply in ["h", "help"]:
            print(_OPTS_STR_)
        elif reply != "":
            if type_ is not None:
                ans = check_constraints(reply, type_, constraints)
                if ans is None:
                    err = "Invalid input, it must be a number! "
                    if constraints is not None:
                        err += (
                            f"And be between {constraints[0]}"
                            f" and {constraints[-1]}"
                        )

                    print(err)
            else:
                ans = reply
    return ans


def confirm_pad(text, midiout, midomsg):
    midiout.send_message(midomsg.bytes())
    if not query_yn(text):
        msg_copy = mido.Message(
            type="note_off", velocity=0, note=midomsg.note
        )
        midiout.send_message(msg_copy.bytes())
        return False

    return True


# __all__ = [
#     "_HELP_STR_",
#     "query_yn",
#     "query_choices",
#     "query_num",
#     "confirm_pad"
# ]
