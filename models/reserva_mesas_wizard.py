from odoo import models, fields, api


class ReservaMesasWizard(models.TransientModel):
    _name = 'reserva.mesas.wizard'
    _description = 'Wizard Reserva Mesas'

    x_name = fields.Char(string='Nombre')
    x_studio_fecha_1 = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.context_today
    )
    x_studio_hora_1 = fields.Selection(
        selection=[
            ('13:00', '13:00'),
            ('13:15', '13:15'),
            ('13:30', '13:30'),
            ('13:45', '13:45'),
            ('14:00', '14:00'),
            ('14:15', '14:15'),
            ('14:30', '14:30'),
            ('14:45', '14:45'),
            ('15:00', '15:00'),
            ('15:15', '15:15'),
            ('15:30', '15:30'),
            ('15:45', '15:45'),
            ('19:00', '19:00'),
            ('19:30', '19:30'),
            ('20:00', '20:00'),
            ('20:30', '20:30'),
            ('21:00', '21:00'),
            ('21:30', '21:30'),
        ],
        string='Hora',
        required=True
    )
    x_studio_numero_adultos_1 = fields.Integer(string='Adultos', required=True)
    x_studio_numero_ninos = fields.Integer(string='Niños')
    x_studio_numero_personas = fields.Integer(
        string='Personas',
        compute='_compute_numero_personas',
        store=True,
    )
    x_studio_idreservapiscina_1 = fields.Char(string='Id reserva piscina')
    x_studio_tag_ids = fields.Many2many(
        'x_camping_reservamesas_tag',
        string='Etiquetas'
    )
    x_studio_notes = fields.Text(string='Notas')
    x_studio_partner_id = fields.Many2one(
        'res.partner',
        string='Cliente'
    )
    x_studio_partner_phone = fields.Char(string='Teléfono')
    x_studio_partner_email = fields.Char(string='Email')

    # NUEVO CAMPO
    x_studio_observaciones_externas_1 = fields.Text(string='Observaciones externas')

    @api.depends('x_studio_numero_adultos_1', 'x_studio_numero_ninos')
    def _compute_numero_personas(self):
        for rec in self:
            rec.x_studio_numero_personas = (rec.x_studio_numero_adultos_1 or 0) + (rec.x_studio_numero_ninos or 0)

    @api.onchange('x_studio_partner_id')
    def _onchange_x_studio_partner_id(self):
        for rec in self:
            if rec.x_studio_partner_id:
                rec.x_name = rec.x_studio_partner_id.name or rec.x_name
                rec.x_studio_partner_phone = rec.x_studio_partner_id.phone or False
                rec.x_studio_partner_email = rec.x_studio_partner_id.email or False
            else:
                rec.x_studio_partner_phone = False
                rec.x_studio_partner_email = False

    @api.onchange('x_studio_observaciones_externas_1')
    def _onchange_x_studio_observaciones_externas_1(self):
        for rec in self:
            if rec.x_studio_observaciones_externas_1:
                rec.x_studio_observaciones_externas_1 = rec._sanitize_single_line(
                    rec.x_studio_observaciones_externas_1
                )

    def _sanitize_single_line(self, value):
        if not value:
            return value
        return ' '.join(value.replace('\r', ' ').replace('\n', ' ').split())

    def action_guardar(self):
        self.ensure_one()

        self.env['x_camping_reservamesas'].create({
            'x_name': self.x_name,
            'x_studio_fecha_1': self.x_studio_fecha_1,
            'x_studio_hora_1': self.x_studio_hora_1,
            'x_studio_numero_adultos_1': self.x_studio_numero_adultos_1,
            'x_studio_numero_ninos': self.x_studio_numero_ninos,
            'x_studio_numero_personas': self.x_studio_numero_personas,
            'x_studio_idreservapiscina_1': self.x_studio_idreservapiscina_1,
            'x_studio_tag_ids': [(6, 0, self.x_studio_tag_ids.ids)],
            'x_studio_notes': self.x_studio_notes,
            'x_studio_partner_id': self.x_studio_partner_id.id,
            'x_studio_partner_phone': self.x_studio_partner_phone,
            'x_studio_partner_email': self.x_studio_partner_email,
            'x_studio_observaciones_externas_1': self._sanitize_single_line(
                self.x_studio_observaciones_externas_1
            ),
        })

        return {'type': 'ir.actions.act_window_close'}