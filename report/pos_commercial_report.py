from collections import defaultdict
from odoo import models


class ReportPosCommercialDT(models.AbstractModel):
    _name = "report.dt_gestion_reportes.report_pos_commercial_template"
    _description = "Reporte Comercial Textil DT"

    def _get_report_values(self, docids, data=None):
        docs = self.env["pos.order.line"].browse(docids)

        product_qty = defaultdict(float)
        variant_qty = defaultdict(float)
        store_amount = defaultdict(float)

        for line in docs:
            product_name = (
                line.dt_product_template_id.name or line.product_id.display_name
            )
            variant_name = line.dt_attribute_values or "Sin variante"
            store_name = line.dt_config_id.name or "Sin tienda"

            product_qty[product_name] += line.qty
            variant_qty[variant_name] += line.qty
            store_amount[store_name] += line.price_subtotal_incl

        top_product = max(product_qty, key=product_qty.get) if product_qty else ""
        top_variant = max(variant_qty, key=variant_qty.get) if variant_qty else ""
        top_store = max(store_amount, key=store_amount.get) if store_amount else ""

        return {
            "doc_ids": docids,
            "doc_model": "pos.order.line",
            "docs": docs,
            "top_product": top_product,
            "top_variant": top_variant,
            "top_store": top_store,
        }
