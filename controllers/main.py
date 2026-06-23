from odoo import http
from odoo.http import request


class ReservaMesasRedirect(http.Controller):
    """Redirige la ruta genérica del modelo Studio x_camping_reservamesas a su acción principal."""

    @http.route('/odoo/x_camping_reservamesas/<int:record_id>', type='http', auth='user', website=False)
    def redirect_reservamesas(self, record_id, **kwargs):
        record = request.env['x_camping_reservamesas'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect('/odoo')

        action = request.env.ref(
            'odoo_restaurant_table_reservation.reservamesas_0eceabb9-3db7-4cfd-a5bb-3cdb3750e7a6',
            raise_if_not_found=False,
        )
        if action:
            return request.redirect('/odoo/action-%s/%s' % (action.id, record_id))
        return request.redirect('/odoo')
