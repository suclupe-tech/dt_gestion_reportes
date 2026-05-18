from odoo import models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def action_preview_stock_report(self):

        ids = ",".join(map(str, self.ids))

        return {
            'type': 'ir.actions.act_url',
            'url': f'/report/pdf/dt_gestion_reportes.report_stock_quant_dt_template/{ids}',
            'target': 'new',
        }