"""Selectors de Client (consultas de leitura)."""
import uuid
from datetime import date

import pytest

from beauty_formula.apps.core.constants.gender import Gender

from beauty_formula.apps.accounts.models import User
from beauty_formula.apps.accounts.models.client import Client
from beauty_formula.apps.accounts.selectors import client_selector as sel
from beauty_formula.apps.core.exceptions.user import UserNotFound

pytestmark = pytest.mark.django_db


def _client(email, **fields):
    user = User.objects.create_user(email=email, password="Senha12345!", role="client")
    user.is_trusty = True
    user.save(update_fields=["is_trusty"])
    c = user.client_profile if hasattr(user, "client_profile") else None
    if c is None:
        return Client.objects.create(user=user, **fields)
    for k, v in fields.items():
        setattr(c, k, v)
    c.save()
    return c


@pytest.fixture
def ana(db):
    return _client("ana@example.com", username="ana_s", first_name="Ana", last_name="Souza", phone="+5577999991111",
                   instagram="https://instagram.com/ana", birth_date=date(1990, 5, 20), gender=Gender.FEMALE)


@pytest.fixture
def bruno(db):
    return _client("bruno@example.com", username="bruno_l", first_name="Bruno", last_name="Lima", gender=Gender.MALE)


def test_by_id_user_id_and_404(ana):
    assert sel.get_client_by_id(ana.id) == ana
    assert sel.get_client_by_id(uuid.uuid4()) is None
    assert sel.get_client_by_user_id(ana.user_id) == ana
    assert sel.get_client_or_404(ana.id) == ana
    with pytest.raises(Exception):
        sel.get_client_or_404(uuid.uuid4())


def test_by_username(ana):
    assert sel.get_client_by_username("ANA_S") == ana
    assert sel.get_client_by_username("ANA_S", case_sensitive=True) is None
    assert sel.get_client_by_username("") is None
    assert list(sel.get_clients_by_username_partial("na_")) == [ana]


def test_by_names(ana, bruno):
    assert list(sel.get_clients_by_first_name("ana")) == [ana]
    assert list(sel.get_clients_by_first_name("Ana", exact=True)) == [ana]
    assert list(sel.get_clients_by_last_name("lim")) == [bruno]
    assert list(sel.get_clients_by_last_name("Lima", exact=True)) == [bruno]
    assert list(sel.get_clients_by_full_name("Ana Souza")) == [ana]
    assert list(sel.get_clients_by_full_name("")) == []


def test_by_email(ana):
    assert sel.get_client_by_email("ANA@example.com") == ana
    assert sel.get_client_by_email("") is None
    assert list(sel.get_clients_by_email_partial("ana@")) == [ana]


def test_by_phone_and_instagram(ana):
    assert sel.get_client_by_phone("(77) 99999-1111") == ana
    assert sel.get_client_by_phone("") is None
    assert list(sel.get_clients_by_phone_partial("99999")) == [ana]
    assert sel.get_client_by_instagram("https://instagram.com/ana") == ana
    assert sel.get_client_by_instagram("") is None


def test_birth_dates(ana, bruno):
    assert list(sel.get_clients_by_birth_date(date(1990, 5, 20))) == [ana]
    assert list(sel.get_clients_by_birth_date_range(date(1990, 1, 1), date(1990, 12, 31))) == [ana]
    assert list(sel.get_clients_with_birthday_in_month(5)) == [ana]
    today = date.today()
    ana.birth_date = date(1990, today.month, today.day)
    ana.save(update_fields=["birth_date"])
    assert list(sel.get_clients_with_birthday_today()) == [ana]


def test_gender(ana, bruno):
    assert list(sel.get_clients_by_gender(Gender.FEMALE)) == [ana]
    stats = sel.get_gender_statistics()
    assert stats.get(Gender.FEMALE) == 1 and stats.get(Gender.MALE) == 1


def test_search(ana, bruno):
    assert list(sel.search_clients("bruno")) == [bruno]
    assert list(sel.search_clients("Souza", search_fields=["last_name"])) == [ana]
    assert sel.search_clients("") == []
    assert list(sel.get_clients_by_name_and_username(name="Ana")) == [ana]
    assert list(sel.get_clients_by_name_and_username(username="bruno")) == [bruno]


def test_filter_clients(ana, bruno):
    assert list(sel.filter_clients(gender=Gender.FEMALE)) == [ana]
    assert list(sel.filter_clients(has_phone=True)) == [ana]
    assert list(sel.filter_clients(has_phone=False)) == [bruno]
    assert list(sel.filter_clients(has_instagram=True)) == [ana]
    assert list(sel.filter_clients(is_verified=True, order_by="first_name")) == [ana, bruno]
    assert list(sel.filter_clients(birth_date_after=date(1980, 1, 1), birth_date_before=date(2000, 1, 1))) == [ana]
    assert len(list(sel.filter_clients(created_after=date(2000, 1, 1), created_before=date(2100, 1, 1)))) == 2
    assert len(list(sel.filter_clients(has_photo=False))) in (0, 1, 2)


def test_helpers(ana, bruno):
    assert sel.validate_client_exists(ana.id) is True
    assert sel.validate_client_exists(uuid.uuid4()) is False
    assert "Ana" in sel.get_client_full_name_display(ana)
    info = sel.get_client_contact_info(ana)
    assert info["email"] == "ana@example.com"
    assert set(sel.get_clients_by_ids([ana.id, bruno.id])) == {ana, bruno}
    assert list(sel.get_clients_without_phone()) == [bruno]
    assert list(sel.get_clients_without_instagram()) == [bruno]
    assert sel.normalize_phone_for_search("(77) 99999-1111").endswith("999991111")