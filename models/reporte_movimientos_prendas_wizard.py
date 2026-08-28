from odoo import models, fields


class ReporteMovimientosPrendasWizard(models.TransientModel):
    _name = "dt.reporte.movimientos.prendas.wizard"
    _description = "Reporte de Movimientos de Prendas"

    pos_config_id = fields.Many2one(
        "pos.config",
        string="Tienda",
        required=True,
    )

    fecha = fields.Date(
        string="Fecha",
        required=True,
        default=fields.Date.context_today,
    )

    def action_imprimir_ticket(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_url",
            "url": (
                "/dt_gestion_reportes/movimientos_prendas/ticket"
                "?config_id=%s&fecha=%s"
                % (
                    self.pos_config_id.id,
                    self.fecha.strftime("%Y-%m-%d"),
                )
            ),
            "target": "new",
        }
