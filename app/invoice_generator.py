from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth
import datetime
import os
import re


class ProfessionalInvoice:
    MARGIN = 0.75 * inch
    HEADER_HEIGHT = 1.2 * inch
    FOOTER_HEIGHT = 1.5 * inch

    PRIMARY_COLOR = colors.HexColor("#2C3E50")
    ACCENT_COLOR = colors.HexColor("#3498DB")
    LIGHT_GRAY = colors.HexColor("#F8F9FA")
    BORDER_COLOR = colors.HexColor("#E9ECEF")

    def __init__(self, filename, logo_path, invoice_data, company_data):
        self.filename = filename
        self.logo_path = logo_path
        self.invoice_data = invoice_data
        self.company_data = company_data
        self.width, self.height = letter

        self.table_x0 = self.MARGIN
        self.table_x1 = self.width - self.MARGIN
        self.table_width = self.table_x1 - self.table_x0

        # Column percentages (description - 40%, qty - 12%, unit - 16%, amount - 16%)
        perc = [0.40, 0.12, 0.16, 0.16]
        desc_w = self.table_width * perc[0]
        qty_w = self.table_width * perc[1]
        unit_w = self.table_width * perc[2]
        amt_w = self.table_width * perc[3]

        self.col_desc = self.table_x0
        self.col_qty = self.col_desc + desc_w
        self.col_unit_price = self.col_qty + qty_w
        self.col_amount = self.col_unit_price + unit_w

        # For description wrapping
        self.desc_col_width = desc_w - 0.1 * inch

    def _calc_info_block_height(self, main_line, address, items=None):
        lines = 1  # main_line
        lines += len(address.split("\n"))
        if items:
            lines += len(items)
        return 0.3 * inch + lines * 0.15 * inch + 0.3 * inch

    def _split_description(self, text, max_width, fontname="Helvetica", fontsize=9):
        all_lines = []
        for physical_line in text.splitlines():
            physical_line = physical_line.replace("\t", "    ")
            match = re.match(r"^(\s*)", physical_line)
            indent = match.group(1) if match else ""
            words = physical_line.strip().split()
            line = indent
            for word in words:
                test = (line + " " + word) if line.strip() else indent + word
                if stringWidth(test, fontname, fontsize) <= max_width:
                    line = test
                else:
                    all_lines.append(line)
                    line = indent + word
            if line or physical_line.strip() == "":
                all_lines.append(line)
            elif not words:
                all_lines.append("")
        return all_lines

    def _draw_header(self, c, page_number, page_count):
        c.saveState()
        c.setFillColor(self.LIGHT_GRAY)
        c.rect(
            0,
            self.height - self.HEADER_HEIGHT,
            self.width,
            self.HEADER_HEIGHT,
            fill=1,
            stroke=0,
        )
        if page_number == 1 and self.logo_path and os.path.exists(self.logo_path):
            try:
                c.drawImage(
                    self.logo_path,
                    self.MARGIN,
                    self.height - self.HEADER_HEIGHT + 0.2 * inch,
                    width=2 * inch,
                    height=0.8 * inch,
                    mask="auto",
                    preserveAspectRatio=True,
                )
            except Exception as e:
                print(f"Logo error: {e}")

        c.setFillColor(self.PRIMARY_COLOR)
        c.setFont("Helvetica-Bold", 16)
        c.drawRightString(self.width - self.MARGIN, self.height - 0.4 * inch, "INVOICE")

        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.black)
        info_y = self.height - 0.6 * inch
        c.drawRightString(
            self.width - self.MARGIN,
            info_y,
            f"Invoice #: {self.invoice_data['invoice_number']}",
        )
        c.drawRightString(
            self.width - self.MARGIN,
            info_y - 0.15 * inch,
            f"Date: {self.invoice_data['invoice_date']}",
        )
        c.drawRightString(
            self.width - self.MARGIN,
            info_y - 0.3 * inch,
            f"Due: {self.invoice_data.get('due_date','')}",
        )
        c.setFont("Helvetica", 9)
        c.drawRightString(
            self.width - self.MARGIN,
            info_y - 0.45 * inch,
            f"Page {page_number}/{page_count}",
        )
        c.restoreState()

    def _draw_footer(self, c):
        c.saveState()
        footer_y = self.FOOTER_HEIGHT - 0.5 * inch
        c.setStrokeColor(self.BORDER_COLOR)
        c.setLineWidth(1)
        c.line(self.MARGIN, footer_y, self.width - self.MARGIN, footer_y)

        c.setFont("Helvetica", 7)
        c.setFillColor(colors.black)

        # Your desired multiline footer text:
        footer_text = (
            "Powered by Tech Solutions Inc.\n"
            "www.techsolutions.com\n"
            "Contact: info@techsolutions.com"
        )
        lines = footer_text.replace("\t", "    ").splitlines()

        y = footer_y - 0.3 * inch  # Adjust as needed for vertical position
        line_height = 0.16 * inch
        for line in lines:
            c.drawCentredString(self.width / 2, y, line)
            y -= line_height

        c.restoreState()

    def _draw_company_info(self, c, y_position):
        c.saveState()
        c.setFillColor(self.PRIMARY_COLOR)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(self.MARGIN, y_position, "FROM:")
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 11)
        y = y_position - 0.3 * inch
        c.drawString(self.MARGIN, y, self.company_data["name"])
        c.setFont("Helvetica", 10)
        y -= 0.2 * inch
        address_lines = self.company_data["address"].split("\n")
        for line in address_lines:
            c.drawString(self.MARGIN, y, line.strip())
            y -= 0.15 * inch
        c.drawString(self.MARGIN, y, f"Phone: {self.company_data['phone']}")
        y -= 0.15 * inch
        c.drawString(self.MARGIN, y, f"Email: {self.company_data['email']}")
        c.restoreState()

    def _draw_customer_info(self, c, y_position):
        cust = self.invoice_data["customer"]
        c.saveState()
        c.setFillColor(self.PRIMARY_COLOR)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(self.width / 2, y_position, "BILL TO:")
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 11)
        y = y_position - 0.3 * inch
        c.drawString(self.width / 2, y, cust["name"])
        c.setFont("Helvetica", 10)
        y -= 0.2 * inch
        address_lines = cust["address"].split("\n")
        for line in address_lines:
            c.drawString(self.width / 2, y, line.strip())
            y -= 0.15 * inch
        c.drawString(self.width / 2, y, f"Phone: {cust.get('phone', '')}")
        y -= 0.15 * inch
        c.drawString(self.width / 2, y, f"Email: {cust.get('email', '')}")
        c.restoreState()

    def _draw_table_header(self, c, y_position):
        c.saveState()
        header_height = 0.3 * inch
        c.setFillColor(self.PRIMARY_COLOR)
        c.rect(
            self.table_x0,
            y_position - header_height,
            self.table_width,
            header_height,
            fill=1,
            stroke=0,
        )
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        header_y = y_position - 0.2 * inch
        c.drawString(self.col_desc + 0.05 * inch, header_y, "DESCRIPTION")
        c.drawCentredString(
            self.col_qty + 0.05 * inch + (self.col_unit_price - self.col_qty) * 0.10,
            header_y,
            "QTY",
        )
        c.drawRightString(
            self.col_unit_price + (self.col_amount - self.col_unit_price) * 0.40,
            header_y,
            "UNIT PRICE",
        )
        c.drawRightString(self.col_amount + 0.15 * inch, header_y, "AMOUNT")
        c.restoreState()
        return y_position - header_height

    def _paginate_table_rows(self, y_position):
        items = self.invoice_data["items"]
        min_y = self.FOOTER_HEIGHT + inch
        pages = []
        current_y = y_position
        page_items = []
        i = 0
        while i < len(items):
            item = items[i]
            desc_lines = self._split_description(
                item["description"],
                self.desc_col_width,
                fontname="Helvetica",
                fontsize=9,
            )
            row_height = max(0.25 * inch, 0.18 * inch * len(desc_lines))
            if current_y - row_height < min_y and page_items:
                pages.append((y_position, page_items.copy()))
                page_items = []
                current_y = y_position
            page_items.append((item, desc_lines, row_height))
            current_y -= row_height
            i += 1
        if page_items:
            pages.append((y_position, page_items.copy()))
        return pages

    def _table_rows_drawer(self, c, page_y, items_desc_lines):
        y_position = page_y
        for i, (item, desc_lines, row_height) in enumerate(items_desc_lines):
            if i % 2 == 0:
                c.setFillColor(self.LIGHT_GRAY)
                c.rect(
                    self.table_x0,
                    y_position - row_height,
                    self.table_width,
                    row_height,
                    fill=1,
                    stroke=0,
                )
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 9)
            for j, line in enumerate(desc_lines):
                text_y = y_position - 0.15 * inch - j * 0.18 * inch
                c.drawString(self.col_desc + 0.05 * inch, text_y, line)
            cell_y = (
                y_position - row_height / 2 + 0.09 * inch * (len(desc_lines) - 1) / 2
            )
            c.drawCentredString(
                self.col_qty
                + 0.05 * inch
                + (self.col_unit_price - self.col_qty) * 0.10,
                cell_y,
                str(item["quantity"]),
            )
            c.drawRightString(
                self.col_unit_price + (self.col_amount - self.col_unit_price) * 0.40,
                cell_y,
                f"{item['unit_price']:.2f}",
            )
            amount = float(item["unit_price"]) * float(item["quantity"])
            c.drawRightString(self.col_amount + 0.15 * inch, cell_y, f"{amount:.2f}")
            y_position -= row_height
        c.setStrokeColor(self.BORDER_COLOR)
        c.setLineWidth(1)
        c.line(self.table_x0, y_position, self.table_x1, y_position)
        return y_position - 0.3 * inch

    def _draw_totals_section(self, c, y_position):
        c.saveState()
        box_width = 2.5 * inch
        box_height = 1.6 * inch
        box_x = self.width - self.MARGIN - box_width
        min_y = self.FOOTER_HEIGHT + inch
        if y_position - box_height < min_y:
            c.restoreState()
            return False, y_position

        c.setFillColor(self.LIGHT_GRAY)
        c.setStrokeColor(self.BORDER_COLOR)
        c.rect(box_x, y_position - box_height, box_width, box_height, fill=1, stroke=1)
        c.setFillColor(colors.black)
        y = y_position - 0.3 * inch
        c.setFont("Helvetica", 10)
        c.drawString(box_x + 0.2 * inch, y, "Subtotal:")
        c.drawRightString(
            box_x + box_width - 0.2 * inch, y, f"{self.invoice_data['subtotal']:.2f}"
        )
        y -= 0.2 * inch

        if self.invoice_data.get("discount_amount", 0):
            c.drawString(box_x + 0.2 * inch, y, "Discount:")
            c.drawRightString(
                box_x + box_width - 0.2 * inch,
                y,
                f"-{self.invoice_data['discount_amount']:.2f}",
            )
            y -= 0.2 * inch

        if self.invoice_data.get("timbre", 0):
            c.drawString(box_x + 0.2 * inch, y, "Timbre:")
            c.drawRightString(
                box_x + box_width - 0.2 * inch, y, f"{self.invoice_data['timbre']:.2f}"
            )
            y -= 0.2 * inch

        c.drawString(
            box_x + 0.2 * inch, y, f"Tax ({self.invoice_data['tax_percent']}%):"
        )
        c.drawRightString(
            box_x + box_width - 0.2 * inch, y, f"{self.invoice_data['tax_amount']:.2f}"
        )

        y -= 0.15 * inch
        c.setStrokeColor(self.PRIMARY_COLOR)
        c.setLineWidth(1)
        c.line(box_x + 0.1 * inch, y, box_x + box_width - 0.1 * inch, y)
        y -= 0.25 * inch
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(self.PRIMARY_COLOR)
        c.drawString(box_x + 0.2 * inch, y, "TOTAL:")
        c.drawRightString(
            box_x + box_width - 0.2 * inch,
            y,
            f"{self.invoice_data['total_amount']:.2f}",
        )
        c.restoreState()
        return True, y_position - box_height - 0.5 * inch

    def _draw_notes_section(self, c, y_position):
        c.saveState()
        notes = self.invoice_data.get("notes", "")
        if notes:
            # Normalize tabs to spaces
            notes = notes.replace("\t", "    ")
            notes_lines = notes.splitlines()
            c.setFont("Helvetica", 9)
            c.setFillColor(colors.black)
            note_y = y_position
            notes_label = "Notes: "
            max_width = self.width - 2 * self.MARGIN

            fontname, fontsize = "Helvetica", 9
            label_width = stringWidth(notes_label, fontname, fontsize)

            def wrap_line(line, is_first_paragraph_line):
                """
                Wrap a single line, put 'Notes: ' only on the very first physical/paragraph line.
                Subsequent lines (wrapped due to width) are not indented artificially.
                """
                out = []
                # Only the first physical line gets the label.
                prefix = notes_label if is_first_paragraph_line else ""
                effective_width = max_width if not prefix else (max_width - label_width)
                words = line.lstrip().split() if prefix else line.split()
                current = ""
                first = True
                while words:
                    word = words.pop(0)
                    sep = " " if current else ""
                    candidate = current + sep + word
                    width = stringWidth(candidate, fontname, fontsize)
                    if width > effective_width and current:
                        # Output current and start again with word
                        out.append(prefix + current)
                        current = word
                        prefix = ""
                        effective_width = max_width
                    else:
                        current = candidate
                # last line
                if current or not out:
                    out.append(prefix + current)
                return out

            is_first_physical_line = True
            for physical_line in notes_lines:
                wrapped_lines = wrap_line(physical_line, is_first_physical_line)
                for wrapped_line in wrapped_lines:
                    c.drawString(self.MARGIN, note_y, wrapped_line)
                    note_y -= 0.15 * inch
                is_first_physical_line = False
            y_position = note_y
        c.restoreState()
        return y_position

    def generate_invoice(self):
        company_h = self._calc_info_block_height(
            self.company_data["name"],
            self.company_data["address"],
            items=[
                self.company_data.get("phone", ""),
                self.company_data.get("email", ""),
            ],
        )
        cust = self.invoice_data["customer"]
        customer_h = self._calc_info_block_height(
            cust["name"],
            cust["address"],
            items=[cust.get("phone", ""), cust.get("email", "")],
        )
        block_h = max(company_h, customer_h)
        y_position = self.height - self.HEADER_HEIGHT - 0.5 * inch
        table_start_y = y_position - block_h - 0.5 * inch
        table_pages = self._paginate_table_rows(table_start_y)
        page_count = len(table_pages)
        dummy_canvas = canvas.Canvas(None, pagesize=letter)
        y_test = self._table_rows_drawer(
            dummy_canvas, table_pages[-1][0], table_pages[-1][1]
        )
        can_fit, notes_y_ct = self._draw_totals_section(dummy_canvas, y_test)
        if not can_fit:
            page_count += 1

        c = canvas.Canvas(self.filename, pagesize=letter)
        page_number = 1

        for pi, (page_y, items_desc_lines) in enumerate(table_pages):
            self._draw_header(c, page_number, page_count)
            self._draw_footer(c)
            y = y_position
            if page_number == 1:
                self._draw_company_info(c, y_position)
                self._draw_customer_info(c, y_position)
                rows_start_y = page_y
            else:
                rows_start_y = self.height - self.HEADER_HEIGHT - 0.5 * inch
                rows_start_y = self._draw_table_header(c, rows_start_y)
            if page_number == 1:
                rows_start_y = self._draw_table_header(c, rows_start_y)
            y_end = self._table_rows_drawer(c, rows_start_y, items_desc_lines)
            if pi == len(table_pages) - 1:
                success, notes_y = self._draw_totals_section(c, y_end)
                if success:
                    self._draw_notes_section(c, notes_y)
                else:
                    c.showPage()
                    page_number += 1
                    self._draw_header(c, page_number, page_count)
                    self._draw_footer(c)
                    y_totals = self.height - self.HEADER_HEIGHT - 0.5 * inch
                    success, notes_y = self._draw_totals_section(c, y_totals)
                    self._draw_notes_section(c, notes_y)
            if pi != len(table_pages) - 1:
                c.showPage()
                page_number += 1
        c.save()


