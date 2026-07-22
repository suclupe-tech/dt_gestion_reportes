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
            activeSection: "ventas_pos",
            filters: {
                date_from: today,
                date_to: today,
                pos_config_id: "",
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

    setSection(section) {
        this.state.activeSection = section;
    }

    formatMoney(value) {
        return Number(value || 0).toFixed(2);
    }
}

DashboardTiendas.template = "dt_gestion_reportes.DashboardTiendas";

registry.category("actions").add("dt_gestion_reportes.dashboard_tiendas", DashboardTiendas);