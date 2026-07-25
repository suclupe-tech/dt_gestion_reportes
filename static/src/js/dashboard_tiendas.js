/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import {useService} from "@web/core/utils/hooks";

class DashboardTiendas extends Component {
    setup() {
        const today = new Date().toISOString().slice(0, 10);

        this.action = useService("action");

        this.state = useState({
            loading: true,
            stockLoading: false,
            activeSection: "ventas_pos",

            filters: {
                date_from: today,
                date_to: today,
                pos_config_id: "",
            },

            stockFilters: {
                warehouse_id: "",
            },

            data: {
                ventas_hoy: 0,
                ordenes_hoy: 0,
                ticket_promedio: 0,
                prendas_vendidas: 0,
                sunat_error: 0,
                ventas_por_tienda: [],
                ventas_por_medio: [],
                ventas_por_documento: [],
                top_productos: [],
                estado_sunat: [],
                puntos_venta: [],
                pos_config_id: false,
                anulaciones_devoluciones: [],
            },

            stockData: {
                total_unidades: 0,
                productos_con_stock: 0,
                productos_sin_stock: 0,
                productos_stock_bajo: 0,
                stock_por_almacen: [],
                productos_stock_bajo_lista: [],
                almacenes: [],
                warehouse_id: false,
            },

            productosLoading: false,

            productosFilters: {
                date_from: today,
                date_to: today,
                pos_config_id: "",
            },

            productosData: {
                total_productos_vendidos: 0,
                productos_vendidos_distintos: 0,
                producto_mas_vendido: "",
                productos_sin_movimiento: 0,
                top_productos: [],
                productos_sin_movimiento_lista: [],
                puntos_venta: [],
                pos_config_id: false,
            },

            cajaLoading: false,

            cajaFilters: {
                date_from: today,
                date_to: today,
                pos_config_id: "",
            },

            cajaData: {
                total_ventas: 0,
                total_efectivo: 0,
                total_digital: 0,
                total_ordenes: 0,
                ventas_por_medio: [],
                resumen_por_punto_venta: [],
                puntos_venta: [],
                pos_config_id: false,
            },
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;

        const data = await rpc("/dt_gestion_reportes/dashboard_tiendas/data", {
            date_from: this.state.filters.date_from,
            date_to: this.state.filters.date_to,
            pos_config_id: this.state.filters.pos_config_id,
        });

        this.state.data = data;
        this.state.loading = false;
    }

    onChangeDateFrom(ev) {
        this.state.filters.date_from = ev.target.value;
    }

    onChangeDateTo(ev) {
        this.state.filters.date_to = ev.target.value;
    }

    onChangePosConfig(ev) {
        this.state.filters.pos_config_id = ev.target.value;
    }

    openOrders() {
        const domain = [
            ["date_order", ">=", this.state.filters.date_from + " 00:00:00"],
            ["date_order", "<=", this.state.filters.date_to + " 23:59:59"],
            ["state", "in", ["paid", "done", "invoiced"]],
        ];

        if (this.state.filters.pos_config_id) {
            domain.push(["config_id", "=", parseInt(this.state.filters.pos_config_id)]);
        }

        // Excluir anuladas y reversas
        domain.push(["venta_anulada", "=", false]);
        domain.push(["es_reversa_anulacion", "=", false]);

        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Órdenes POS del periodo",
            res_model: "pos.order",
            view_mode: "list,form",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: domain,
            target: "current",
        });
    }

    openSunatErrors() {
        const domain = [
            ["date_order", ">=", this.state.filters.date_from + " 00:00:00"],
            ["date_order", "<=", this.state.filters.date_to + " 23:59:59"],
            ["sunat_state", "=", "error"],
        ];

        if (this.state.filters.pos_config_id) {
            domain.push(["config_id", "=", parseInt(this.state.filters.pos_config_id)]);
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Órdenes POS con error SUNAT",
            res_model: "pos.order",
            view_mode: "list,form",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: domain,
            target: "current",
        });
    }

    openAnulaciones() {
        const domain = [
            ["date_order", ">=", this.state.filters.date_from + " 00:00:00"],
            ["date_order", "<=", this.state.filters.date_to + " 23:59:59"],
            ["venta_anulada", "=", true],
        ];

        if (this.state.filters.pos_config_id) {
            domain.push(["config_id", "=", parseInt(this.state.filters.pos_config_id)]);
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Órdenes POS anuladas",
            res_model: "pos.order",
            view_mode: "list,form",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: domain,
            target: "current",
        });
    }

    openDevoluciones() {
        const domain = [
            ["date_order", ">=", this.state.filters.date_from + " 00:00:00"],
            ["date_order", "<=", this.state.filters.date_to + " 23:59:59"],
            ["lines.qty", "<", 0],
        ];

        if (this.state.filters.pos_config_id) {
            domain.push(["config_id", "=", parseInt(this.state.filters.pos_config_id)]);
        }

        // No mezclar reversas de anulación con devoluciones reales
        domain.push(["es_reversa_anulacion", "=", false]);

        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Órdenes POS con devolución / reembolso",
            res_model: "pos.order",
            view_mode: "list,form",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: domain,
            target: "current",
        });
    }

    async setSection(section) {
        this.state.activeSection = section;

        if (section === "stock") {
            await this.loadStockData();
        }

        if (section === "productos") {
            await this.loadProductosData();
        }

        if (section === "caja") {
            await this.loadCajaData();
        }
    }

    async loadStockData() {
        this.state.stockLoading = true;

        const data = await rpc("/dt_gestion_reportes/dashboard_stock/data", {
            warehouse_id: this.state.stockFilters.warehouse_id,
        });

        this.state.stockData = data;
        this.state.stockLoading = false;
    }

    async loadProductosData() {
        this.state.productosLoading = true;

        const data = await rpc("/dt_gestion_reportes/dashboard_productos/data", {
            date_from: this.state.productosFilters.date_from,
            date_to: this.state.productosFilters.date_to,
            pos_config_id: this.state.productosFilters.pos_config_id,
        });

        this.state.productosData = data;
        this.state.productosLoading = false;
    }

    async loadCajaData() {
        this.state.cajaLoading = true;

        const data = await rpc("/dt_gestion_reportes/dashboard_caja/data", {
            date_from: this.state.cajaFilters.date_from,
            date_to: this.state.cajaFilters.date_to,
            pos_config_id: this.state.cajaFilters.pos_config_id,
        });

        this.state.cajaData = data;
        this.state.cajaLoading = false;
    }

    onChangeProductosDateFrom(ev) {
        this.state.productosFilters.date_from = ev.target.value;
    }

    onChangeProductosDateTo(ev) {
        this.state.productosFilters.date_to = ev.target.value;
    }

    onChangeProductosPosConfig(ev) {
        this.state.productosFilters.pos_config_id = ev.target.value;
    }

    onChangeCajaDateFrom(ev) {
        this.state.cajaFilters.date_from = ev.target.value;
    }

    onChangeCajaDateTo(ev) {
        this.state.cajaFilters.date_to = ev.target.value;
    }

    onChangeCajaPosConfig(ev) {
        this.state.cajaFilters.pos_config_id = ev.target.value;
    }

    onChangeWarehouse(ev) {
        this.state.stockFilters.warehouse_id = ev.target.value;
    }

    formatMoney(value) {
        return Number(value || 0).toFixed(2);
    }
}

DashboardTiendas.template = "dt_gestion_reportes.DashboardTiendas";

registry.category("actions").add("dt_gestion_reportes.dashboard_tiendas", DashboardTiendas);