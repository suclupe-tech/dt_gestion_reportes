{
    "name": "Gestión de Reportes",
    "version": "1.0",
    "category": "Inventory",
    "summary": "Reportes dinámicos Detalles Textiles",
    "author": "Detalles Textiles",
    "depends": ["stock", "product", "sale", "point_of_sale"],
    "data": [
        "views/stock_quant_filters.xml",
        "report/stock_quant_template.xml",
        "report/stock_quant_report.xml",
        "data/server_action.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
