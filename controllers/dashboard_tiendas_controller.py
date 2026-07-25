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

    @http.route("/dt_gestion_reportes/dashboard_stock/data", type="json", auth="user")
    def get_dashboard_stock_data(self, warehouse_id=None):
        StockQuant = request.env["stock.quant"].sudo()
        StockWarehouse = request.env["stock.warehouse"].sudo()
        ProductProduct = request.env["product.product"].sudo()

        warehouses = StockWarehouse.search([], order="name asc")

        almacenes = [
            {
                "id": warehouse.id,
                "name": warehouse.name,
            }
            for warehouse in warehouses
        ]

        productos_excluidos = [
            "bolsa",
            "empaque",
            "delivery",
            "envío",
            "envio",
            "redondeo",
            "ajuste",
            "descuento",
            "propina",
            "propinas",
        ]

        domain_quant = [
            ("location_id.usage", "=", "internal"),
            ("product_id.active", "=", True),
            ("product_id.type", "in", ["product", "consu"]),
        ]

        if warehouse_id:
            selected_warehouse = StockWarehouse.browse(int(warehouse_id))
            if selected_warehouse.exists():
                domain_quant.append(
                    ("location_id", "child_of", selected_warehouse.view_location_id.id)
                )

        quants = StockQuant.search(domain_quant)

        stock_producto = {}
        stock_por_almacen_dict = {}
        productos_stock_bajo_lista = []

        for quant in quants:
            product = quant.product_id
            nombre_producto = (product.display_name or "").lower()

            if any(palabra in nombre_producto for palabra in productos_excluidos):
                continue

            cantidad_disponible = quant.quantity - quant.reserved_quantity

            if product.id not in stock_producto:
                stock_producto[product.id] = {
                    "producto": product.display_name,
                    "cantidad": 0.0,
                }

            stock_producto[product.id]["cantidad"] += cantidad_disponible

            # 2. Para stock disponible por almacén solo contamos stock positivo
            if cantidad_disponible <= 0:
                continue

            almacen_nombre = "Sin almacén"

            for warehouse in warehouses:
                view_location = warehouse.view_location_id
                location = quant.location_id

                if view_location and location.parent_path and view_location.parent_path:
                    if location.parent_path.startswith(view_location.parent_path):
                        almacen_nombre = warehouse.name
                        break

            # Productos con stock bajo
            if 0 < cantidad_disponible <= 20:
                productos_stock_bajo_lista.append(
                    {
                        "producto": product.display_name or "Sin producto",
                        "almacen": almacen_nombre,
                        "stock": round(cantidad_disponible, 2),
                    }
                )

            if almacen_nombre not in stock_por_almacen_dict:
                stock_por_almacen_dict[almacen_nombre] = {
                    "almacen": almacen_nombre,
                    "productos": set(),
                    "unidades": 0.0,
                }

            stock_por_almacen_dict[almacen_nombre]["productos"].add(product.id)
            stock_por_almacen_dict[almacen_nombre]["unidades"] += cantidad_disponible

        total_unidades = sum(
            item["unidades"] for item in stock_por_almacen_dict.values()
        )

        productos_con_stock_ids = set()
        productos_sin_stock_ids = set()
        productos_stock_bajo_ids = set()

        for quant in quants:
            product = quant.product_id
            nombre_producto = (product.display_name or "").lower()

            if any(palabra in nombre_producto for palabra in productos_excluidos):
                continue

            cantidad_disponible = quant.quantity - quant.reserved_quantity

            if cantidad_disponible > 0:
                productos_con_stock_ids.add(product.id)

            if 0 < cantidad_disponible <= 20:
                productos_stock_bajo_ids.add(product.id)

        # Productos sin stock se calcula con los productos reales del filtro
        productos_validos_ids = set(stock_producto.keys())

        productos_sin_stock_ids = productos_validos_ids - productos_con_stock_ids

        productos_con_stock = len(productos_con_stock_ids)
        productos_sin_stock = len(productos_sin_stock_ids)
        productos_stock_bajo = len(productos_stock_bajo_ids)

        stock_por_almacen = []

        for item in stock_por_almacen_dict.values():
            stock_por_almacen.append(
                {
                    "almacen": item["almacen"],
                    "productos": len(item["productos"]),
                    "unidades": round(item["unidades"], 2),
                }
            )

        stock_por_almacen = sorted(
            stock_por_almacen, key=lambda x: x["unidades"], reverse=True
        )

        productos_stock_bajo_lista = sorted(
            productos_stock_bajo_lista, key=lambda x: x["stock"]
        )[:10]

        return {
            "total_unidades": round(total_unidades, 2),
            "productos_con_stock": productos_con_stock,
            "productos_sin_stock": productos_sin_stock,
            "productos_stock_bajo": productos_stock_bajo,
            "stock_por_almacen": stock_por_almacen,
            "productos_stock_bajo_lista": productos_stock_bajo_lista,
            "almacenes": almacenes,
            "warehouse_id": int(warehouse_id) if warehouse_id else False,
        }

    @http.route(
        "/dt_gestion_reportes/dashboard_productos/data", type="json", auth="user"
    )
    def get_dashboard_productos_data(
        self, date_from=None, date_to=None, pos_config_id=None
    ):
        PosOrder = request.env["pos.order"].sudo()
        StockQuant = request.env["stock.quant"].sudo()
        StockWarehouse = request.env["stock.warehouse"].sudo()

        user_tz = request.env.user.tz or "America/Lima"
        tz = pytz.timezone(user_tz)

        if not date_from:
            date_from = fields.Date.context_today(request.env.user)
        if not date_to:
            date_to = fields.Date.context_today(request.env.user)

        date_from_obj = fields.Date.from_string(date_from)
        date_to_obj = fields.Date.from_string(date_to)

        start_local = tz.localize(datetime.combine(date_from_obj, time.min))
        end_local = tz.localize(datetime.combine(date_to_obj, time.max))

        start_utc = start_local.astimezone(pytz.UTC).replace(tzinfo=None)
        end_utc = end_local.astimezone(pytz.UTC).replace(tzinfo=None)

        domain_orders = [
            ("date_order", ">=", start_utc),
            ("date_order", "<=", end_utc),
            ("state", "in", ["paid", "done", "invoiced"]),
        ]

        if "venta_anulada" in PosOrder._fields:
            domain_orders.append(("venta_anulada", "=", False))

        if "es_reversa_anulacion" in PosOrder._fields:
            domain_orders.append(("es_reversa_anulacion", "=", False))

        if pos_config_id:
            domain_orders.append(("config_id", "=", int(pos_config_id)))

        orders = PosOrder.search(domain_orders)

        productos_excluidos = [
            "bolsa",
            "empaque",
            "delivery",
            "envío",
            "envio",
            "redondeo",
            "ajuste",
            "descuento",
            "propina",
            "propinas",
        ]

        productos_vendidos = {}

        for order in orders:
            for line in order.lines:
                product = line.product_id
                nombre_producto = (product.display_name or "").lower()

                if any(palabra in nombre_producto for palabra in productos_excluidos):
                    continue

                if product.type == "service":
                    continue

                if line.qty <= 0:
                    continue

                if line.price_subtotal <= 0:
                    continue

                if product.id not in productos_vendidos:
                    productos_vendidos[product.id] = {
                        "producto": product.display_name,
                        "cantidad": 0.0,
                        "total": 0.0,
                    }

                productos_vendidos[product.id]["cantidad"] += line.qty
                productos_vendidos[product.id]["total"] += line.price_subtotal_incl

        top_productos = sorted(
            productos_vendidos.values(), key=lambda x: x["cantidad"], reverse=True
        )[:10]

        total_productos_vendidos = sum(
            item["cantidad"] for item in productos_vendidos.values()
        )

        productos_vendidos_distintos = len(productos_vendidos)

        producto_mas_vendido = ""
        if top_productos:
            producto_mas_vendido = top_productos[0]["producto"]

        # Stock actual positivo por producto
        domain_quant = [
            ("location_id.usage", "=", "internal"),
            ("product_id.active", "=", True),
            ("product_id.type", "in", ["product", "consu"]),
        ]

        quants = StockQuant.search(domain_quant)

        stock_actual = {}

        for quant in quants:
            product = quant.product_id
            nombre_producto = (product.display_name or "").lower()

            if any(palabra in nombre_producto for palabra in productos_excluidos):
                continue

            cantidad_disponible = quant.quantity - quant.reserved_quantity

            if cantidad_disponible <= 0:
                continue

            if product.id not in stock_actual:
                stock_actual[product.id] = {
                    "producto": product.display_name,
                    "stock": 0.0,
                }

            stock_actual[product.id]["stock"] += cantidad_disponible

        productos_sin_movimiento = []

        for product_id, item in stock_actual.items():
            if product_id not in productos_vendidos:
                productos_sin_movimiento.append(
                    {
                        "producto": item["producto"],
                        "stock": round(item["stock"], 2),
                    }
                )

        productos_sin_movimiento = sorted(
            productos_sin_movimiento, key=lambda x: x["stock"], reverse=True
        )[:10]

        puntos_venta = request.env["pos.config"].sudo().search([], order="name asc")

        return {
            "total_productos_vendidos": round(total_productos_vendidos, 2),
            "productos_vendidos_distintos": productos_vendidos_distintos,
            "producto_mas_vendido": producto_mas_vendido,
            "productos_sin_movimiento": len(productos_sin_movimiento),
            "top_productos": top_productos,
            "productos_sin_movimiento_lista": productos_sin_movimiento,
            "puntos_venta": [{"id": pos.id, "name": pos.name} for pos in puntos_venta],
            "pos_config_id": int(pos_config_id) if pos_config_id else False,
        }

    @http.route("/dt_gestion_reportes/dashboard_caja/data", type="json", auth="user")
    def get_dashboard_caja_data(self, date_from=None, date_to=None, pos_config_id=None):
        PosOrder = request.env["pos.order"].sudo()
        PosPayment = request.env["pos.payment"].sudo()
        PosConfig = request.env["pos.config"].sudo()

        user_tz = request.env.user.tz or "America/Lima"
        tz = pytz.timezone(user_tz)

        if not date_from:
            date_from = fields.Date.context_today(request.env.user)
        if not date_to:
            date_to = fields.Date.context_today(request.env.user)

        date_from_obj = fields.Date.from_string(date_from)
        date_to_obj = fields.Date.from_string(date_to)

        start_local = tz.localize(datetime.combine(date_from_obj, time.min))
        end_local = tz.localize(datetime.combine(date_to_obj, time.max))

        start_utc = start_local.astimezone(pytz.UTC).replace(tzinfo=None)
        end_utc = end_local.astimezone(pytz.UTC).replace(tzinfo=None)

        domain_orders = [
            ("date_order", ">=", start_utc),
            ("date_order", "<=", end_utc),
            ("state", "in", ["paid", "done", "invoiced"]),
        ]

        if "venta_anulada" in PosOrder._fields:
            domain_orders.append(("venta_anulada", "=", False))

        if "es_reversa_anulacion" in PosOrder._fields:
            domain_orders.append(("es_reversa_anulacion", "=", False))

        if pos_config_id:
            domain_orders.append(("config_id", "=", int(pos_config_id)))

        orders = PosOrder.search(domain_orders)

        total_ventas = sum(order.amount_total for order in orders)

        ventas_por_medio_dict = {}
        resumen_pos_dict = {}

        total_efectivo = 0.0
        total_digital = 0.0

        palabras_efectivo = ["efectivo", "cash"]

        for order in orders:
            pos_name = order.config_id.name or "Sin punto de venta"

            if pos_name not in resumen_pos_dict:
                resumen_pos_dict[pos_name] = {
                    "punto_venta": pos_name,
                    "ventas": 0.0,
                    "ordenes": 0,
                    "efectivo": 0.0,
                    "digital": 0.0,
                }

            resumen_pos_dict[pos_name]["ventas"] += order.amount_total
            resumen_pos_dict[pos_name]["ordenes"] += 1

            for payment in order.payment_ids:
                metodo = payment.payment_method_id.name or "Sin método"
                metodo_lower = metodo.lower()
                monto = payment.amount or 0.0

                if metodo not in ventas_por_medio_dict:
                    ventas_por_medio_dict[metodo] = {
                        "medio_pago": metodo,
                        "monto": 0.0,
                    }

                ventas_por_medio_dict[metodo]["monto"] += monto

                es_efectivo = any(
                    palabra in metodo_lower for palabra in palabras_efectivo
                )

                if es_efectivo:
                    total_efectivo += monto
                    resumen_pos_dict[pos_name]["efectivo"] += monto
                else:
                    total_digital += monto
                    resumen_pos_dict[pos_name]["digital"] += monto

        ventas_por_medio = sorted(
            ventas_por_medio_dict.values(), key=lambda x: x["monto"], reverse=True
        )

        resumen_por_punto_venta = sorted(
            resumen_pos_dict.values(), key=lambda x: x["ventas"], reverse=True
        )

        puntos_venta = PosConfig.search([], order="name asc")

        return {
            "total_ventas": round(total_ventas, 2),
            "total_efectivo": round(total_efectivo, 2),
            "total_digital": round(total_digital, 2),
            "total_ordenes": len(orders),
            "ventas_por_medio": [
                {
                    "medio_pago": item["medio_pago"],
                    "monto": round(item["monto"], 2),
                }
                for item in ventas_por_medio
            ],
            "resumen_por_punto_venta": [
                {
                    "punto_venta": item["punto_venta"],
                    "ventas": round(item["ventas"], 2),
                    "ordenes": item["ordenes"],
                    "efectivo": round(item["efectivo"], 2),
                    "digital": round(item["digital"], 2),
                }
                for item in resumen_por_punto_venta
            ],
            "puntos_venta": [{"id": pos.id, "name": pos.name} for pos in puntos_venta],
            "pos_config_id": int(pos_config_id) if pos_config_id else False,
        }
