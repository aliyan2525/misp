from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io


def generate_pdf_report(org_name: str, campaign_df, recommendations: list) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"Marketing Performance Report — {org_name}", styles["Title"]))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("Campaign Performance", styles["Heading2"]))

    if campaign_df is not None and not campaign_df.empty:
        table_data = [["Campaign", "Total Cost", "Conversions"]]
        for _, row in campaign_df.iterrows():
            table_data.append([
                str(row["name"]),
                f"${float(row['total_cost']):.2f}",
                str(int(row["total_conversions"]))
            ])

        table = Table(table_data)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("No campaign data available yet.", styles["Normal"]))

    elements.append(Spacer(1, 20))

    elements.append(Paragraph("Recommendations", styles["Heading2"]))
    if recommendations:
        for rec in recommendations:
            elements.append(Paragraph(
                f"• [{rec['priority'].upper()}] {rec['recommendation']}",
                styles["Normal"]
            ))
            elements.append(Spacer(1, 6))
    else:
        elements.append(Paragraph("No recommendations generated yet.", styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()