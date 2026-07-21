



from typing import TypeVar, Generic, List
from ninja import Schema

T = TypeVar("T")

class PageOut(Schema, Generic[T]):
    """Schema de resposta paginada."""
    items: List[T]
    total: int     
    page: int      
    page_size: int 
    pages: int     



