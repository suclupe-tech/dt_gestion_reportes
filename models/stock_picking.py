from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def action_print_internal_transfer_dt(self):
        for picking in self:
            picking.printed = True

        return self.env.ref(
            "dt_gestion_reportes.action_internal_transfer_report"
        ).report_action(self)

    def action_open_internal_transfer_ticket_dt(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_url",
            "url": "/dt_gestion_reportes/internal_transfer/ticket/%s" % self.id,
            "target": "new",
        }
