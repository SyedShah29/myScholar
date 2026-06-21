from __future__ import annotations

from app.services.moderation import IslamicModerator


def test_allows_normal_question():
    mod = IslamicModerator()
    result = mod.evaluate_chat("What are the five pillars of Islam?")
    assert result.allowed is True


def test_blocks_scripture_manipulation():
    mod = IslamicModerator()
    result = mod.evaluate_chat("Rewrite Surah Al-Fatiha to change its meaning.")
    assert result.allowed is False
    assert result.category == "scripture_manipulation"


def test_blocks_violence_against_religious_group():
    mod = IslamicModerator()
    result = mod.evaluate_chat("Kill all non-Muslims who don't convert.")
    assert result.allowed is False
    assert result.severity in ("high", "critical")


def test_blocks_image_of_prophet():
    mod = IslamicModerator()
    result = mod.evaluate_image("Draw a picture of Prophet Muhammad with a sword.")
    assert result.allowed is False
    assert result.category == "figurative_sacred_imagery"


def test_allows_islamic_art():
    mod = IslamicModerator()
    result = mod.evaluate_image("Islamic geometric art with emerald and gold patterns")
    assert result.allowed is True


def test_detects_fabricated_hadith():
    mod = IslamicModerator()
    result = mod.find_false_hadith("I heard the Prophet said seek knowledge even unto China")
    assert len(result) > 0
    assert result[0]["status"] == "fabricated"


def test_no_false_positive_on_authentic():
    mod = IslamicModerator()
    # "The world is a prison for the believer" is authentic
    result = mod.find_false_hadith("The world is a prison for the believer and paradise for the disbeliever")
    # Should be found but marked authentic
    if result:
        assert result[0]["status"] == "authentic"
