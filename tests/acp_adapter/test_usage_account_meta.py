"""The account travels with the usage update, in the provider's own words.

ACP carries no money: ``usage_update`` speaks of tokens and, optionally, of the session's own cost, and
``/usage`` - the block that shows a balance - is a command of Hermes' CLI, not of the protocol. What a
provider reports about the account is a list of labelled lines, and they ride in
``_meta.hermes.accountUsage``, which is what ``_meta`` is reserved for. An editor therefore shows the
balance of whatever provider is in use without knowing anything about the provider.
"""

from __future__ import annotations

from acp_adapter.server import _account_usage_meta


class _Agent:
    """Just enough of an agent: the provider, and the last response's own accounting."""

    def __init__(self, *, provider: str = "nous", credits_state=None) -> None:
        self.provider = provider
        self._credits_state = credits_state


def _credits_from_headers():
    from agent.credits_tracker import CreditsState

    # What a Nous response's x-nous-credits-* headers yield, with Andy's own numbers.
    return CreditsState(
        remaining_usd="14.06", subscription_usd="0.00", purchased_usd="14.06", from_header=True
    )


def test_the_balance_travels_as_the_lines_usage_prints():
    meta = _account_usage_meta(_Agent(credits_state=_credits_from_headers()))
    assert meta is not None, "the account was known and nothing travelled with the update"
    assert meta["provider"] == "nous"
    assert meta["stale"] is False
    assert "Top-up credits: $14.06" in meta["lines"], meta["lines"]
    # The snapshot builder is written for the dev fixture and says so in a tail line; a live account is
    # not a fixture, and a balance that arrives with a lie beside it is worse than no balance at all.
    assert not any("HERMES_DEV_CREDITS_FIXTURE" in line for line in meta["lines"]), meta["lines"]


def test_a_provider_with_no_account_to_show_says_nothing(monkeypatch):
    # Nothing is not zero: an account that could not be read must not arrive as a balance of nothing.
    monkeypatch.setattr("agent.account_usage_cache.cached_account_usage", lambda *a, **k: None)
    monkeypatch.setattr("agent.account_usage_cache.refresh_account_usage_async", lambda *a, **k: [])
    assert _account_usage_meta(_Agent(credits_state=None, provider="nous")) is None


def test_an_agent_with_no_provider_at_all_says_nothing():
    assert _account_usage_meta(_Agent(credits_state=None, provider="")) is None


def test_an_account_of_another_provider_is_not_sent(monkeypatch):
    # Andy works on one provider for days, and this process keeps the accounting of the last response it
    # saw - whoever made it. Nous numbers handed to a turn on opencode-go are a balance nobody there can
    # spend: nothing is said at all, and the editor shows its dash.
    from agent import credits_tracker

    monkeypatch.setattr("agent.account_usage_cache.cached_account_usage", lambda *a, **k: None)
    monkeypatch.setattr("agent.account_usage_cache.refresh_account_usage_async", lambda *a, **k: [])
    monkeypatch.setattr(credits_tracker, "_last_response_credits", _credits_from_headers())
    monkeypatch.setattr(credits_tracker, "_last_response_provider", "nous")
    assert _account_usage_meta(_Agent(credits_state=None, provider="opencode-go")) is None


def test_the_account_of_the_provider_in_front_travels_with_its_own_name(monkeypatch):
    from agent import credits_tracker

    monkeypatch.setattr(credits_tracker, "_last_response_credits", _credits_from_headers())
    monkeypatch.setattr(credits_tracker, "_last_response_provider", "nous")
    meta = _account_usage_meta(_Agent(credits_state=None, provider="nous"))
    assert meta is not None, "the account of the provider in front was not sent"
    assert meta["provider"] == "nous", meta
    assert "Top-up credits: $14.06" in meta["lines"], meta["lines"]
