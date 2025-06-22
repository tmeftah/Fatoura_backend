from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.invoice_generator import ProfessionalInvoice


# SQLAlchemy imports
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    Text,
    Boolean,
    UniqueConstraint,
)

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session, joinedload


SECRET_KEY = "J7sn8fg"  # Change this for production!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


app = FastAPI()

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = "sqlite:///./database/invoice_db.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# --- SQLAlchemy Models ---


class DBUser(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)


class DBProduct(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    unit_price = Column(Float, nullable=False)

    invoice_items = relationship("DBInvoiceItem", back_populates="product")


class DBInvoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, nullable=False)
    invoice_date = Column(String, nullable=False)
    due_date = Column(String, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    subtotal = Column(Float, nullable=False)
    discount_type = Column(String, default="percent")  # "percent" or "fixed"
    discount_value = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    tax_percent = Column(Float, nullable=False, default=0.0)
    tax_amount = Column(Float, nullable=False)
    timbre = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)

    customer = relationship("DBCustomer", back_populates="invoices")
    items = relationship(
        "DBInvoiceItem", back_populates="invoice", cascade="all, delete-orphan"
    )


class DBInvoiceItem(Base):
    __tablename__ = "invoice_items"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    description = Column(String, nullable=True)
    unit_price = Column(Float, nullable=True)
    quantity = Column(Integer, nullable=False)
    total = Column(Float, nullable=False)
    invoice = relationship("DBInvoice", back_populates="items")

    product = relationship("DBProduct", back_populates="invoice_items")


class DBSetting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=True)
    __table_args__ = (UniqueConstraint("key", name="unique_setting_key"),)


def create_default_settings():
    db = SessionLocal()

    settings = {
        "company_name": "comp-1",
        "company_address": "address of comp-1",
        "company_telephone": "00010011",
        "company_email": "email@email.email",
        "currency_symbol": "TND",
        "timbre_value": "1",
        "footer_text": """Powered by Tech Solutions Inc.
        www.techsolutions.come""",
    }

    for x, y in settings.items():
        db_setting = DBSetting(key=x, value=y)
        db.add(db_setting)
        try:
            db.commit()

            db.close()

        except Exception as e:
            db.rollback()


class DBCustomer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    invoices = relationship("DBInvoice", back_populates="customer")


def create_default_superuser():
    db = SessionLocal()
    username = "admin"
    email = "admin@tt.com"
    password = "admin"  # CHANGE THIS IN PRODUCTION

    existing = db.query(DBUser).filter(DBUser.username == username).first()
    if not existing:
        superuser = DBUser(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            is_active=True,
            is_superuser=True,
        )
        db.add(superuser)
        db.commit()
        print(f"Created default superuser: {username}/{password}")
    db.close()


Base.metadata.create_all(bind=engine)

create_default_superuser()
create_default_settings()
# --- Pydantic Models ---


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_superuser: bool

    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    unit_price: float


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    unit_price: Optional[float] = None


class Product(ProductBase):
    id: int

    class Config:
        from_attributes = True


class InvoiceItemBase(BaseModel):
    product_id: int
    description: Optional[str] = None
    unit_price: Optional[float] = None
    quantity: int


class InvoiceItemCreate(InvoiceItemBase):
    pass


class InvoiceItemUpdate(BaseModel):
    id: Optional[int] = Field(default=None)
    product_id: Optional[int] = Field(default=None)
    description: Optional[str] = Field(default=None)
    unit_price: Optional[float] = Field(default=None)
    quantity: Optional[int] = Field(default=None)


class InvoiceItem(InvoiceItemBase):
    id: int
    invoice_id: int
    product_id: int
    name: Optional[str] = None
    product: Product

    class Config:
        from_attributes = True


