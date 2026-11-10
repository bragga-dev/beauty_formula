"""Produtos da vitrine: leitura pública; escrita para admin ou gerente."""
import json
import uuid
from decimal import Decimal

import pytest

from beauty_formula.apps.conftest import image_file
from beauty_formula.apps.website.models.product_models import DEFAULT_PRODUCT_PHOTO, Product

pytestmark = pytest.mark.django_db


@pytest.fixture
def product(db):
    return Product.objects.create(name="Shampoo", description="Hidratante", price=Decimal("39.90"), stock=10)


@pytest.fixture
def inactive_product(db):
    return Product.objects.create(name="Máscara", price=Decimal("59.90"), stock=3, is_active=False)


def _create_payload(**extra):
    return {"payload": json.dumps({"name": "Condicionador", "description": "Suave", "price": "29.90", "stock": 5, **extra})}


# ── Leitura ─────────────────────────────────────────────────────────────────

def test_public_list_shows_only_active_products(api, product, inactive_product):
    r = api.get("/products/list-public-products")
    assert r.status_code == 200
    names = [i["name"] for i in r.json()["items"]]
    assert names == ["Shampoo"]


def test_private_list_shows_all_for_admin_and_manager(api, root_admin, manager_user, product, inactive_product):
    for user in (root_admin, manager_user):
        r = api.get("/products/list-private-products", user=user)
        assert r.status_code == 200 and r.json()["total"] == 2


@pytest.mark.parametrize("who", ["verified_client", "verified_employee"])
def test_private_list_forbidden_for_client_and_employee(api, request, who):
    assert api.get("/products/list-private-products", user=request.getfixturevalue(who)).status_code == 403


def test_private_list_requires_authentication(api):
    assert api.get("/products/list-private-products").status_code == 401


def test_detail_is_public(api, product):
    r = api.get(f"/products/detail-product/{product.id}")
    assert r.status_code == 200 and r.json()["name"] == "Shampoo"


def test_detail_unknown_is_404(api):
    assert api.get(f"/products/detail-product/{uuid.uuid4()}").status_code == 404


# ── Escrita ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("who", ["root_admin", "manager_user"])
def test_admin_and_manager_create_product(api, request, who):
    r = api.post_form("/products/create-product", _create_payload(), user=request.getfixturevalue(who))
    assert r.status_code == 201, r.content
    assert Product.objects.get(name="Condicionador").stock == 5


def test_create_product_with_image(api, root_admin):
    data = {**_create_payload(), "image": image_file()}
    r = api.post_form("/products/create-product", data, user=root_admin)
    assert r.status_code == 201, r.content
    assert Product.objects.get(name="Condicionador").image.name != DEFAULT_PRODUCT_PHOTO


@pytest.mark.xfail(strict=True, reason="product_service não chama validate_image_file: upload inválido é aceito")
def test_create_product_with_invalid_image_is_400(api, root_admin):
    from django.core.files.uploadedfile import SimpleUploadedFile
    bad = SimpleUploadedFile("x.png", b"nao-e-imagem", content_type="image/png")
    r = api.post_form("/products/create-product", {**_create_payload(), "image": bad}, user=root_admin)
    assert r.status_code == 400
    assert not Product.objects.filter(name="Condicionador").exists()


def test_create_duplicate_name_is_400(api, root_admin, product):
    r = api.post_form("/products/create-product", _create_payload(name="Shampoo"), user=root_admin)
    assert r.status_code == 400


def test_create_negative_stock_is_422(api, root_admin):
    r = api.post_form("/products/create-product", _create_payload(stock=-1), user=root_admin)
    assert r.status_code == 422


@pytest.mark.parametrize("who", ["verified_client", "verified_employee"])
def test_create_forbidden_for_client_and_employee(api, request, who):
    assert api.post_form("/products/create-product", _create_payload(), user=request.getfixturevalue(who)).status_code == 403


def test_update_product(api, root_admin, product):
    r = api.patch(f"/products/update-product/{product.id}", {"price": "45.00", "stock": 7}, user=root_admin)
    assert r.status_code == 200, r.content
    product.refresh_from_db()
    assert product.price == Decimal("45.00") and product.stock == 7 and product.name == "Shampoo"


def test_update_unknown_is_404(api, root_admin):
    assert api.patch(f"/products/update-product/{uuid.uuid4()}", {"stock": 1}, user=root_admin).status_code == 404


def test_update_image(api, manager_user, product):
    r = api.patch_form(f"/products/update-image-product/{product.id}", {"image": image_file()}, user=manager_user)
    assert r.status_code == 200, r.content
    product.refresh_from_db()
    assert product.image.name != DEFAULT_PRODUCT_PHOTO


def test_deactivate_and_activate(api, root_admin, product):
    assert api.patch(f"/products/deactivate-product/{product.id}", user=root_admin).status_code == 201
    product.refresh_from_db()
    assert product.is_active is False
    assert api.get("/products/list-public-products").json()["total"] == 0
    assert api.patch(f"/products/activate-product/{product.id}", user=root_admin).status_code == 201
    product.refresh_from_db()
    assert product.is_active is True


def test_delete_product(api, root_admin, product):
    assert api.delete(f"/products/delete-product/{product.id}", user=root_admin).status_code == 200
    assert not Product.objects.filter(id=product.id).exists()


def test_delete_unknown_is_404(api, root_admin):
    assert api.delete(f"/products/delete-product/{uuid.uuid4()}", user=root_admin).status_code == 404


def test_write_routes_forbidden_for_client(api, verified_client, product):
    assert api.patch(f"/products/update-product/{product.id}", {"stock": 1}, user=verified_client).status_code == 403
    assert api.delete(f"/products/delete-product/{product.id}", user=verified_client).status_code == 403
    assert api.patch(f"/products/deactivate-product/{product.id}", user=verified_client).status_code == 403