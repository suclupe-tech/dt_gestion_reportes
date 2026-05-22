from odoo import fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    dt_tipo_documento = fields.Selection(
        related="tipo_documento_reporte",
        string="Tipo documento",
        store=True,
        readonly=True,
    )
