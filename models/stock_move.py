from odoo import models


def _dt_get_location_label(record, location):
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

    warehouses = record.env["stock.warehouse"].sudo().search([])

    for warehouse in warehouses:
        view_location = warehouse.view_location_id

        if view_location and location.parent_path and view_location.parent_path:
            if location.parent_path.startswith(view_location.parent_path):
                return warehouse.name

    return location.display_name


class StockMove(models.Model):
    _inherit = "stock.move"

    def dt_location_label(self, location):
        return _dt_get_location_label(self, location)


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def dt_location_label(self, location):
        return _dt_get_location_label(self, location)
