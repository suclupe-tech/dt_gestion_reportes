/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { renderToElement } from "@web/core/utils/render";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";


patch(ClosePosPopup.prototype, {

    async imprimirReporteDiario() {
        try {

            // =========================
            // 1. SINCRONIZAR VENTAS POS
            // =========================
            const syncSuccess = await this.pos.pushOrdersWithClosingPopup();

            if (!syncSuccess) {
                return;
            }

            // =========================
            // 2. OBTENER DATOS
            // DEL REPORTE DEL DÍA
            // =========================
            const reporte = await this.pos.data.call(
                "pos.config",
                "get_reporte_movimientos_prendas",
                [[this.pos.config.id]]
            );

            // =========================
            // 3. GENERAR TICKET
            // =========================
            const ticket = renderToElement(
                "dt_gestion_reportes.ReporteMovimientosPrendasTicket",
                {
                    reporte: reporte,
                }
            );

            const temp = document.createElement("div");
            temp.id = "print-movimientos-prendas-temp";
            temp.appendChild(ticket);

            document.body.appendChild(temp);

            // =========================
            // 4. FORMATO 80 MM
            // =========================
            const style = document.createElement("style");

            style.id = "print-movimientos-prendas-style";

            style.innerHTML = `
                @page {
                    size: 80mm auto;
                    margin: 0;
                }

                @media print {

                    body * {
                        visibility: hidden !important;
                    }

                    #print-movimientos-prendas-temp,
                    #print-movimientos-prendas-temp * {
                        visibility: visible !important;
                    }

                    #print-movimientos-prendas-temp {
                        display: block !important;
                        position: absolute !important;
                        left: 0 !important;
                        top: 0 !important;
                        width: 80mm !important;
                        margin: 0 !important;
                        padding: 0 !important;
                        background: white !important;
                    }

                    .reporte-movimientos-prendas-ticket {
                        display: block !important;
                        width: 76mm !important;
                        max-width: 76mm !important;
                        margin: 0 !important;
                        padding: 2mm !important;
                        box-sizing: border-box !important;
                        background: white !important;
                        color: black !important;

                        -webkit-print-color-adjust: exact !important;
                        print-color-adjust: exact !important;
                    }

                    .reporte-movimientos-prendas-ticket * {
                        -webkit-print-color-adjust: exact !important;
                        print-color-adjust: exact !important;
                    }
                }
            `;

            document.head.appendChild(style);

            // =========================
            // 5. IMPRIMIR
            // =========================
            setTimeout(() => {
                window.print();
            }, 300);

            window.onafterprint = () => {
                document
                    .getElementById("print-movimientos-prendas-temp")
                    ?.remove();

                document
                    .getElementById("print-movimientos-prendas-style")
                    ?.remove();

                window.onafterprint = null;
            };

        } catch (error) {

            console.error(
                "Error generando Reporte de Movimientos de Prendas:",
                error
            );

            this.dialog.add(AlertDialog, {
                title: "Reporte diario",
                body: "No se pudo generar el reporte de movimientos de prendas.",
            });
        }
    },

});