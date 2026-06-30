from ai.language import detect


def test_empty_or_none_defaults_to_english():
    assert detect("") == "en"
    assert detect(None) == "en"
    assert detect("   ") == "en"


def test_plain_english():
    assert detect("I want a margherita pizza") == "en"
    assert detect("hello there") == "en"
    assert detect("two thin crust please") == "en"


def test_devanagari_is_hindi():
    assert detect("मुझे पिज़्ज़ा चाहिए") == "hi"
    assert detect("order: मार्गरीटा") == "hi"  # mixed script -> Hindi


def test_hinglish_keywords_are_hindi():
    assert detect("mujhe ek pizza chahiye") == "hi"
    assert detect("kitna hai bhai") == "hi"
    assert detect("accha theek hai") == "hi"


def test_order_alone_does_not_flip_to_hindi():
    # "order" is English too; it must not tip detection by itself.
    assert detect("order one pizza") == "en"
