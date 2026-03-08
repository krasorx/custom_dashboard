# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


class CustomDashboard(models.TransientModel):
    _name = 'custom.dashboard'
    _description = 'Custom Dashboard'

    @api.model
    def get_dashboard_data(self, date_from=None, date_to=None):
        """Retorna todos los datos necesarios para el dashboard."""
        today = date.today()

        if not date_from:
            date_from = today.replace(day=1)
        else:
            date_from = fields.Date.from_string(date_from)

        if not date_to:
            date_to = today
        else:
            date_to = fields.Date.from_string(date_to)

        return {
            'billing': self._get_billing_data(date_from, date_to),
            'sales': self._get_sales_data(date_from, date_to),
            'top_products': self._get_top_products(date_from, date_to),
            'sales_chart': self._get_sales_chart_data(date_from, date_to),
            'billing_chart': self._get_billing_chart_data(date_from, date_to),
            'billing_by_customer': self._get_billing_by_customer(date_from, date_to),
            'date_from': fields.Date.to_string(date_from),
            'date_to': fields.Date.to_string(date_to),
        }

    def _get_billing_data(self, date_from, date_to):
        Invoice = self.env['account.move']

        # Facturas confirmadas en el período
        confirmed = Invoice.search([
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
        ])

        total_invoiced = sum(
            inv.amount_total if inv.move_type == 'out_invoice'
            else -inv.amount_total
            for inv in confirmed
        )
        total_paid = sum(
            inv.amount_total if inv.move_type == 'out_invoice'
            else -inv.amount_total
            for inv in confirmed if inv.payment_state == 'paid'
        )
        total_pending = sum(
            inv.amount_residual
            for inv in confirmed
            if inv.move_type == 'out_invoice' and inv.payment_state not in ('paid', 'reversed')
        )

        # Vencidas
        overdue = Invoice.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'not in', ['paid', 'reversed']),
            ('invoice_date_due', '<', fields.Date.today()),
        ])
        total_overdue = sum(inv.amount_residual for inv in overdue)

        # Por vencer (próximos 30 días)
        upcoming = Invoice.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'not in', ['paid', 'reversed']),
            ('invoice_date_due', '>=', fields.Date.today()),
            ('invoice_date_due', '<=', fields.Date.today() + timedelta(days=30)),
        ])
        total_upcoming = sum(inv.amount_residual for inv in upcoming)

        return {
            'total_invoiced': round(total_invoiced, 2),
            'total_paid': round(total_paid, 2),
            'total_pending': round(total_pending, 2),
            'total_overdue': round(total_overdue, 2),
            'total_upcoming': round(total_upcoming, 2),
            'count_invoices': len([i for i in confirmed if i.move_type == 'out_invoice']),
            'count_refunds': len([i for i in confirmed if i.move_type == 'out_refund']),
            'count_overdue': len(overdue),
        }

    def _get_sales_data(self, date_from, date_to):
        SaleOrder = self.env['sale.order']

        confirmed_orders = SaleOrder.search([
            ('state', 'in', ['sale', 'done']),
            ('date_order', '>=', fields.Datetime.to_datetime(date_from)),
            ('date_order', '<=', fields.Datetime.to_datetime(date_to).replace(hour=23, minute=59, second=59)),
        ])

        total_sales = sum(order.amount_total for order in confirmed_orders)
        customer_ids = confirmed_orders.mapped('partner_id')
        avg_ticket = total_sales / len(confirmed_orders) if confirmed_orders else 0

        # Órdenes por estado
        quotations = SaleOrder.search_count([
            ('state', 'in', ['draft', 'sent']),
            ('date_order', '>=', fields.Datetime.to_datetime(date_from)),
            ('date_order', '<=', fields.Datetime.to_datetime(date_to).replace(hour=23, minute=59, second=59)),
        ])

        return {
            'total_sales': round(total_sales, 2),
            'count_orders': len(confirmed_orders),
            'count_customers': len(customer_ids),
            'avg_ticket': round(avg_ticket, 2),
            'count_quotations': quotations,
        }

    def _get_top_products(self, date_from, date_to):
        SaleOrderLine = self.env['sale.order.line']

        lines = SaleOrderLine.search([
            ('order_id.state', 'in', ['sale', 'done']),
            ('order_id.date_order', '>=', fields.Datetime.to_datetime(date_from)),
            ('order_id.date_order', '<=', fields.Datetime.to_datetime(date_to).replace(hour=23, minute=59, second=59)),
            ('product_id', '!=', False),
        ])

        product_data = {}
        for line in lines:
            pid = line.product_id.id
            if pid not in product_data:
                product_data[pid] = {
                    'id': pid,
                    'name': line.product_id.display_name,
                    'qty': 0,
                    'revenue': 0,
                }
            product_data[pid]['qty'] += line.product_uom_qty
            product_data[pid]['revenue'] += line.price_subtotal

        top = sorted(product_data.values(), key=lambda x: x['revenue'], reverse=True)[:10]
        for p in top:
            p['qty'] = round(p['qty'], 2)
            p['revenue'] = round(p['revenue'], 2)

        return top

    def _get_sales_chart_data(self, date_from, date_to):
        """Ventas agrupadas por día o mes según el rango."""
        SaleOrder = self.env['sale.order']
        delta = (date_to - date_from).days

        if delta <= 31:
            # Agrupado por día
            group_by = 'date_order:day'
            label_format = '%d/%m'
        else:
            # Agrupado por mes
            group_by = 'date_order:month'
            label_format = '%m/%Y'

        result = SaleOrder.read_group(
            domain=[
                ('state', 'in', ['sale', 'done']),
                ('date_order', '>=', fields.Datetime.to_datetime(date_from)),
                ('date_order', '<=', fields.Datetime.to_datetime(date_to).replace(hour=23, minute=59, second=59)),
            ],
            fields=['amount_total:sum', 'date_order:'],
            groupby=[group_by],
            orderby='date_order asc',
        )

        labels = []
        values = []
        for r in result:
            dt = r.get('date_order:day') or r.get('date_order:month')
            if dt:
                try:
                    from datetime import datetime
                    d = datetime.strptime(str(dt), '%d %b %Y') if ':day' in group_by else datetime.strptime(str(dt), '%B %Y')
                    labels.append(d.strftime(label_format))
                except Exception:
                    labels.append(str(dt))
            values.append(round(r.get('amount_total', 0), 2))

        return {'labels': labels, 'values': values}

    def _get_billing_by_customer(self, date_from, date_to):
        """Facturación agrupada por cliente, top 10 + resto agrupado en 'Otros'."""
        Invoice = self.env['account.move']

        invoices = Invoice.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
        ])

        customer_data = {}
        for inv in invoices:
            pid = inv.partner_id.id
            if pid not in customer_data:
                customer_data[pid] = {
                    'id': pid,
                    'name': inv.partner_id.display_name or 'Sin nombre',
                    'total': 0.0,
                }
            customer_data[pid]['total'] += inv.amount_total

        sorted_customers = sorted(customer_data.values(), key=lambda x: x['total'], reverse=True)

        top = sorted_customers[:10]
        others = sorted_customers[10:]

        labels = [c['name'] for c in top]
        values = [round(c['total'], 2) for c in top]
        ids = [c['id'] for c in top]

        if others:
            labels.append('Otros')
            values.append(round(sum(c['total'] for c in others), 2))
            ids.append(None)

        return {'labels': labels, 'values': values, 'ids': ids}

    def _get_billing_chart_data(self, date_from, date_to):
        """Facturación agrupada por mes."""
        Invoice = self.env['account.move']

        result = Invoice.read_group(
            domain=[
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', date_from),
                ('invoice_date', '<=', date_to),
            ],
            fields=['amount_total:sum', 'invoice_date:'],
            groupby=['invoice_date:month'],
            orderby='invoice_date asc',
        )

        labels = []
        values = []
        for r in result:
            dt = r.get('invoice_date:month')
            if dt:
                try:
                    from datetime import datetime
                    d = datetime.strptime(str(dt), '%B %Y')
                    labels.append(d.strftime('%m/%Y'))
                except Exception:
                    labels.append(str(dt))
            values.append(round(r.get('amount_total', 0), 2))

        return {'labels': labels, 'values': values}
