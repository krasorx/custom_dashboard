/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { rpc } from '@web/core/network/rpc';
import { Component, onMounted, onWillStart, useRef, useState } from '@odoo/owl';


export class CustomDashboard extends Component {
    static template = 'custom_dashboard.Dashboard';

    setup() {
        this.action = useService('action');
        this.notification = useService('notification');

        this.dateFrom = useRef('dateFrom');
        this.dateTo = useRef('dateTo');
        this.salesChartRef = useRef('salesChart');
        this.billingChartRef = useRef('billingChart');

        this._salesChartInstance = null;
        this._billingChartInstance = null;

        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);

        this.state = useState({
            loading: true,
            data: {
                billing: {},
                sales: {},
                top_products: [],
                sales_chart: { labels: [], values: [] },
                billing_chart: { labels: [], values: [] },
            },
            dateFrom: this._formatDate(firstDay),
            dateTo: this._formatDate(today),
        });

        onWillStart(async () => {
            await this._loadData();
        });

        onMounted(() => {
            if (this.dateFrom.el) this.dateFrom.el.value = this.state.dateFrom;
            if (this.dateTo.el) this.dateTo.el.value = this.state.dateTo;
            this._renderCharts();
        });
    }

    // ---- Helpers ----

    _formatDate(d) {
        return d.toISOString().split('T')[0];
    }

    formatCurrency(value) {
        if (value === undefined || value === null) return '$0';
        return new Intl.NumberFormat('es-MX', {
            style: 'currency',
            currency: 'MXN',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(value);
    }

    getProductShare(revenue) {
        const total = this.state.data.top_products.reduce((s, p) => s + p.revenue, 0);
        if (!total) return 0;
        return Math.round((revenue / total) * 100);
    }

    // ---- Data Loading ----

    async _loadData() {
        this.state.loading = true;
        try {
            const result = await rpc('/custom_dashboard/data', {
                date_from: this.state.dateFrom,
                date_to: this.state.dateTo,
            });
            this.state.data = result;
        } catch (e) {
            this.notification.add('Error al cargar datos del dashboard', { type: 'danger' });
            console.error(e);
        } finally {
            this.state.loading = false;
        }
    }

    // ---- Chart Rendering ----

    _renderCharts() {
        this._renderSalesChart();
        this._renderBillingChart();
    }

    _renderSalesChart() {
        const canvas = this.salesChartRef.el;
        if (!canvas || !window.Chart) return;

        if (this._salesChartInstance) {
            this._salesChartInstance.destroy();
        }

        const { labels, values } = this.state.data.sales_chart;
        this._salesChartInstance = new window.Chart(canvas, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Ventas',
                    data: values,
                    backgroundColor: 'rgba(59, 130, 246, 0.7)',
                    borderColor: 'rgba(59, 130, 246, 1)',
                    borderWidth: 1,
                    borderRadius: 6,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => ' ' + this.formatCurrency(ctx.raw),
                        },
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0,0,0,0.04)' },
                        ticks: {
                            callback: (v) => this.formatCurrency(v),
                            font: { size: 11 },
                        },
                    },
                    x: {
                        grid: { display: false },
                        ticks: { font: { size: 11 } },
                    },
                },
            },
        });
    }

    _renderBillingChart() {
        const canvas = this.billingChartRef.el;
        if (!canvas || !window.Chart) return;

        if (this._billingChartInstance) {
            this._billingChartInstance.destroy();
        }

        const { labels, values } = this.state.data.billing_chart;
        this._billingChartInstance = new window.Chart(canvas, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: 'Facturación',
                    data: values,
                    borderColor: 'rgba(99, 102, 241, 1)',
                    backgroundColor: 'rgba(99, 102, 241, 0.08)',
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: 'rgba(99, 102, 241, 1)',
                    pointRadius: 4,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => ' ' + this.formatCurrency(ctx.raw),
                        },
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0,0,0,0.04)' },
                        ticks: {
                            callback: (v) => this.formatCurrency(v),
                            font: { size: 11 },
                        },
                    },
                    x: {
                        grid: { display: false },
                        ticks: { font: { size: 11 } },
                    },
                },
            },
        });
    }

    // ---- Event Handlers ----

    async onDateChange() {
        const from = this.dateFrom.el?.value;
        const to = this.dateTo.el?.value;
        if (from && to && from <= to) {
            this.state.dateFrom = from;
            this.state.dateTo = to;
            await this._loadData();
            this._renderCharts();
        }
    }

    async resetFilters() {
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        this.state.dateFrom = this._formatDate(firstDay);
        this.state.dateTo = this._formatDate(today);
        if (this.dateFrom.el) this.dateFrom.el.value = this.state.dateFrom;
        if (this.dateTo.el) this.dateTo.el.value = this.state.dateTo;
        await this._loadData();
        this._renderCharts();
    }

    // ---- Navigation ----

    goToInvoices(paymentState) {
        const domain = [
            ['move_type', 'in', ['out_invoice', 'out_refund']],
            ['state', '=', 'posted'],
            ['invoice_date', '>=', this.state.dateFrom],
            ['invoice_date', '<=', this.state.dateTo],
        ];
        if (paymentState === 'paid') {
            domain.push(['payment_state', '=', 'paid']);
        } else if (paymentState === 'not_paid') {
            domain.push(['payment_state', 'not in', ['paid', 'reversed']]);
        }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Facturas',
            res_model: 'account.move',
            views: [[false, 'list'], [false, 'form']],
            domain,
            context: { default_move_type: 'out_invoice' },
        });
    }

    goToOverdueInvoices() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Facturas Vencidas',
            res_model: 'account.move',
            views: [[false, 'list'], [false, 'form']],
            domain: [
                ['move_type', '=', 'out_invoice'],
                ['state', '=', 'posted'],
                ['payment_state', 'not in', ['paid', 'reversed']],
                ['invoice_date_due', '<', this._formatDate(new Date())],
            ],
        });
    }

    goToUpcomingInvoices() {
        const today = new Date();
        const in30 = new Date();
        in30.setDate(today.getDate() + 30);
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Facturas Por Vencer',
            res_model: 'account.move',
            views: [[false, 'list'], [false, 'form']],
            domain: [
                ['move_type', '=', 'out_invoice'],
                ['state', '=', 'posted'],
                ['payment_state', 'not in', ['paid', 'reversed']],
                ['invoice_date_due', '>=', this._formatDate(today)],
                ['invoice_date_due', '<=', this._formatDate(in30)],
            ],
        });
    }

    goToSales(state) {
        const domain = [
            ['date_order', '>=', this.state.dateFrom + ' 00:00:00'],
            ['date_order', '<=', this.state.dateTo + ' 23:59:59'],
        ];
        if (state === 'draft') {
            domain.push(['state', 'in', ['draft', 'sent']]);
        } else {
            domain.push(['state', 'in', ['sale', 'done']]);
        }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: state === 'draft' ? 'Cotizaciones' : 'Órdenes de Venta',
            res_model: 'sale.order',
            views: [[false, 'list'], [false, 'form']],
            domain,
        });
    }

    goToCustomers() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Clientes',
            res_model: 'res.partner',
            views: [[false, 'list'], [false, 'form']],
            domain: [['customer_rank', '>', 0]],
        });
    }

    goToProduct(productId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Producto',
            res_model: 'product.product',
            views: [[false, 'form']],
            res_id: productId,
        });
    }
}

registry.category('actions').add('CustomDashboard', CustomDashboard);
