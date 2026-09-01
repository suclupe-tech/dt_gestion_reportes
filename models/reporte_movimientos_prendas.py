from collections import defaultdict
from datetime import datetime, time, timedelta

import pytz

from odoo import models, fields


class PosConfig(models.Model):
    _inherit = "pos.config"

    def get_reporte_movimientos_prendas(self, fecha=None):
        self.ensure_one()

        # =========================
        # FECHA DEL REPORTE
        # =========================
        if fecha:
            fecha_reporte = fields.Date.to_date(fecha)
        else:
            fecha_reporte = fields.Date.context_today(self)

        # Trabajamos con el día completo según zona horaria del usuario
        tz_name = self.env.user.tz or "America/Lima"
        tz = pytz.timezone(tz_name)

        inicio_local = tz.localize(datetime.combine(fecha_reporte, time.min))
        fin_local = inicio_local + timedelta(days=1)

        inicio_utc = inicio_local.astimezone(pytz.UTC).replace(tzinfo=None)
        fin_utc = fin_local.astimezone(pytz.UTC).replace(tzinfo=None)

        # =========================
        # FUNCIÓN PARA AGRUPAR
        # PRODUCTO + CANTIDAD
        # =========================
        def agregar_producto(acumulador, producto, cantidad):
            if not producto or not cantidad or cantidad <= 0:
                return

            producto_id = producto.id

            if producto_id not in acumulador:
                acumulador[producto_id] = {
                    "product_id": producto_id,
                    "descripcion": producto.display_name,
                    "cantidad": 0.0,
                }

            acumulador[producto_id]["cantidad"] += cantidad

        def restar_producto(acumulador, producto, cantidad):
            if not producto or not cantidad or cantidad <= 0:
                return

            producto_id = producto.id

            if producto_id not in acumulador:
                return

            acumulador[producto_id]["cantidad"] -= cantidad

            # Si la devolución dejó el movimiento en cero,
            # ya no debe aparecer en el reporte.
            if acumulador[producto_id]["cantidad"] <= 0:
                acumulador.pop(producto_id, None)

        def obtener_codigo_almacen(location):
            if not location:
                return ""

            warehouses = self.env["stock.warehouse"].sudo().search([])

            for warehouse_item in warehouses:
                view_location = warehouse_item.view_location_id

                if (
                    view_location
                    and location.parent_path
                    and view_location.parent_path
                    and location.parent_path.startswith(view_location.parent_path)
                ):
                    return warehouse_item.code or warehouse_item.name

            return ""

        # ==========================================================
        # 1. PRENDAS VENDIDAS
        # ==========================================================
        ventas_agrupadas = {}

        orders = self.env["pos.order"].search(
            [
                ("config_id", "=", self.id),
                ("date_order", ">=", inicio_utc),
                ("date_order", "<", fin_utc),
                ("state", "in", ["paid", "done"]),
            ],
            order="date_order asc, id asc",
        )

        # Solo ventas válidas
        orders = orders.filtered(
            lambda order: not getattr(order, "venta_anulada", False)
            and not getattr(order, "es_reversa_anulacion", False)
            and getattr(order, "sunat_document_type", False) in ("01", "03", "NV")
        )

        for order in orders:
            for line in order.lines:
                cantidad = line.qty or 0.0

                if cantidad <= 0:
                    continue

                agregar_producto(
                    ventas_agrupadas,
                    line.product_id,
                    cantidad,
                )

        # ==========================================================
        # APLICAR CAMBIOS DE PRENDA REALIZADOS EL MISMO DÍA
        # ==========================================================

        cambios = self.env["pos.order.edit"].search(
            [
                ("pos_order_id", "in", orders.ids),
                ("pos_config_id", "=", self.id),
                ("tipo_operacion", "=", "cambio"),
                ("estado", "=", "aprobado"),
                ("fecha", ">=", inicio_utc),
                ("fecha", "<", fin_utc),
            ],
            order="fecha asc, id asc",
        )

        for cambio in cambios:

            # ------------------------------------------
            # RESTAR PRENDAS DEVUELTAS
            # ------------------------------------------
            for devolucion in cambio.return_line_ids.filtered(
                lambda l: l.qty_return > 0
            ):

                producto = devolucion.product_id
                cantidad = devolucion.qty_return or 0.0

                if not producto or cantidad <= 0:
                    continue

                producto_id = producto.id

                if producto_id not in ventas_agrupadas:
                    ventas_agrupadas[producto_id] = {
                        "product_id": producto_id,
                        "descripcion": producto.display_name,
                        "cantidad": 0.0,
                    }

                ventas_agrupadas[producto_id]["cantidad"] -= cantidad

            # ------------------------------------------
            # SUMAR PRENDAS NUEVAS ENTREGADAS
            # ------------------------------------------
            for nueva in cambio.line_ids.filtered(lambda l: l.qty > 0):

                agregar_producto(
                    ventas_agrupadas,
                    nueva.product_id,
                    nueva.qty,
                )

        # Eliminar productos que terminaron en cero
        ventas = [item for item in ventas_agrupadas.values() if item["cantidad"] > 0]

        ventas.sort(key=lambda item: (item["descripcion"] or "").lower())

        total_vendidas = sum(item["cantidad"] for item in ventas)

        # ==========================================================
        # ALMACÉN RELACIONADO AL POS
        # ==========================================================
        picking_type = self.picking_type_id
        warehouse = picking_type.warehouse_id if picking_type else False

        # Estructuras para transferencias
        transferencias_salida = defaultdict(dict)
        ingresos_agrupados = defaultdict(dict)

        # ==========================================================
        # 2. TRANSFERENCIAS DE PRENDAS
        # ==========================================================
        if warehouse and warehouse.view_location_id:

            view_location = warehouse.view_location_id

            pickings = self.env["stock.picking"].search(
                [
                    ("state", "=", "done"),
                    ("date_done", ">=", inicio_utc),
                    ("date_done", "<", fin_utc),
                    ("location_id.usage", "=", "internal"),
                    ("location_dest_id.usage", "=", "internal"),
                ],
                order="date_done asc, id asc",
            )

            for picking in pickings:

                helper_move = picking.move_ids[:1]

                if not helper_move:
                    continue

                origen_es_tienda = (
                    picking.location_id == view_location
                    or picking.location_id.parent_path
                    and str(view_location.id) + "/" in picking.location_id.parent_path
                )

                destino_es_tienda = (
                    picking.location_dest_id == view_location
                    or picking.location_dest_id.parent_path
                    and str(view_location.id) + "/"
                    in picking.location_dest_id.parent_path
                )

                # Evitar movimientos internos dentro del mismo almacén
                if origen_es_tienda and destino_es_tienda:
                    continue

                # ==========================================================
                # DEVOLUCIONES DE ODOO DEL MISMO DÍA
                # ==========================================================
                movimientos_devolucion = picking.move_ids.filtered(
                    lambda m: (
                        m.origin_returned_move_id
                        and m.origin_returned_move_id.picking_id
                        and m.origin_returned_move_id.picking_id.date_done
                        and inicio_utc
                        <= m.origin_returned_move_id.picking_id.date_done
                        < fin_utc
                    )
                )

                if movimientos_devolucion:

                    for move in movimientos_devolucion:

                        movimiento_original = move.origin_returned_move_id

                        cantidad = (
                            move.quantity
                            if "quantity" in move._fields
                            else move.product_uom_qty
                        )

                        # --------------------------------------------------
                        # La devolución SALE de esta tienda.
                        # Significa que originalmente había INGRESADO.
                        # Ejemplo:
                        # Planta -> Huánuco
                        # Huánuco -> Planta (devolución)
                        # --------------------------------------------------
                        if origen_es_tienda and not destino_es_tienda:

                            origen_original = obtener_codigo_almacen(
                                movimiento_original.location_id
                            )

                            if not origen_original:
                                origen_original = movimiento_original.dt_location_label(
                                    movimiento_original.location_id
                                )

                            restar_producto(
                                ingresos_agrupados[origen_original],
                                move.product_id,
                                cantidad,
                            )

                        # --------------------------------------------------
                        # La devolución INGRESA a esta tienda.
                        # Significa que originalmente había SALIDO.
                        # Ejemplo:
                        # Huánuco -> Planta
                        # Planta -> Huánuco (devolución)
                        # --------------------------------------------------
                        elif destino_es_tienda and not origen_es_tienda:

                            destino_original = movimiento_original.dt_location_label(
                                movimiento_original.location_dest_id
                            )

                            if destino_original:
                                restar_producto(
                                    transferencias_salida[destino_original],
                                    move.product_id,
                                    cantidad,
                                )

                    # Esta devolución ya fue procesada.
                    # No debe contarse nuevamente como transferencia normal.
                    continue

                # =========================
                # SALIDAS A OTRA TIENDA
                # =========================
                if origen_es_tienda and not destino_es_tienda:

                    destino = helper_move.dt_location_label(picking.location_dest_id)

                    if not destino:
                        continue

                    destino_acumulador = transferencias_salida[destino]

                    for move in picking.move_ids:

                        cantidad = (
                            move.quantity
                            if "quantity" in move._fields
                            else move.product_uom_qty
                        )

                        agregar_producto(
                            destino_acumulador,
                            move.product_id,
                            cantidad,
                        )

                # =========================
                # INGRESOS DESDE OTRA TIENDA
                # =========================
                elif destino_es_tienda and not origen_es_tienda:

                    origen = obtener_codigo_almacen(picking.location_id)

                    if not origen:
                        origen = helper_move.dt_location_label(picking.location_id)

                    origen_acumulador = ingresos_agrupados[origen]

                    for move in picking.move_ids:

                        cantidad = (
                            move.quantity
                            if "quantity" in move._fields
                            else move.product_uom_qty
                        )

                        agregar_producto(
                            origen_acumulador,
                            move.product_id,
                            cantidad,
                        )

        # =========================
        # PREPARAR SALIDAS
        # =========================
        transferencias = []
        total_transferidas = 0.0

        for destino, productos in sorted(
            transferencias_salida.items(),
            key=lambda item: item[0].lower(),
        ):
            lineas = list(productos.values())

            if not lineas:
                continue

            lineas.sort(key=lambda item: (item["descripcion"] or "").lower())

            total_destino = sum(item["cantidad"] for item in lineas)

            total_transferidas += total_destino

            transferencias.append(
                {
                    "destino": destino,
                    "lineas": lineas,
                    "total": total_destino,
                }
            )

        # =========================
        # PREPARAR INGRESOS
        # =========================
        ingresos = []

        for origen, productos in sorted(
            ingresos_agrupados.items(),
            key=lambda item: item[0].lower(),
        ):
            for producto in productos.values():

                ingresos.append(
                    {
                        "origen": origen,
                        "product_id": producto["product_id"],
                        "descripcion": producto["descripcion"],
                        "cantidad": producto["cantidad"],
                    }
                )

        ingresos.sort(
            key=lambda item: (
                (item["origen"] or "").lower(),
                (item["descripcion"] or "").lower(),
            )
        )

        total_ingresadas = sum(item["cantidad"] for item in ingresos)

        # ==========================================================
        # RESULTADO ÚNICO
        # POS Y BACKEND USARÁN ESTOS MISMOS DATOS
        # ==========================================================
        return {
            "titulo": "REPORTE DE MOVIMIENTOS DE PRENDAS",
            "tienda": self.name or "",
            "fecha": fecha_reporte.strftime("%d/%m/%Y"),
            "ventas": ventas,
            "totalVendidas": total_vendidas,
            "transferencias": transferencias,
            "totalTransferidas": total_transferidas,
            "ingresos": ingresos,
            "totalIngresadas": total_ingresadas,
        }
