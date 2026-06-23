from odoo import api, models, _
from odoo.exceptions import UserError


class CampingReservamesasSetup(models.AbstractModel):
    _name = 'camping.reservamesas.setup'
    _description = 'Herramientas internas ReservaMesas independiente'

    DEFAULT_TAGS = [
        (7, '🐶', 0),
        (8, '♿', 0),
        (9, '👶🏻', 0),
        (10, '🥘', 0),
        (12, '🪑', 0),
        (13, 'COMEDOR', 1),
        (14, 'BAR', 4),
        (15, 'PORCHE BAR', 10),
        (16, 'TERRAZA BAR', 3),
        (17, 'SALÓN SOCIAL', 6),
        (18, 'SALÓN TERRAZA', 5),
        (19, 'PARA LLEVAR', 0),
        (20, 'PENSIÓN', 3),
        (21, 'GRUPO', 0),
        (22, 'BAUTIZO', 0),
        (23, '1️⃣', 0),
        (24, '2️⃣', 0),
        (25, '3️⃣', 0),
    ]

    @api.model
    def setup_default_tags(self):
        """Create/update the default tags with the same numeric IDs used by the old Studio kanban.

        The kanban exported from Studio checks many2many raw IDs directly, so the independent
        tag model intentionally keeps the same numeric IDs for the visual badges/emojis.
        """
        table = 'x_camping_reservamesas_tag'
        now = "NOW() AT TIME ZONE 'UTC'"
        for tag_id, name, color in self.DEFAULT_TAGS:
            self.env.cr.execute(
                f"""
                INSERT INTO {table} (id, x_name, x_color, create_uid, write_uid, create_date, write_date)
                VALUES (%s, %s, %s, %s, %s, {now}, {now})
                ON CONFLICT (id) DO UPDATE
                    SET x_name = EXCLUDED.x_name,
                        x_color = EXCLUDED.x_color,
                        write_uid = EXCLUDED.write_uid,
                        write_date = EXCLUDED.write_date
                """,
                (tag_id, name, color, self.env.uid, self.env.uid),
            )
        self.env.cr.execute(
            """
            SELECT setval(
                pg_get_serial_sequence('x_camping_reservamesas_tag', 'id'),
                GREATEST((SELECT COALESCE(MAX(id), 1) FROM x_camping_reservamesas_tag), 25),
                true
            )
            """
        )
        return True



    @api.model
    def setup_ticket_tpv_link_field(self):
        """Ensure x_tickets can point to the independent ReservaMesas model.

        The legacy POS ticket model is still x_tickets, but the independent reservation
        model is x_camping_reservamesas. We therefore add a new link field on x_tickets
        instead of reusing the old Studio field that may point to x_reservamesas.
        """
        model_name = 'x_tickets'
        field_name = 'x_camping_reserva_mesa_vinculada'

        ir_model = self.env['ir.model'].sudo().search([('model', '=', model_name)], limit=1)
        if not ir_model:
            return False

        field = self.env['ir.model.fields'].sudo().search([
            ('model', '=', model_name),
            ('name', '=', field_name),
        ], limit=1)
        if not field:
            field = self.env['ir.model.fields'].sudo().create({
                'name': field_name,
                'field_description': 'Reserva de mesa vinculada',
                'model': model_name,
                'model_id': ir_model.id,
                'ttype': 'many2one',
                'relation': 'x_camping_reservamesas',
                'copied': True,
            })

        imd = self.env['ir.model.data'].sudo()
        if not imd.search([
            ('module', '=', 'odoo_restaurant_table_reservation'),
            ('name', '=', 'field_x_tickets__x_camping_reserva_mesa_vinculada'),
        ], limit=1):
            imd.create({
                'module': 'odoo_restaurant_table_reservation',
                'name': 'field_x_tickets__x_camping_reserva_mesa_vinculada',
                'model': 'ir.model.fields',
                'res_id': field.id,
                'noupdate': True,
            })
        return True

    @api.model
    def sync_ticket_tpv_links(self):
        """Synchronize linked x_tickets with independent ReservaMesas records."""
        if 'x_camping_reservamesas' not in self.env or 'x_tickets' not in self.env:
            return False
        self.setup_ticket_tpv_link_field()
        reservas = self.env['x_camping_reservamesas'].sudo().search([])
        for record in reservas:
            ticket_nuevo = record.x_studio_ticket_tpv_vinculado

            tickets_antiguos = self.env['x_tickets'].sudo().search([
                ('x_camping_reserva_mesa_vinculada', '=', record.id)
            ])
            if ticket_nuevo:
                tickets_antiguos = tickets_antiguos.filtered(lambda t: t.id != ticket_nuevo.id)

            for ticket in tickets_antiguos:
                ticket.write({
                    'x_studio_telefono_contacto': False,
                    'x_camping_reserva_mesa_vinculada': False,
                    'x_studio_fecha_grupo': False,
                    'x_studio_numero_personas': False,
                })

            if ticket_nuevo:
                ticket_nuevo.sudo().write({
                    'x_studio_telefono_contacto': record.x_studio_partner_phone or False,
                    'x_camping_reserva_mesa_vinculada': record.id,
                    'x_studio_fecha_grupo': record.x_studio_fecha_1 or False,
                    'x_studio_numero_personas': record.x_studio_numero_personas or 0,
                })
        return True

    @api.model
    def migrate_from_studio(self, limit=None):
        """Copy old Studio reservations from x_reservamesas to x_camping_reservamesas.

        This is idempotent: it uses ir.model.data entries named migrated_reservamesas_<old_id>
        so running it twice will update the migrated records instead of creating duplicates.
        """
        if 'x_reservamesas' not in self.env or 'x_camping_reservamesas' not in self.env:
            raise UserError(_('No existen los modelos origen/destino necesarios para la migración.'))

        self.setup_default_tags()

        old_model = self.env['x_reservamesas'].sudo()
        new_model = self.env['x_camping_reservamesas'].sudo()
        imd = self.env['ir.model.data'].sudo()

        old_fields = old_model._fields
        new_fields = new_model._fields
        skip = {
            'id', 'display_name', '__last_update',
            'create_uid', 'create_date', 'write_uid', 'write_date',
        }

        domain = []
        old_records = old_model.search(domain, order='id asc', limit=limit or None)
        created = 0
        updated = 0
        skipped_fields = set()

        for old in old_records:
            xml_name = f'migrated_reservamesas_{old.id}'
            xmlid = imd.search([
                ('module', '=', 'odoo_restaurant_table_reservation'),
                ('name', '=', xml_name),
                ('model', '=', 'x_camping_reservamesas'),
            ], limit=1)
            target = new_model.browse(xmlid.res_id) if xmlid else new_model.browse()

            vals = {}
            for field_name, old_field in old_fields.items():
                if field_name in skip or field_name not in new_fields:
                    continue
                new_field = new_fields[field_name]
                if getattr(new_field, 'readonly', False) and not getattr(new_field, 'compute', False):
                    # Studio-readonly fields may still be regular fields; don't skip just because readonly.
                    pass
                if old_field.type == 'one2many' or new_field.type == 'one2many':
                    skipped_fields.add(field_name)
                    continue
                try:
                    value = old[field_name]
                    if old_field.type == 'many2one':
                        vals[field_name] = value.id or False
                    elif old_field.type == 'many2many':
                        if field_name == 'x_studio_tag_ids':
                            # The new tag table has been seeded with the same numeric IDs.
                            vals[field_name] = [(6, 0, value.ids)]
                        else:
                            vals[field_name] = [(6, 0, value.ids)]
                    elif old_field.type in ('binary', 'html', 'text', 'char', 'selection', 'date', 'datetime', 'float', 'integer', 'boolean', 'monetary'):
                        vals[field_name] = value
                    else:
                        skipped_fields.add(field_name)
                except Exception:
                    skipped_fields.add(field_name)

            if target.exists():
                target.write(vals)
                updated += 1
            else:
                target = new_model.create(vals)
                imd.create({
                    'module': 'odoo_restaurant_table_reservation',
                    'name': xml_name,
                    'model': 'x_camping_reservamesas',
                    'res_id': target.id,
                    'noupdate': True,
                })
                created += 1

        self.sync_ticket_tpv_links()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Migración ReservaMesas'),
                'message': _('Reservas copiadas: %s creadas, %s actualizadas. Campos omitidos: %s') % (
                    created, updated, ', '.join(sorted(skipped_fields)) or '-'
                ),
                'sticky': True,
                'type': 'success',
            },
        }
