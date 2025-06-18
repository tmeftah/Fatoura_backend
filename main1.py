from fastapi import FastAPI, HTTPException
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
from pydantic import BaseModel
import jinja2
from datetime import datetime


def format_date(value, format="%d-%m-%Y"):
    """Custom filter for date formatting.  Handles string inputs."""
    date = datetime.strptime(value, "%Y-%m-%d")
    return date.strftime(format)


# Create a Jinja2 environment and add the filter
jinja_env = jinja2.Environment(
    extensions=[], trim_blocks=True, lstrip_blocks=True
)  # DocxTemplate defaults
jinja_env.filters["dateformat"] = format_date

app = FastAPI()


class InvoiceItem(BaseModel):
    name: str
    description: str
    quantity: int
    unit_price: float
    total: float


class InvoiceData(BaseModel):
    invoice_number: str = "INV-001"
    invoice_date: str = "2023-10-27"
    due_date: str = "2023-11-27"
    bill_to: str = "Client Name"
    bill_to_address: str = "Client Address"
    ship_to: str = "Shipping Name"
    ship_to_address: str = "Shipping Address"
    items: list[InvoiceItem]
    subtotal: float
    discount_percent: float = 0.0
    discount_amount: float = 0.0
    tax_amount: float
    timbre: float = 1.0
    total_amount: float
    notes: str = "Thank you for your business!"


invoice_template_path = "template.docx"  # Make sure this file exists
logo_template_path = "logo.png"  # Make sure this file exists


@app.post("/generate_invoice/")
async def generate_invoice(data: InvoiceData):
    try:
        doc = DocxTemplate(invoice_template_path)
        logo = InlineImage(doc, logo_template_path, width=Mm(40))

        context = data.model_dump()
        context["logo"] = logo
        doc.render(context, jinja_env)

        output_file_path = f"generated_invoice_{data.invoice_number}.docx"
        doc.save(output_file_path)

        return {
            "filename": output_file_path,
            "message": "Invoice generated successfully",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def read_root():
    return {"message": "FastAPI Invoice Generator (Fixed Template)"}
