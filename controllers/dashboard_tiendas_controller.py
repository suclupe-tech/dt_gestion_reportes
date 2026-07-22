from odoo import http, fields
from odoo.http import request
from datetime import datetime, time
import pytz


class DashboardTiendasController(http.Controller):

    @http.route("/dt_gestion_reportes/dashboard_tiendas/data", type="json", auth="user")
    def get_dashboard_data(self, date_from=None, date_to=None, pos_config_id=None):
        PosOrder = request.env["pos.order"].sudo()
        PosConfig = request.env["pos.config"].sudo()

        # Fecha de hoy según zona horaria del usuario
        user_tz = pytz.timezone(request.env.user.tz or "America/Lima")

        if date_from:
            date_from_obj = fields.Date.from_string(date_from)
        else:
            date_from_obj = fields.Date.context_today(request.env.user)

        if date_to:
            date_to_obj = fields.Date.from_string(date_to)
        else:
            date_to_obj = date_from_obj

        start_local = user_tz.localize(datetime.combine(date_from_obj, time.min))
        end_local = user_tz.localize(datetime.combine(date_to_obj, time.max))

        start_utc = start_local.astimezone(pytz.UTC).replace(tzinfo=None)
        end_utc = end_local.astimezone(pytz.UTC).replace(tzinfo=None)

        domain_hoy = [
            ("date_order", ">=", fields.Datetime.to_string(start_utc)),
            ("date_order", "<=", fields.Datetime.to_string(end_utc)),
            ("state", "in", ["paid", "done", "invoiced"]),
        ]

        if "venta_anulada" in PosOrder._fields:
            domain_hoy.append(("venta_anulada", "=", False))

        if "es_reversa_anulacion" in PosOrder._fields:
            domain_hoy.append(("es_reversa_anulacion", "=", False))

        if pos_config_id:
            domain_hoy.append(("config_id", "=", int(pos_config_id)))

        orders_hoy = PosOrder.search(domain_hoy)

        ventas_hoy = sum(orders_hoy.mapped("amount_total"))
        ordenes_hoy = len(orders_hoy)
        ticket_promedio = ventas_hoy / ordenes_hoy if ordenes_hoy else 0

        ventas_por_tienda_dict = {}

        for order in orders_hoy:
            tienda = order.config_id.name if order.config_id else "Sin tienda"

            if tienda not in ventas_por_tienda_dict:
                ventas_por_tienda_dict[tienda] = {
                    "tienda": tienda,
                    "ordenes": 0,
                    "ventas": 0.0,
                }

            ventas_por_tienda_dict[tienda]["ordenes"] += 1
            ventas_por_tienda_dict[tienda]["ventas"] += order.amount_total

        ventas_por_tienda = list(ventas_por_tienda_dict.values())

        ventas_por_tienda = sorted(
            ventas_por_tienda, key=lambda x: x["ventas"], reverse=True
        )

        ventas_por_medio_dict = {}

        for order in orders_hoy:
            for payment in order.payment_ids:
                medio = (
                    payment.payment_method_id.name
                    if payment.payment_method_id
                    else "Sin medio"
                )

                if medio not in ventas_por_medio_dict:
                    ventas_por_medio_dict[medio] = {
                        "medio": medio,
                        "cantidad": 0,
                        "monto": 0.0,
                    }

                ventas_por_medio_dict[medio]["cantidad"] += 1
                ventas_por_medio_dict[medio]["monto"] += payment.amount

        ventas_por_medio = list(ventas_por_medio_dict.values())

        ventas_por_medio = sorted(
            ventas_por_medio, key=lambda x: x["monto"], reverse=True
        )

        ventas_por_documento_dict = {}

        for order in orders_hoy:
            tipo = False

            if "tipo_documento_reporte" in PosOrder._fields:
                tipo = order.tipo_documento_reporte

            if not tipo and "sunat_document_type" in PosOrder._fields:
                if order.sunat_document_type == "01":
                    tipo = "Factura"
                elif order.sunat_document_type == "03":
                    tipo = "Boleta"
                elif order.sunat_document_type == "00":
                    tipo = "Nota de venta"
                else:
                    tipo = order.sunat_document_type or "Sin documento"

            if not tipo:
                tipo = "Sin documento"

            nombres_documento = {
                "nota_venta": "Nota de venta",
                "factura": "Factura",
                "boleta": "Boleta",
                "01": "Factura",
                "03": "Boleta",
                "00": "Nota de venta",
            }

            tipo = nombres_documento.get(tipo, tipo)

            if tipo not in ventas_por_documento_dict:
                ventas_por_documento_dict[tipo] = {
                    "tipo": tipo,
                    "ordenes": 0,
                    "monto": 0.0,
                }

            ventas_por_documento_dict[tipo]["ordenes"] += 1
            ventas_por_documento_dict[tipo]["monto"] += order.amount_total

        ventas_por_documento = list(ventas_por_documento_dict.values())

        ventas_por_documento = sorted(
            ventas_por_documento, key=lambda x: x["monto"], reverse=True
        )

        top_productos_dict = {}

        productos_excluidos = [
            "bolsa",
            "empaque",
            "delivery",
            "envío",
            "envio",
            "redondeo",
            "ajuste",
            "descuento",
        ]

        for order in orders_hoy:
            for line in order.lines:
                product = line.product_id

                if line.qty <= 0:
                    continue

                if product.type == "service":
                    continue

                nombre_producto = (product.display_name or "").lower()

                if any(palabra in nombre_producto for palabra in productos_excluidos):
                    continue

                producto_id = product.id
                producto_nombre = product.display_name or "Sin producto"

                if producto_id not in top_productos_dict:
                    top_productos_dict[producto_id] = {
                        "producto": producto_nombre,
                        "cantidad": 0,
                        "monto": 0.0,
                    }

                top_productos_dict[producto_id]["cantidad"] += line.qty
                top_productos_dict[producto_id]["monto"] += line.price_subtotal_incl

        top_productos = list(top_productos_dict.values())

        top_productos = sorted(
            top_productos, key=lambda x: x["cantidad"], reverse=True
        )[:10]

        estado_sunat_dict = {}

        for order in orders_hoy:

            tipo_doc = False

            if "tipo_documento_reporte" in PosOrder._fields:
                tipo_doc = order.tipo_documento_reporte

            if tipo_doc == "nota_venta":
                continue
            estado = "Sin estado"

            if "sunat_state" in PosOrder._fields:
                estado = order.sunat_state or "Sin estado"

            # Mejorar nombres visuales
            nombres_estado = {
                "aceptado": "Aceptado",
                "error": "Error",
                "pendiente": "Pendiente",
                "pendiente_resumen": "Pendiente resumen",
                "xml_firmado": "XML firmado",
                "enviado": "Enviado",
                "rechazado": "Rechazado",
                "respuesta_sunat": "Con respuesta SUNAT",
                "pendiente_envio": "Pendiente de envío",
                "sin_estado": "Sin estado SUNAT",
            }

            estado_nombre = nombres_estado.get(estado, estado)

            if estado_nombre not in estado_sunat_dict:
                estado_sunat_dict[estado_nombre] = {
                    "estado": estado_nombre,
                    "cantidad": 0,
                    "monto": 0.0,
                }

            estado_sunat_dict[estado_nombre]["cantidad"] += 1
            estado_sunat_dict[estado_nombre]["monto"] += order.amount_total

        estado_sunat = list(estado_sunat_dict.values())

        estado_sunat = sorted(estado_sunat, key=lambda x: x["cantidad"], reverse=True)

        domain_operaciones = [
            ("date_order", ">=", fields.Datetime.to_string(start_utc)),
            ("date_order", "<=", fields.Datetime.to_string(end_utc)),
            ("state", "in", ["paid", "done", "invoiced"]),
        ]

        if pos_config_id:
            domain_operaciones.append(("config_id", "=", int(pos_config_id)))

        orders_operaciones = PosOrder.search(domain_operaciones)

        anulaciones_devoluciones = []

        # Ventas anuladas
        ventas_anuladas = orders_operaciones.filtered(
            lambda o: getattr(o, "venta_anulada", False)
        )

        monto_anuladas = sum(ventas_anuladas.mapped("amount_total"))

        anulaciones_devoluciones.append(
            {
                "concepto": "Órdenes anuladas",
                "cantidad": len(ventas_anuladas),
                "monto": monto_anuladas,
            }
        )

        # Reversas de anulación
        reversas_anulacion = orders_operaciones.filtered(
            lambda o: getattr(o, "es_reversa_anulacion", False)
        )

        monto_reversas = abs(sum(reversas_anulacion.mapped("amount_total")))

        anulaciones_devoluciones.append(
            {
                "concepto": "Reversas de anulación",
                "cantidad": len(reversas_anulacion),
                "monto": monto_reversas,
            }
        )

        # Devoluciones / reembolsos por líneas negativas
        ordenes_con_devolucion = request.env["pos.order"]

        for order in orders_operaciones:
            # No contar reversas de anulación como devolución/reembolso
            if getattr(order, "es_reversa_anulacion", False):
                continue

            tiene_linea_negativa = any(line.qty < 0 for line in order.lines)

            if tiene_linea_negativa:
                ordenes_con_devolucion |= order

        monto_devoluciones = abs(sum(ordenes_con_devolucion.mapped("amount_total")))

        anulaciones_devoluciones.append(
            {
                "concepto": "Devoluciones / reembolsos",
                "cantidad": len(ordenes_con_devolucion),
                "monto": monto_devoluciones,
            }
        )

        prendas_vendidas = 0

        for order in orders_hoy:
            for line in order.lines:
                product = line.product_id

                # No contar cantidades negativas o cero
                if line.qty <= 0:
                    continue

                # No contar productos gratis o líneas sin valor
                if line.price_subtotal <= 0:
                    continue

                # No contar servicios
                if product.type == "service":
                    continue

                # No contar bolsas, empaques o productos auxiliares por nombre
                nombre_producto = (product.display_name or "").lower()

                productos_excluidos = [
                    "bolsa",
                    "empaque",
                    "delivery",
                    "envío",
                    "envio",
                    "redondeo",
                    "ajuste",
                    "descuento",
                ]

                if any(palabra in nombre_producto for palabra in productos_excluidos):
                    continue

                prendas_vendidas += line.qty

        domain_sunat_error = [
            ("date_order", ">=", fields.Datetime.to_string(start_utc)),
            ("date_order", "<=", fields.Datetime.to_string(end_utc)),
        ]

        if pos_config_id:
            domain_sunat_error.append(("config_id", "=", int(pos_config_id)))

        if "sunat_state" in PosOrder._fields:
            domain_sunat_error.append(("sunat_state", "=", "error"))
            sunat_error = PosOrder.search_count(domain_sunat_error)
        else:
            sunat_error = 0

        pos_configs = PosConfig.search([], order="name asc")

        puntos_venta = [
            {
                "id": config.id,
                "name": config.name,
            }
            for config in pos_configs
        ]

        return {
            "ventas_hoy": round(ventas_hoy, 2),
            "ordenes_hoy": ordenes_hoy,
            "ticket_promedio": round(ticket_promedio, 2),
            "prendas_vendidas": prendas_vendidas,
            "sunat_error": sunat_error,
            "ventas_por_tienda": ventas_por_tienda,
            "ventas_por_medio": ventas_por_medio,
            "ventas_por_documento": ventas_por_documento,
            "top_productos": top_productos,
            "estado_sunat": estado_sunat,
            "puntos_venta": puntos_venta,
            "pos_config_id": int(pos_config_id) if pos_config_id else False,
            "anulaciones_devoluciones": anulaciones_devoluciones,
        }
