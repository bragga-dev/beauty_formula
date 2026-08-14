import pytest
import uuid
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from beauty_formula.apps.accounts.models.client import Client
from beauty_formula.apps.core.constants.gender import Gender

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestClientModel:
    def test_client_creation(self, client_user):
        """Testa criação básica de um cliente"""
        client = Client.objects.create(
            user=client_user,
            first_name="João",
            last_name="Silva",
            username="joaosilva",
            gender=Gender.MALE,
            birth_date=date(1990, 1, 15)
        )
        
        assert client.id is not None
        assert isinstance(client.id, uuid.UUID)
        assert client.user == client_user
        assert client.first_name == "João"
        assert client.last_name == "Silva"
        assert client.username == "joaosilva"
        assert client.gender == Gender.MALE
        assert client.birth_date == date(1990, 1, 15)
        assert str(client) == "João Silva (test@example.com)"

    def test_client_str_method(self, client_user):
        """Testa o método __str__ do Client"""
        client = Client.objects.create(
            user=client_user,
            first_name="Maria",
            last_name="Santos"
        )
        assert str(client) == "Maria Santos (test@example.com)"

    def test_client_photo_url_with_default_photo(self, client_user, monkeypatch):
        """Testa photo_url quando não há foto personalizada"""
        client = Client.objects.create(user=client_user)
        
        # Mock CORRETO - função que aceita o parâmetro 'name'
        def mock_storage_url(name):  # ← CORRIGIDO: função recebe 'name', não 'self'
            return "/media/default/client_img.jpg"
        
        monkeypatch.setattr(client.photo.storage, 'url', mock_storage_url)
        
        url = client.photo_url
        assert url == "/media/default/client_img.jpg"

    def test_client_photo_url_with_custom_photo(self, client_user, monkeypatch):
        """Testa photo_url com foto personalizada"""
        client = Client.objects.create(
            user=client_user,
            photo=SimpleUploadedFile("photo.jpg", b"file_content", content_type="image/jpeg")
        )
        
        def mock_url(self):
            return "/media/photos/photo.jpg"
        
        monkeypatch.setattr(type(client.photo), 'url', property(mock_url))
        
        url = client.photo_url
        assert url == "/media/photos/photo.jpg"

    def test_client_photo_url_custom_photo_not_exists(self, client_user, monkeypatch):
        """Testa photo_url quando foto personalizada não existe no bucket"""
        client = Client.objects.create(
            user=client_user,
            photo=SimpleUploadedFile("photo.jpg", b"file_content", content_type="image/jpeg")
        )
        
        def mock_url_with_exception(self):
            raise Exception("File not found")
        
        # Mock CORRETO - função que aceita o parâmetro 'name'
        def mock_storage_url(name):  # ← CORRIGIDO: função recebe 'name', não 'self'
            return "/media/default/client_img.jpg"
        
        monkeypatch.setattr(type(client.photo), 'url', property(mock_url_with_exception))
        monkeypatch.setattr(client.photo.storage, 'url', mock_storage_url)
        
        url = client.photo_url
        assert url == "/media/default/client_img.jpg"

    def test_client_get_full_name(self, client_user):
        """Testa o método get_full_name"""
        client = Client.objects.create(
            user=client_user,
            first_name="João",
            last_name="Silva"
        )
        assert client.get_full_name() == "João Silva"
        
        client2 = Client.objects.create(
            user=User.objects.create_user(email="test2@example.com", password="pass123"),
            first_name="Maria"
        )
        assert client2.get_full_name() == "Maria"
        
        client3 = Client.objects.create(
            user=User.objects.create_user(email="test3@example.com", password="pass123"),
            last_name="Santos"
        )
        assert client3.get_full_name() == "Santos"
        
        client4 = Client.objects.create(
            user=User.objects.create_user(email="test4@example.com", password="pass123"),
            username="usuario123"
        )
        assert client4.get_full_name() == "usuario123"
        
        client5 = Client.objects.create(
            user=User.objects.create_user(email="test5@example.com", password="pass123")
        )
        assert client5.get_full_name().startswith("Client ")

    def test_client_normalize_phone(self):
        """Testa a normalização de telefone"""
        phone = Client.normalize_phone("11999998888")
        assert phone == "+5511999998888"
        
        phone2 = Client.normalize_phone("+5511999998888")
        assert phone2 == "+5511999998888"

    def test_client_clean_birth_date_future(self, client_user):
        """Testa validação de data de nascimento futura"""
        client = Client(
            user=client_user,
            birth_date=date.today() + timedelta(days=1)
        )
        
        with pytest.raises(ValidationError) as exc_info:
            client.clean()
        
        assert "birth_date" in exc_info.value.message_dict
        assert "Data de nascimento não pode ser no futuro" in str(exc_info.value.message_dict["birth_date"][0])

    def test_client_save_with_photo(self, client_user):
        """Testa o método save com foto"""
        client = Client(
            user=client_user,
            first_name="João",
            photo=SimpleUploadedFile("photo.jpg", b"file_content", content_type="image/jpeg")
        )
        client.save()
        
        assert client.photo.name != "default/client_img.jpg"
        assert client.photo.name.startswith("photos/")

    def test_client_save_without_photo(self, client_user):
        """Testa o método save sem foto - deve usar foto padrão"""
        client = Client(
            user=client_user,
            first_name="João",
            photo=None
        )
        client.save()
        
        assert client.photo.name == "default/client_img.jpg"

    def test_client_meta_options(self):
        """Testa as opções Meta do Client"""
        assert Client._meta.verbose_name == "Cliente"
        assert Client._meta.verbose_name_plural == "Clientes"
        assert Client._meta.ordering == ["first_name", "last_name"]
        assert len(Client._meta.indexes) == 1
        assert Client._meta.indexes[0].fields == ["first_name", "last_name"]