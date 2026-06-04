from odoo import http, fields
from odoo.http import request
from io import BytesIO
import xlsxwriter
from datetime import datetime


class PosOrderExcelController(http.Controller):

    def _selection_label(self, record, field_name):
        if field_name not in record._fields:
            return ""

        value = record[field_name]
        if not value:
            return ""

        selection = record._fields[field_name].selection

        if callable(selection):
            selection = selection(record.env)

        return dict(selection).get(value, value)

    @http.route(
        "/dt_gestion_reportes/pos_orders/excel",
        type="http",
        auth="user",
        website=False,
    )
    def export_pos_orders_excel(self, ids=None, **kwargs):
        if not ids:
            return request.not_found()

        order_ids = []
        for item in ids.split(","):
            if item.strip().isdigit():
                order_ids.append(int(item.strip()))

        orders = request.env["pos.order"].browse(order_ids).exists()

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Ordenes POS")

        title_format = workbook.add_format(
            {
                "bold": True,
                "font_size": 14,
                "align": "center",
                "valign": "vcenter",
            }
        )

        header_format = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#123B63",
                "font_color": "#FFFFFF",
                "border": 1,
                "align": "center",
                "valign": "vcenter",
            }
        )

        text_format = workbook.add_format(
            {
                "border": 1,
                "valign": "vcenter",
            }
        )

        money_format = workbook.add_format(
            {
                "border": 1,
                "num_format": "#,##0.00",
                "valign": "vcenter",
            }
        )

        total_format = workbook.add_format(
            {
                "bold": True,
                "border": 1,
                "num_format": "#,##0.00",
                "bg_color": "#F2F2F2",
            }
        )

        sheet.merge_range(
            "A1:K1", "REPORTE DE ÓRDENES POS PARA CONTABILIDAD", title_format
        )

        sheet.write("A2", "Generado:", text_format)
        sheet.write("B2", datetime.now().strftime("%d/%m/%Y %H:%M"), text_format)

        headers = [
            "Fecha",
            "Punto de venta",
            "Cliente",
            "Tipo",
            "Número Documento",
            "Estado SUNAT",
            "Empleado",
            "Medio de pago",
            "Subtotal",
            "IGV",
            "Total",
        ]

        row = 3
        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_format)

        total_subtotal = 0.0
        total_igv = 0.0
        total_general = 0.0

        row += 1

        for order in orders:
            fecha_texto = ""
            if order.date_order:
                fecha_local = fields.Datetime.context_timestamp(order, order.date_order)
                fecha_texto = fecha_local.strftime("%d/%m/%Y %H:%M")

            punto_venta = order.config_id.name or ""
            cliente = order.partner_id.name or "Cliente varios"

            tipo = ""
            if "tipo_documento_reporte" in order._fields:
                field_tipo = order._fields["tipo_documento_reporte"]

                if hasattr(field_tipo, "selection") and field_tipo.selection:
                    tipo = dict(field_tipo.selection).get(
                        order.tipo_documento_reporte, order.tipo_documento_reporte or ""
                    )
                else:
                    tipo = order.tipo_documento_reporte or ""

            numero_documento = ""
            if "sunat_document_number" in order._fields:
                numero_documento = order.sunat_document_number or ""

            estado_sunat = ""
            if "sunat_state" in order._fields:
                estado_sunat = order.sunat_state or ""

            empleado = order.user_id.name or ""

            medios_pago = []
            for payment in order.payment_ids:
                if payment.payment_method_id and payment.amount:
                    medios_pago.append(payment.payment_method_id.name)

            medio_pago = ", ".join(sorted(set(medios_pago)))

            igv = order.amount_tax if "amount_tax" in order._fields else 0.0
            total = order.amount_total or 0.0
            subtotal = total - igv

            total_subtotal += subtotal
            total_igv += igv
            total_general += total

            sheet.write(row, 0, fecha_texto, text_format)
            sheet.write(row, 1, punto_venta, text_format)
            sheet.write(row, 2, cliente, text_format)
            sheet.write(row, 3, tipo, text_format)
            sheet.write(row, 4, numero_documento, text_format)
            sheet.write(row, 5, estado_sunat, text_format)
            sheet.write(row, 6, empleado, text_format)
            sheet.write(row, 7, medio_pago, text_format)
            sheet.write_number(row, 8, subtotal, money_format)
            sheet.write_number(row, 9, igv, money_format)
            sheet.write_number(row, 10, total, money_format)

            row += 1

        sheet.write(row, 7, "TOTAL", header_format)
        sheet.write_number(row, 8, total_subtotal, total_format)
        sheet.write_number(row, 9, total_igv, total_format)
        sheet.write_number(row, 10, total_general, total_format)

        sheet.set_column("A:A", 18)
        sheet.set_column("B:B", 22)
        sheet.set_column("C:C", 28)
        sheet.set_column("D:D", 14)
        sheet.set_column("E:E", 20)
        sheet.set_column("F:F", 18)
        sheet.set_column("G:G", 20)
        sheet.set_column("H:H", 24)
        sheet.set_column("I:K", 13)

        sheet.autofilter(3, 0, row - 1, 10)
        sheet.freeze_panes(4, 0)

        workbook.close()
        output.seek(0)

        filename = "ordenes_pos_contabilidad.xlsx"

        return request.make_response(
            output.read(),
            headers=[
                (
                    "Content-Type",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
                ("Content-Disposition", f'attachment; filename="{filename}"'),
            ],
        )
