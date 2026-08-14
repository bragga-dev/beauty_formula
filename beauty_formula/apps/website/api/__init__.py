from beauty_formula.apps.website.api.contact import (
    create_contact_router,
    update_contact_status_router,
    delete_contact_router,
    list_contacts_router,
    detail_contact_router,
    
)
from beauty_formula.apps.website.api.product import (
    create_product_router,
    deactivate_product_router,
    update_product_router,
    update_image_product_router,
    activate_product_router,
    detail_product_router,
    delete_product_router,
    list_private_products_router,
    list_public_products_router,
    
)


__all__ = [

    "create_contact_router",
    "update_contact_status_router",
    "delete_contact_router",
    "list_contacts_router",
    "detail_contact_router",

    "create_product_router",
    "deactivate_product_router",
    "update_product_router",
    "update_image_product_router",
    "activate_product_router",
    "detail_product_router",
    "delete_product_router",
    "list_private_products_router",
    "list_public_products_router",

]