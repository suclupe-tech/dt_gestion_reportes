from odoo import http, fields
from odoo.http import request


class ReporteMovimientosPrendasController(http.Controller):

    @http.route(
        "/dt_gestion_reportes/movimientos_prendas/ticket",
        type="http",
        auth="user",
        website=False,
    )
    def imprimir_ticket(self, config_id=None, fecha=None, session_id=None, **kwargs):

        config = False
        fecha_reporte = False

        # Reimpresión desde una sesión POS
        if session_id:
            session = request.env["pos.session"].sudo().browse(int(session_id)).exists()

            if not session:
                return request.not_found()

            config = session.config_id

            if session.start_at:
                fecha_local = fields.Datetime.context_timestamp(
                    session,
                    session.start_at,
                )
                fecha_reporte = fecha_local.date()

        # Compatibilidad con el wizard anterior
        elif config_id and fecha:
            config = request.env["pos.config"].sudo().browse(int(config_id)).exists()

            if config:
                fecha_reporte = fields.Date.to_date(fecha)

        if not config or not fecha_reporte:
            return request.not_found()

        reporte = config.get_reporte_movimientos_prendas(fecha_reporte)

        return request.render(
            "dt_gestion_reportes.reporte_movimientos_prendas_ticket_backend",
            {
                "reporte": reporte,
            },
        )

    @http.route(
        "/dt_gestion_reportes/movimientos_prendas/a4",
        type="http",
        auth="user",
        website=False,
    )
    def imprimir_a4(self, session_id=None, **kwargs):

        if not session_id:
            return request.not_found()

        session = request.env["pos.session"].sudo().browse(int(session_id)).exists()

        if not session or not session.start_at:
            return request.not_found()

        config = session.config_id

        fecha_local = fields.Datetime.context_timestamp(
            session,
            session.start_at,
        )

        fecha_reporte = fecha_local.date()

        reporte = config.get_reporte_movimientos_prendas(fecha_reporte)

        return request.render(
            "dt_gestion_reportes.reporte_movimientos_prendas_a4",
            {
                "reporte": reporte,
                "session": session,
            },
        )
