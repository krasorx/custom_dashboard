# -*- coding: utf-8 -*-
{
    'name': 'Custom Dashboard',
    'version': '18.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'Dashboard personalizado con métricas de facturación, ventas y productos.',
    'description': """
        Dashboard ejecutivo con:
        - KPIs de facturación (ingresos, facturas pendientes, por vencer)
        - KPIs de ventas (órdenes, clientes, ticket promedio)
        - Productos más vendidos
        - Gráfico de ventas por período
        - Navegación directa a registros al hacer click
    """,
    'author': 'Custom',
    'depends': ['account', 'sale_management', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/dashboard_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_dashboard/static/src/xml/dashboard_templates.xml',
            'custom_dashboard/static/src/js/dashboard.js',
            'custom_dashboard/static/src/css/dashboard.css',
            'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js',
            'https://cdn.tailwindcss.com',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
