from odoo import http
from odoo.http import request


class InternalTransferTicketController(http.Controller):

    @http.route(
        "/dt_gestion_reportes/internal_transfer/ticket/<int:picking_id>",
        type="http",
        auth="user",
        website=False,
    )
    def imprimir_internal_transfer_ticket(self, picking_id, **kwargs):
        picking = request.env["stock.picking"].browse(picking_id).exists()

        if not picking:
            return request.not_found()

        if picking.picking_type_code != "internal":
            return request.not_found()

        return request.render(
            "dt_gestion_reportes.internal_transfer_ticket_html",
            {
                "docs": picking,
                "company": picking.company_id,
            },
        )
