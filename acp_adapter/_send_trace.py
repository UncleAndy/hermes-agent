"""Diagnostic (temporary): name whoever sends an ACP notification, and with what metadata.

Every `session_update` the agent side sends passes through one SDK method; wrapping it answers two
questions at once - which of our builders produced the update (from the caller's file and line) and
whether the account rode along in ``_meta``. Records to /tmp/acct_trace.log with the process id, so a
send from the gateway daemon is told apart from a send from an ``hermes acp`` child.

Armed from the adapter's entry points; safe to arm more than once.
"""

from __future__ import annotations

import io
import os
import time


def _note(line: str) -> None:
    try:
        with io.open("/tmp/acct_trace.log", "a") as fh:
            fh.write("%s pid=%d %s\n" % (time.strftime("%H:%M:%S"), os.getpid(), line))
    except Exception:
        pass


def arm() -> None:
    import inspect
    import sys

    def find(mod):
        try:
            items = list(vars(mod).items())
        except Exception:
            return None
        for _name, _obj in items:
            if inspect.isclass(_obj) and "session_update" in getattr(_obj, "__dict__", {}):
                return _obj
        return None

    targets = []
    for name, mod in list(sys.modules.items()):
        if mod is None or not (name == "acp" or name.startswith("acp.")):
            continue
        cls = find(mod)
        if cls is not None and cls not in targets:
            targets.append(cls)
    _note("armed: %r" % [c.__module__ + "." + c.__name__ for c in targets])
    for cls in targets:
        if getattr(cls, "_hermes_traced", False):
            continue
        original = cls.session_update

        def make(inner):
            async def traced(self, session_id, update, **kwargs):
                if type(update).__name__ == "UsageUpdate":
                    try:
                        frame = inspect.stack()[1]
                        who = "%s:%d" % (frame.filename.replace("/opt/hermes/", ""), frame.lineno)
                    except Exception:
                        who = "?"
                    meta = getattr(update, "field_meta", None)
                    told = "META" if meta else "no-meta"
                    _note("SEND UsageUpdate %s <- %s meta=%r" % (told, who, meta))
                return await inner(self, session_id, update, **kwargs)

            return traced

        cls.session_update = make(original)
        try:
            cls._hermes_traced = True
        except Exception:
            pass


try:
    arm()
except Exception as _exc:  # pragma: no cover - a diagnostic must never break a door
    _note("arming failed: %r" % (_exc,))