class InvoiceBase(BaseModel):
    invoice_number: str
    invoice_date: str
    due_date: str
    customer_id: int
    discount_type: str = "percent"  # "percent" or "fixed"
    discount_value: float = 0.0  # percentage value or fixed value
    discount_amount: float = 0.0
    timbre: float
    tax_percent: float
    tax_amount: float = 0.0
    subtotal: float = 0.0
    total_amount: float = 0.0
    notes: Optional[str] = None


class InvoiceCreate(InvoiceBase):
    items: List[InvoiceItemCreate]


class InvoiceUpdate(BaseModel):
    invoice_number: Optional[str] = Field(default=None)
    invoice_date: Optional[str] = Field(default=None)
    due_date: Optional[str] = Field(default=None)
    customer_id: Optional[int] = Field(default=None)
    discount_type: Optional[str] = Field(default=None)
    discount_value: Optional[float] = Field(default=None)
    discount_amount: Optional[float] = Field(default=None)
    tax_percent: Optional[float] = Field(default=None)
    tax_amount: Optional[float] = Field(default=None)
    timbre: Optional[float] = Field(default=None)
    subtotal: Optional[float] = Field(default=None)
    total_amount: Optional[float] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    items: Optional[List[InvoiceItemCreate]] = Field(default=None)


class CustomerBase(BaseModel):
    name: str
    address: str
    email: Optional[str] = None
    phone: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class Customer(CustomerBase):
    id: int

    class Config:
        from_attributes = True


class Invoice(InvoiceBase):
    id: int
    subtotal: float
    discount_amount: float
    tax_amount: float
    total_amount: float
    customer: Customer
    items: List[InvoiceItem]

    class Config:
        from_attributes = True


class SettingBase(BaseModel):
    key: str
    value: str


class SettingCreate(SettingBase):
    pass


class Setting(SettingBase):
    id: int

    class Config:
        from_attributes = True


class Settings(SettingBase):
    id: int

    class Config:
        from_attributes = True


# --- Dependency to get the database session ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_by_username(db: Session, username: str):
    return db.query(DBUser).filter(DBUser.username == username).first()


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    return user