if __name__ == "__main__":
    company_data = {
        "name": "Tech Solutions Inc.",
        "address": "456 Innovation Boulevard\nTech City, TX 75001\nUnited States",
        "phone": "+1 (555) 123-4567",
        "email": "billing@techsolutions.com",
    }

    invoice_data = {
        "invoice_number": "Facture-150625-01",
        "invoice_date": "2025-06-15",
        "due_date": "2025-06-27",
        "customer_id": 1,
        "discount_type": "amount",
        "discount_value": 4,
        "discount_amount": 4,
        "timbre": 1,
        "tax_percent": 19,
        "tax_amount": 160.74,
        "subtotal": 846,
        "total_amount": 1007.74,
        "notes": "dsf\tNote1\nLine2\tLine2b\n\tIndented line.\n\nA New Para.",
        "id": 1,
        "customer": {
            "name": "c1",
            "address": "Rue 14 Kihng\n4458945 Tunsie\nDjerba",
            "email": "c.com@com.com",
            "phone": "(216) 225 - 2255",
            "id": 1,
        },
        "items": [
            {
                "product_id": 1,
                "description": "p1 desc",
                "unit_price": 100,
                "quantity": 2,
                "id": 5,
                "invoice_id": 1,
                "name": None,
                "product": {
                    "name": "p1",
                    "description": "p1 desc",
                    "unit_price": 150,
                    "id": 1,
                },
            },
            {
                "product_id": 2,
                "description": "com -21",
                "unit_price": 200,
                "quantity": 1,
                "id": 6,
                "invoice_id": 1,
                "name": None,
                "product": {
                    "name": "p2",
                    "description": "com",
                    "unit_price": 200,
                    "id": 2,
                },
            },
            {
                "product_id": 1,
                "description": "p1 desc  sxfbv",
                "unit_price": 150,
                "quantity": 3,
                "id": 7,
                "invoice_id": 1,
                "name": None,
                "product": {
                    "name": "p1",
                    "description": "p1 desc",
                    "unit_price": 150,
                    "id": 1,
                },
            },
        ],
    }

    try:
        invoice_generator = ProfessionalInvoice(
            "professional_invoice.pdf", "logo.png", invoice_data, company_data
        )
        invoice_generator.generate_invoice()
        print("✅ Professional invoice generated successfully!")
        print("📄 Check 'professional_invoice.pdf' in your current directory.")
    except Exception as e:
        print(f"❌ Error generating invoice: {e}")
