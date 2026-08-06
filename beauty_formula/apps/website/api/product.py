"""
Endpoints de Produto — CRUD de produtos da Barbearia/Salão.
"""
import uuid
from typing import Optional

from django_ratelimit.decorators import ratelimit
from ninja import File, Router, UploadedFile

from beauty_formula.apps.website.services.product_service import (
    create_product_for_admin,
    update_product_for_admin,
    delete_product_for_admin,
    deactivate_product_for_admin,
    activate_product_for_admin,
    list_all_public_products,
    list_all_private_products,
    detail_product,
)

from beauty_formula.apps.website.schemas.product_schema import (
    ProductCreateIn,
    ProductOut,
    ProductUpdateIn,
    ProductPrivateOut,
)

from beauty_formula.apps.core.exceptions.product_exception import ProductNotFound
from beauty_formula.apps.core.permissions.auth_classes import AdminOnlyAuth
from beauty_formula.apps.accounts.schemas.user_schema import MessageOut
from beauty_formula.apps.core.exceptions.permissions import PermissionDenied
from beauty_formula.apps.core.utils.pagination import paginate_queryset, PageOut

router = Router()


@router.get(
    "/list-public-products",
    response={
        200: PageOut[ProductOut],
        400: MessageOut,
    },
    auth=None,
    summary="Retorna todos os Produtos públicos",
)
@ratelimit(key="ip", rate="10/m", block=True)
def list_public_products_router(request, page: int = 1, page_size: int = 20):
    """
    Endpoint público para listar todos os produtos.
    """
    try:
        products_qs = list_all_public_products()
        result = paginate_queryset(products_qs, page, page_size, lambda product: product)
        return 200, result
    except PermissionDenied:
        return 403, {"detail": "Acesso negado"}
    except ProductNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/list-private-products",
    response={
        200: PageOut[ProductPrivateOut],
        400: MessageOut,
        403: MessageOut,
        404: MessageOut,
    },
    auth=AdminOnlyAuth(),
    summary="Retorna todos os Produtos privados",
)
@ratelimit(key="ip", rate="10/m", block=True)
def list_private_products_router(request, page: int = 1, page_size: int = 20):
    """
    Endpoint privado para listar todos os produtos (ativos e inativos).
    """
    try:
        products_qs = list_all_private_products()
        result = paginate_queryset(products_qs, page, page_size, lambda product: product)
        return 200, result
    except PermissionDenied:
        return 403, {"detail": "Acesso negado"}
    except ProductNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/detail-product/{product_id}",
    response={
        200: ProductOut,
        400: MessageOut,
        403: MessageOut,
        404: MessageOut,
    },
    auth=None,
    summary="Retorna um Produto específico pelo ID",
)
@ratelimit(key="ip", rate="10/m", block=True)
def detail_product_router(request, product_id: uuid.UUID):
    """
    Endpoint público para exibir detalhes de um produto.
    """
    try:
        product = detail_product(product_id=product_id)
        return 200, product
    except PermissionDenied:
        return 403, {"detail": "Acesso negado"}
    except ProductNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post(
    "/create-product",
    response={201: ProductOut, 400: MessageOut, 403: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Cria/Registra um produto da Barbearia/Salão",
)
@ratelimit(key="user", rate="30/m", block=True)
def create_product_router(request, payload: ProductCreateIn, image: Optional[UploadedFile] = File(None)):
    try:
        product = create_product_for_admin(payload, image=image)
        return 201, product
    except PermissionDenied:
        raise
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/update-product/{product_id}",
    response={200: ProductOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Atualiza um produto existente, apenas Admins podem acessar esse recurso",
)
@ratelimit(key="user", rate="30/m", block=True)
def update_product_router(request, product_id: uuid.UUID, payload: ProductUpdateIn):
    try:
        product = update_product_for_admin(product_id, payload)
        return 200, product
    except PermissionDenied:
        raise
    except ProductNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}



@router.delete(
    "/delete-product/{product_id}",
    response={200: None, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Deleta um produto existente, apenas Admins podem acessar esse recurso",
)
@ratelimit(key="user", rate="30/m", block=True)
def delete_product_router(request, product_id: uuid.UUID):
    try:
        delete_product_for_admin(product_id)
        return 200, {"detail": "Produto excluído com sucesso !!!"}
    except PermissionDenied:
        raise
    except ProductNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/deactivate-product/{product_id}",
    response={201: ProductOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Desativa produto (soft delete), apenas Admins podem acessar esse recurso",
)
@ratelimit(key="user", rate="30/m", block=True)
def deactivate_product_router(request, product_id: uuid.UUID):
    try:
        product = deactivate_product_for_admin(product_id)
        return 201, product
    except PermissionDenied:
        raise
    except ProductNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/activate-product/{product_id}",
    response={201: ProductOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Ativa produto, apenas Admins podem acessar esse recurso",
)
@ratelimit(key="user", rate="30/m", block=True)
def activate_product_router(request, product_id: uuid.UUID):
    try:
        product = activate_product_for_admin(product_id)
        return 201, product
    except PermissionDenied:
        raise
    except ProductNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}