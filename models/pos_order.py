from odoo import fields, models, api


class PosOrder(models.Model):
    _inherit = "pos.order"

    dt_tipo_documento = fields.Selection(
        related="tipo_documento_reporte",
        string="Tipo documento",
        store=True,
        readonly=True,
    )

    dt_payment_methods = fields.Char(
        string="Medio de pago",
        compute="_compute_dt_payment_methods",
        store=False,
    )

    dt_amount_untaxed = fields.Monetary(
        string="Subtotal",
        compute="_compute_dt_amounts",
        currency_field="currency_id",
        store=False,
    )

    dt_amount_tax = fields.Monetary(
        string="IGV",
        compute="_compute_dt_amounts",
        currency_field="currency_id",
        store=False,
    )

    @api.depends("payment_ids.payment_method_id", "payment_ids.amount")
    def _compute_dt_payment_methods(self):
        for order in self:
            methods = []

            for payment in order.payment_ids:
                if payment.payment_method_id and payment.amount:
                    methods.append(payment.payment_method_id.name)

            order.dt_payment_methods = (
                ", ".join(sorted(set(methods))) if methods else ""
            )

    @api.depends("amount_total", "amount_tax")
    def _compute_dt_amounts(self):
        for order in self:
            order.dt_amount_tax = order.amount_tax or 0.0
            order.dt_amount_untaxed = (order.amount_total or 0.0) - (
                order.amount_tax or 0.0
            )

    def action_export_excel_contabilidad_dt(self):
        ids = ",".join(str(order.id) for order in self)

        return {
            "type": "ir.actions.act_url",
            "url": "/dt_gestion_reportes/pos_orders/excel?ids=%s" % ids,
            "target": "self",
        }
