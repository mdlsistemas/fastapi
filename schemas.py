from pydantic import BaseModel, EmailStr
from typing import Optional
from decimal import Decimal
from datetime import datetime
import enum

# ----------- USUARIOS -----------
class UserRole(str, enum.Enum):
    administrador = "administrador"
    operador = "operador"
    analista = "analista"

class UsuarioCreate(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    rol: UserRole
    foto: Optional[str] = None

class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str

class UsuarioOut(BaseModel):
    id: int
    nombre: str
    email: EmailStr
    rol: UserRole
    foto: Optional[str] = None
    class Config:
        orm_mode = True

# ----------- PRODUCTOS -----------
class ProductoBase(BaseModel):
    product_name: str
    sku: Optional[str] = ""
    unit_of_measure: Optional[str] = ""
    cost: Optional[Decimal] = 0
    sale_price: Optional[Decimal] = 0
    category: Optional[str] = ""
    location: Optional[str] = ""
    active: Optional[str] = "Yes"
    foto: Optional[str] = None

class ProductoCreate(ProductoBase):
    pass

class ProductoOut(ProductoBase):
    product_id: str
    class Config:
        orm_mode = True

# ----------- MOVIMIENTOS DE STOCK -----------
class MovimientoCreate(BaseModel):
    product_id: str
    movement_type: str   # "Ingreso" o "Egreso"
    quantity: int
    notes: Optional[str] = ""
    order_id: Optional[str] = None   # Opcional

class MovimientoOut(BaseModel):
    movement_id: str
    date: datetime
    product_id: str
    movement_type: str
    quantity: int
    notes: Optional[str] = ""
    order_id: Optional[str] = None

    class Config:
        orm_mode = True
