/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

class DashboardTiendas extends Component {
    setup() {
        const today = new Date().toISOString().slice(0, 10);

        this.state = useState({
            loading: true,
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

    formatMoney(value) {
        return Number(value || 0).toFixed(2);
    }
}

DashboardTiendas.template = "dt_gestion_reportes.DashboardTiendas";

registry.category("actions").add("dt_gestion_reportes.dashboard_tiendas", DashboardTiendas);