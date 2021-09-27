import mido


def query_yn(text):
    ans = False
    reply = input(f"{text} (Y/n)")
    reply = reply.strip().lower()
    if reply in ["h", "help"]:
        print(_HELP_STR_)
        ans = query_yn(text)
    elif reply == "":
        ans = query(text)
    elif reply in ["y", "yes"]:
        ans = True

    return ans


def query_choices(text, choices):
    ans = False
    short_ch = "/".join([ch[0].upper() for ch in choices])
    reply = input(f"{text} ({short_ch})")
    reply = reply.strip().lower()
    if reply == ["h", "help"]:
        print(_HELP_STR_)
        ans = query(text, choices)
    elif reply == "":
        ans = query(text, choices)
    elif reply in short_ch:
        ans = reply

    return ans


def query_num(text, type_=None, sample=None):
    ans = False
    if sample is not None:
        if not isinstance(sample, list):
            sample = [sample]

        if len(sample) > 4:
            sample[4:] = "."
            sample[4] += ".."

        text += f" ({str(s) for s in sample})"

    reply = input(text)
    reply = reply.strip().lower() == ""
    if reply == ["h", "help"]:
        print(_HELP_STR_)
        ans = query(text, type_, sample)
    elif reply == "":
        ans = query(text)
    else:
        ans = type_(reply) if type_ is not None else reply

    return ans


def confirm_pad(text, midiout, message):
    midout.send_message(message.bytes())
    if not query_yn(text):
        msg_copy = mido.Message(
            type="note_off", velocity=0, note=message.note
        )
        midout.send_message(msg_copy)
        return False

    return True
