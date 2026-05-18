from odoo import models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def action_preview_stock_report(self):

        ids = ",".join(map(str, self.ids))

        return {
            "type": "ir.actions.act_url",
            "url": f"/report/pdf/dt_gestion_reportes.report_stock_quant_dt_template/{ids}",
            "target": "new",
        }

    def dt_location_label(self, location):
        if not location:
            return ""

        if location.usage == "customer":
            return "Cliente"
        if location.usage == "supplier":
            return "Proveedor"
        if location.usage == "inventory":
            return "Ajuste de Inventario"
        if location.usage == "production":
            return "Producción"
        if location.usage == "transit":
            return "Tránsito"

        warehouses = self.env["stock.warehouse"].sudo().search([])

        for warehouse in warehouses:
            view_location = warehouse.view_location_id

            if view_location and location.parent_path and view_location.parent_path:
                if location.parent_path.startswith(view_location.parent_path):
                    return warehouse.name

        return location.display_name
