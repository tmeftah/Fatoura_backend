from datetime import datetime
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
import jinja2


tpl = DocxTemplate("template.docx")
logo = InlineImage(tpl, "logo.png", width=Mm(30))

YEAR = (
    2023  # this is just a dummy variable to showcase that variables can be used as well
)

l = []
for i in range(40):
    l.append(
        {
            "name": "month_1",
            "sales": """Page number python-docxStack Overflow4 Antworten·

vor 9 JahrenI am trying to create a program in python that can find a specific word in a .docx file and return page number that it occurred on.4 Antworten·  Top-Antwort: Short answer is no, because the page breaks are inserted by the rendering engine, not determined ...java - Is there a way to keep track of the current page number
14. Feb. 2022java - How can we get the current page number and line ...13. Feb. 2023Weitere Ergebnisse von stackoverflow.com""",
            "perc_profit": f"perc_{i}",
        }
    )

context = {
    "logo": logo,
    "invoice_date": datetime.now().strftime(format="%B %d, %Y"),
    "invoice_number": "REP2023",
    "current_year": YEAR,
    "previous_year": YEAR - 1,
    "current_year_total_sales": 150000,
    "previous_year_total_sales": 120000,
    "change_in_sales": "increase",
    "percentage_change": 25,
    "current_year_profit": 19500,
    "previous_year_profit": 10800,
    "footer_text": "Tags can be used in headers/footers as well.",
    "framework1": l,
}

jinja_env = jinja2.Environment(autoescape=True)
tpl.render(context, jinja_env)
tpl.save("doc.docx")
