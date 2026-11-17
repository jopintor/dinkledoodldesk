import pytest

from app.guardrails.pii import luhn_ok, redact

# Values that must never change.
PROTECTED = ["KB-003", "DD-000125", "0x51", "it-help@picklehub.example"]


def test_protected_values_are_never_changed():
    text = "See KB-003 and ticket DD-000125, error 0x51. Email it-help@picklehub.example"
    clean, found = redact(text)
    assert clean == text
    assert found == []


@pytest.mark.parametrize("value", PROTECTED)
def test_each_protected_value_alone(value):
    assert redact(value) == (value, [])


# ---- PH mobile ----
@pytest.mark.parametrize(
    "number",
    ["09171234567", "0917 123 4567", "0917-123-4567", "+639171234567", "+63 917 123 4567"],
)
def test_mobile_is_hidden(number):
    clean, found = redact(f"Call me at {number} please")
    assert clean == "Call me at [PH_MOBILE] please"
    assert found == ["PH_MOBILE"]


@pytest.mark.parametrize("text", ["ref 12345678901", "dial 0917123", "port 8080"])
def test_mobile_lookalikes_are_kept(text):
    assert redact(text) == (text, [])


# ---- Landline ----
@pytest.mark.parametrize(
    "number", ["(02) 8123 4567", "02-8123-4567", "(046) 123 4567", "046 123-4567"]
)
def test_landline_is_hidden(number):
    clean, found = redact(f"Office line: {number}.")
    assert clean == "Office line: [PH_LANDLINE]."
    assert found == ["PH_LANDLINE"]


@pytest.mark.parametrize("text", ["Room 12 on floor 3", "build 2026-11-04", "port 8080 is open"])
def test_landline_lookalikes_are_kept(text):
    assert redact(text) == (text, [])


# ---- Email ----
def test_personal_email_is_hidden():
    clean, found = redact("Reach me at juan.delacruz@gmail.com today")
    assert clean == "Reach me at [EMAIL] today"
    assert found == ["EMAIL"]


def test_official_email_is_kept():
    text = "Write to it-help@picklehub.example for help"
    assert redact(text) == (text, [])


# ---- Card (Luhn) ----
@pytest.mark.parametrize("card", ["4111111111111111", "4111 1111 1111 1111", "4111-1111-1111-1111"])
def test_valid_card_is_hidden(card):
    clean, found = redact(f"My card is {card}.")
    assert clean == "My card is [CARD]."
    assert found == ["CARD"]


@pytest.mark.parametrize("text", ["4111 1111 1111 1112", "1234567890123456"])
def test_number_failing_luhn_is_kept(text):
    assert redact(text) == (text, [])


def test_luhn_helper():
    assert luhn_ok("4111111111111111")
    assert not luhn_ok("4111111111111112")


# ---- Government IDs ----
@pytest.mark.parametrize(
    "gov_id",
    [
        "34-1234567-8",  # SSS
        "123-456-789",  # TIN
        "123-456-789-000",  # TIN with branch code
        "12-345678901-2",  # PhilHealth
        "0028-1234567-3",  # UMID / CRN
        "N01-23-456789",  # driver's license
        "P1234567A",  # passport
    ],
)
def test_gov_id_is_hidden(gov_id):
    clean, found = redact(f"My ID is {gov_id}.")
    assert clean == "My ID is [GOV_ID]."
    assert found == ["GOV_ID"]


@pytest.mark.parametrize("text", ["ticket DD-000125", "article KB-003", "date 2026-11-04"])
def test_gov_id_lookalikes_are_kept(text):
    assert redact(text) == (text, [])


# ---- Password and PIN ----
def test_password_is_hidden():
    clean, found = redact("my password is hunter2, please log me in")
    assert clean == "my password is [PASSWORD], please log me in"
    assert found == ["PASSWORD"]


def test_password_with_symbols_and_end_punctuation():
    clean, found = redact("My Password: P@ss!w0rd.")
    assert clean == "My Password: [PASSWORD]."
    assert found == ["PASSWORD"]


def test_pin_is_hidden():
    clean, found = redact("my PIN is 4821")
    assert clean == "my PIN is [PIN]"
    assert found == ["PIN"]


@pytest.mark.parametrize(
    "text",
    ["I forgot my password, how do I reset it?", "Reset the PIN for the door", "pin the message"],
)
def test_password_and_pin_lookalikes_are_kept(text):
    assert redact(text) == (text, [])


# ---- Mixed ----
def test_several_types_at_once():
    clean, found = redact(
        "I'm Juan, 09171234567, juan@gmail.com, my password is abc123 and card 4111 1111 1111 1111"
    )
    assert "[PH_MOBILE]" in clean and "[EMAIL]" in clean
    assert "[PASSWORD]" in clean and "[CARD]" in clean
    assert set(found) == {"PH_MOBILE", "EMAIL", "PASSWORD", "CARD"}
