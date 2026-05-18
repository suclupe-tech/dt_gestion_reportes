from odoo import fields, models


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    dt_product_template_id = fields.Many2one(
        related="product_id.product_tmpl_id",
        string="Modelo",
        store=True,
        readonly=True,
    )

    dt_config_id = fields.Many2one(
        related="order_id.config_id",
        string="Punto de venta",
        store=True,
        readonly=True,
    )

    dt_attribute_values = fields.Char(
        string="Variantes",
        compute="_compute_dt_attribute_values",
        store=True,
    )

    dt_order_date = fields.Datetime(
        related="order_id.date_order",
        string="Fecha venta",
        store=True,
        readonly=True,
    )

    def _compute_dt_attribute_values(self):
        for line in self:
            values = line.product_id.product_template_attribute_value_ids.mapped("name")
            line.dt_attribute_values = ", ".join(values) if values else ""