@app.post("/register/", response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_username(db, user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(user.password)
    db_user = DBUser(
        username=user.username, email=user.email, hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/login/")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    # Only allow active accounts to log in!
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account not activated")

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.put("/users/{user_id}/activate")
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Only superusers can activate users"
        )
    user = db.query(DBUser).filter(DBUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    db.commit()
    return {"detail": "User activated."}


# Products endpoints (unchanged)


@app.post("/products/", response_model=Product)
async def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    db_product = DBProduct(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@app.get("/products/{product_id}", response_model=Product)
async def read_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    db_product = db.query(DBProduct).filter(DBProduct.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product


@app.get("/products/", response_model=List[Product])
async def list_products(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    return db.query(DBProduct).all()


@app.put("/products/{product_id}", response_model=Product)
async def update_product(
    product_id: int,
    product: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    db_product = db.query(DBProduct).filter(DBProduct.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    for field, value in product.model_dump(exclude_unset=True).items():
        setattr(db_product, field, value)
    db.commit()
    db.refresh(db_product)
    return db_product


@app.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    db_product = db.query(DBProduct).filter(DBProduct.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(db_product)
    db.commit()
    return {"message": "Product deleted successfully"}


# Customers endpoints (unchanged)
@app.post("/customers/", response_model=Customer)
async def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    db_customer = DBCustomer(**customer.model_dump())
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer


@app.get("/customers/{customer_id}", response_model=Customer)
async def read_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    db_customer = db.query(DBCustomer).filter(DBCustomer.id == customer_id).first()
    if db_customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return db_customer


@app.get("/customers/", response_model=List[Customer])
async def list_customers(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    return db.query(DBCustomer).all()


@app.put("/customers/{customer_id}", response_model=Customer)
async def update_customer(
    customer_id: int,
    customer: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    db_customer = db.query(DBCustomer).filter(DBCustomer.id == customer_id).first()
    if db_customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    for field, value in customer.model_dump(exclude_unset=True).items():
        setattr(db_customer, field, value)
    db.commit()
    db.refresh(db_customer)
    return db_customer


@app.delete("/customers/{customer_id}")
async def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    db_customer = db.query(DBCustomer).filter(DBCustomer.id == customer_id).first()
    if db_customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    db.delete(db_customer)
    db.commit()
    return {"message": "Customer deleted successfully"}


# Settings endpoints (unchanged)
@app.post("/settings/", response_model=Setting)
async def create_setting(
    setting: SettingCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    db_setting = DBSetting(**setting.model_dump())
    db.add(db_setting)
    try:
        db.commit()
        db.refresh(db_setting)
        return db_setting
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Key already exists")


@app.get("/settings/", response_model=List[Settings])
async def read_settings(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    db_settings = db.query(DBSetting).all()
    if db_settings is None:
        raise HTTPException(status_code=404, detail="Settings not found")
    return db_settings


@app.get("/settings/{key}", response_model=Setting)
async def read_setting(
    key: str,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    db_setting = db.query(DBSetting).filter(DBSetting.key == key).first()
    if db_setting is None:
        raise HTTPException(status_code=404, detail="Setting not found")
    return db_setting


@app.put("/settings/{key}", response_model=Setting)
async def update_setting(
    key: str,
    setting: SettingCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    db_setting = db.query(DBSetting).filter(DBSetting.key == key).first()
    if db_setting is None:
        raise HTTPException(status_code=404, detail="Setting not found")
    db_setting.value = setting.value
    db.commit()
    db.refresh(db_setting)
    return db_setting


# Invoices endpoints
@app.post("/invoices/", response_model=Invoice)
async def create_invoice(
    invoice_data: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    print(invoice_data)
    for item_data in invoice_data.items:
        product = (
            db.query(DBProduct).filter(DBProduct.id == item_data.product_id).first()
        )
        if not product:
            raise HTTPException(
                status_code=400,
                detail=f"Product with id {item_data.product_id} not found",
            )

    db_invoice = DBInvoice(
        invoice_number=invoice_data.invoice_number,
        invoice_date=invoice_data.invoice_date,
        due_date=invoice_data.due_date,
        customer_id=invoice_data.customer_id,
        subtotal=invoice_data.subtotal,
        discount_type=invoice_data.discount_type,
        discount_value=invoice_data.discount_value,
        discount_amount=invoice_data.discount_amount,
        tax_percent=invoice_data.tax_percent,
        tax_amount=invoice_data.tax_amount,
        timbre=invoice_data.timbre,
        total_amount=invoice_data.total_amount,
        notes=invoice_data.notes,
    )

    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)

    for item_data in invoice_data.items:
        product = (
            db.query(DBProduct).filter(DBProduct.id == item_data.product_id).first()
        )
        unit_price = (
            item_data.unit_price
            if item_data.unit_price is not None
            else product.unit_price
        )
        item_total = item_data.quantity * unit_price
        db_invoice_item = DBInvoiceItem(
            invoice_id=db_invoice.id,
            product_id=item_data.product_id,
            description=item_data.description,
            unit_price=unit_price,
            quantity=item_data.quantity,
            total=item_total,
        )
        db.add(db_invoice_item)
    db.commit()
    db.refresh(db_invoice)
    return db_invoice


@app.get("/invoices/{invoice_id}", response_model=Invoice)
async def read_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    db_invoice = (
        db.query(DBInvoice)
        .options(joinedload(DBInvoice.items).joinedload(DBInvoiceItem.product))
        .filter(DBInvoice.id == invoice_id)
        .first()
    )
    if db_invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice = Invoice.from_orm(db_invoice)
    invoice.items = [InvoiceItem.from_orm(item) for item in db_invoice.items]
    for i, item in enumerate(db_invoice.items):
        invoice.items[i].name = item.product.name if item.product else None
    return invoice


@app.get("/invoices/", response_model=List[Invoice])
async def list_invoices(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    invoices = (
        db.query(DBInvoice)
        .options(joinedload(DBInvoice.items).joinedload(DBInvoiceItem.product))
        .all()
    )
    invoice_list = []
    for db_invoice in invoices:
        invoice = Invoice.from_orm(db_invoice)
        invoice.items = [InvoiceItem.from_orm(item) for item in db_invoice.items]
        for i, item in enumerate(db_invoice.items):
            invoice.items[i].name = item.product.name if item.product else None
        invoice_list.append(invoice)
    return invoice_list


@app.put("/invoices/{invoice_id}", response_model=Invoice)
async def update_invoice(
    invoice_id: int,
    invoice: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    db_invoice = (
        db.query(DBInvoice)
        .options(joinedload(DBInvoice.items))
        .filter(DBInvoice.id == invoice_id)
        .first()
    )

    if db_invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    for field, value in invoice.model_dump(
        exclude={"items"}, exclude_unset=True
    ).items():
        setattr(db_invoice, field, value)

    if invoice.items is not None:
        for item in db_invoice.items:
            db.delete(item)
        db.commit()
        db_invoice.items.clear()

        for item_data in invoice.items:
            if item_data.product_id is None or item_data.quantity is None:
                raise HTTPException(
                    status_code=400,
                    detail="Product_id and quantity Cannot be None on create",
                )
            product = (
                db.query(DBProduct).filter(DBProduct.id == item_data.product_id).first()
            )
            if not product:
                raise HTTPException(
                    status_code=400,
                    detail=f"Product with id {item_data.product_id} not found",
                )
            unit_price = (
                item_data.unit_price
                if item_data.unit_price is not None
                else product.unit_price
            )
            item_total = item_data.quantity * unit_price
            db_invoice_item = DBInvoiceItem(
                invoice_id=db_invoice.id,
                product_id=item_data.product_id,
                description=item_data.description,
                unit_price=unit_price,
                quantity=item_data.quantity,
                total=item_total,
            )
            db.add(db_invoice_item)
            db_invoice.items.append(db_invoice_item)
    print("***", invoice.discount_amount)
    db_invoice.subtotal = invoice.subtotal
    db_invoice.discount_amount = invoice.discount_amount
    db_invoice.tax_amount = invoice.tax_amount
    db_invoice.total_amount = invoice.total_amount
    db.commit()
    db.refresh(db_invoice)
    return db_invoice


# --- Invoice Generation ---


@app.post("/generate_invoice/{invoice_id}")
async def generate_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
):
    try:
        db_invoice = db.query(DBInvoice).filter(DBInvoice.id == invoice_id).first()
        if not db_invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        company_name = (
            db.query(DBSetting).filter(DBSetting.key == "company_name").first().value
        )

        company_address = (
            db.query(DBSetting).filter(DBSetting.key == "company_address").first().value
        )

        company_telephone = (
            db.query(DBSetting)
            .filter(DBSetting.key == "company_telephone")
            .first()
            .value
        )
        company_email = (
            db.query(DBSetting).filter(DBSetting.key == "company_email").first().value
        )

        footer_text = (
            db.query(DBSetting).filter(DBSetting.key == "footer_text").first().value
        )

        invoice = Invoice.from_orm(db_invoice)
        company_data = {
            "name": company_name,
            "address": company_address,
            "phone": company_telephone,
            "email": company_email,
            "footer_text": footer_text,
        }

        file_name = f"{invoice.invoice_number}.pdf"

        invoice_generator = ProfessionalInvoice(
            file_name, "logo.png", invoice.model_dump(), company_data
        )

        invoice_generator.generate_invoice()

        return FileResponse(
            path=file_name,
            filename=file_name,  # Set the desired filename for the download
            media_type="octet-stream",  # Specify the correct MIME type
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def read_root():
    return {"message": "Invoice Generator V1.0"}
