from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def action_imprimir_movimientos_ticket(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_url",
            "url": (
                "/dt_gestion_reportes/movimientos_prendas/ticket"
                "?session_id=%s" % self.id
            ),
            "target": "new",
        }

    def action_imprimir_movimientos_a4(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_url",
            "url": (
                "/dt_gestion_reportes/movimientos_prendas/a4" "?session_id=%s" % self.id
            ),
            "target": "new",
        }
