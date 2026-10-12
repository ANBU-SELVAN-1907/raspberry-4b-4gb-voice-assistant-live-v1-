import re
from datetime import datetime

NUMBERS = dict(zip(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split(),
    range(21)))
NUMBERS.update(thirty=30, forty=40, fifty=50, sixty=60, seventy=70, eighty=80, ninety=90)


def spoken_number(value):
    if value.isdigit():
        return int(value)
    words = value.replace("-", " ").split()
    if len(words) == 1:
        return NUMBERS.get(words[0])
    if len(words) == 2 and NUMBERS.get(words[0], 0) >= 20 and 0 < NUMBERS.get(words[1], 0) < 10:
        return NUMBERS[words[0]] + NUMBERS[words[1]]
    return None


def local_reply(text, store):
    value = text.strip()
    lower = value.lower().rstrip(".?!")
    if lower == "timer alert":
        return "Your timer is finished."
    if lower.startswith("remember that "):
        store.remember(value[14:])
        return "I'll remember that."
    if lower in {"forget my memory", "forget everything about me"}:
        store.forget()
        return "I've cleared your saved facts."
    if lower in {"what do you remember", "what do you remember about me"}:
        return "; ".join(store.facts()) or "You haven't asked me to remember anything yet."
    if lower in {"what time is it", "tell me the time", "time"}:
        return datetime.now().strftime("It's %I:%M %p.")
    if lower in {"what is the date", "what day is it", "today's date"}:
        return datetime.now().strftime("It's %A, %d %B %Y.")
    if lower in {"help", "what can you do"}:
        return "Ask questions, set a timer, or say remember that followed by a fact. Say okay stop to pause, or exit to close me."
    return None


def timer_seconds(text):
    match = re.fullmatch(r"(?:set (?:a )?timer (?:for )?|timer )([\w -]{1,24}) (seconds?|minutes?|hours?)[.!?]?", text.lower().strip())
    if not match:
        return None
    factor = 3600 if match[2].startswith("hour") else 60 if match[2].startswith("minute") else 1
    value = spoken_number(match[1])
    return min(value * factor, 86400) if value else None
