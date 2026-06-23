from odoo import models, fields


class CampingReservaMesasTag(models.Model):
    _name = 'x_camping_reservamesas_tag'
    _description = 'ReservaMesas Tags'
    _rec_name = 'x_name'
    _order = 'id'

    x_name = fields.Char(string='Nombre')
    x_color = fields.Integer(string='Color')
