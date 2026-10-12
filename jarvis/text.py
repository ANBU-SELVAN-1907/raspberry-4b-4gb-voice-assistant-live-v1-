import re

EXPRESSIONS = {"neutral", "happy", "curious", "sad", "surprised", "concerned", "excited", "calm", "confused", "playful"}


def control(text):
    value = re.sub(r"[^a-z ]", "", text.lower()).strip()
    if value in {"exit", "jarvis exit", "goodbye jarvis", "shut down assistant"}:
        return "exit"
    if value in {"stop", "okay stop", "ok stop", "stop talking", "go to sleep"}:
        return "stop"
    if value in {"hey jarvis", "hello jarvis"}:
        return "wake"
    return None


class SpeechChunks:
    """Bound speech chunks, preserving words and avoiding tiny first chunks."""
    def __init__(self):
        self.pending = ""
        self.emitted = False

    def feed(self, text, final=False):
        self.pending += text
        output = []
        while self.pending:
            match = re.search(r"[.!?](?:\s|$)", self.pending)
            cut = match.end() if match and match.end() >= 12 else None
            if cut is None and not self.emitted:
                clause = re.search(r"[,;:](?:\s|$)", self.pending)
                if clause and clause.end() >= 45:
                    cut = clause.end()
            limit = 90 if not self.emitted else 160
            if cut is None and len(self.pending) >= limit:
                cut = self.pending.rfind(" ", 0, limit)
                if cut < 1:
                    cut = limit
            if cut is None:
                if not final:
                    break
                cut = len(self.pending)
            part, self.pending = self.pending[:cut], self.pending[cut:]
            cleaned = re.sub(r"[*#`_]", "", part).strip()
            if cleaned:
                output.append(cleaned)
                self.emitted = True
        return output


def expression(text):
    lower = text.lower()
    for name, words in (
        ("concerned", ("danger", "careful", "unsafe")),
        ("sad", ("sorry", "sad", "loss")),
        ("excited", ("amazing", "exciting", "wonderful")),
        ("happy", ("great", "glad", "happy", "welcome")),
        ("confused", ("not sure", "don't know", "uncertain")),
        ("curious", ("question", "explore", "wonder")),
        ("calm", ("relax", "breathe", "peace")),
        ("playful", ("joke", "funny")),
    ):
        if any(word in lower for word in words):
            return name
    return "neutral"
