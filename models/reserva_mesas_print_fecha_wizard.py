import base64
import datetime

from odoo import fields, models, _
from odoo.exceptions import UserError


class ReservaMesasPrintFechaWizard(models.TransientModel):
    _name = 'reserva.mesas.print.fecha.wizard'
    _description = 'Imprimir ticket de mesas por fecha'

    fecha = fields.Date(string='Fecha', required=True, default=fields.Date.context_today)

    def _pdf_escape(self, value):
        text = '' if value is None else str(value)
        text = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        # PDF built-in fonts are safest with latin-1/winansi. Replace unsupported symbols.
        return text.encode('latin-1', 'replace').decode('latin-1')

    def _ticket_pdf_bytes(self, reservas, fecha):
        """Create a simple 80 mm PDF ticket without using ir.actions.report.

        This deliberately avoids _render_qweb_pdf/report_action because the IoT
        printing module can intercept ir.actions.report and require an IoT box.
        """
        fecha_txt = fecha.strftime('%d-%m-%Y') if fecha else ''
        grupos = [
            ('13:00 | 13:15', ['13:00', '13:15']),
            ('13:30 | 13:45', ['13:30', '13:45']),
            ('14:00 | 14:15', ['14:00', '14:15']),
            ('14:30 | 14:45', ['14:30', '14:45']),
            ('15:00 | 15:15', ['15:00', '15:15']),
            ('15:30 | 15:45', ['15:30', '15:45']),
            ('19:00 - 21:30', ['19:00', '19:30', '20:00', '20:30', '21:00', '21:30']),
        ]

        reservas_ordenadas = reservas.sorted(lambda r: ((r.x_studio_hora_1 or ''), (r.display_name or '')))
        total_adultos = sum(reservas_ordenadas.mapped(lambda r: r.x_studio_numero_adultos_1 or 0))
        total_ninos = sum(reservas_ordenadas.mapped(lambda r: r.x_studio_numero_ninos or 0))

        lines = []
        lines.append(('CENTER', 'RESERVAS DEL %s' % fecha_txt, 12))
        lines.append(('SEP', '', 10))

        for titulo, horas in grupos:
            bloque = reservas_ordenadas.filtered(lambda r: (r.x_studio_hora_1 or '') in horas)
            lines.append(('BOLD', titulo, 10))
            if bloque:
                for reserva in bloque:
                    nombre = reserva.display_name or reserva.x_name or 'Sin nombre'
                    hora = reserva.x_studio_hora_1 or ''
                    adultos = reserva.x_studio_numero_adultos_1 or 0
                    ninos = reserva.x_studio_numero_ninos or 0
                    line = '%s | %s | Ad: %s | Nn: %s' % (nombre, hora, adultos, ninos)
                    # Split long lines conservatively for 80 mm ticket width.
                    max_len = 38
                    while len(line) > max_len:
                        cut = line.rfind(' ', 0, max_len)
                        if cut <= 0:
                            cut = max_len
                        lines.append(('TEXT', line[:cut], 8))
                        line = line[cut:].strip()
                    lines.append(('TEXT', line, 8))
            else:
                lines.append(('TEXT', '-', 8))
            lines.append(('SPACE', '', 5))

        lines.append(('SEP', '', 10))
        lines.append(('BOLD', 'TOTAL -> Ad: %s | Nn: %s' % (total_adultos, total_ninos), 11))

        width = 226  # 80 mm in points approximately.
        line_height = 12
        height = max(320, 35 + len(lines) * line_height)
        y = height - 24

        content = []
        for kind, text, size in lines:
            if kind == 'SPACE':
                y -= int(size or 5)
                continue
            if kind == 'SEP':
                content.append('0.5 w 12 %.2f m %.2f %.2f l S' % (y, width - 12, y))
                y -= 10
                continue
            font = 'F2' if kind in ('BOLD', 'CENTER') else 'F1'
            safe = self._pdf_escape(text)
            if kind == 'CENTER':
                # Approximate centering for built-in font.
                x = max(10, (width - (len(safe) * size * 0.52)) / 2)
            else:
                x = 12
            content.append('BT /%s %s Tf %.2f %.2f Td (%s) Tj ET' % (font, size, x, y, safe))
            y -= line_height

        stream = '\n'.join(content).encode('cp1252', 'replace')

        objects = []
        objects.append(b'<< /Type /Catalog /Pages 2 0 R >>')
        objects.append(b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>')
        page = ('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] '
                '/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>' % (width, height)).encode('ascii')
        objects.append(page)
        objects.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
        objects.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>')
        objects.append(b'<< /Length ' + str(len(stream)).encode('ascii') + b' >>\nstream\n' + stream + b'\nendstream')

        pdf = bytearray(b'%PDF-1.4\n')
        offsets = [0]
        for i, obj in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(('%s 0 obj\n' % i).encode('ascii'))
            pdf.extend(obj)
            pdf.extend(b'\nendobj\n')
        xref_pos = len(pdf)
        pdf.extend(('xref\n0 %s\n' % (len(objects) + 1)).encode('ascii'))
        pdf.extend(b'0000000000 65535 f \n')
        for off in offsets[1:]:
            pdf.extend(('%010d 00000 n \n' % off).encode('ascii'))
        pdf.extend(('trailer\n<< /Size %s /Root 1 0 R >>\nstartxref\n%s\n%%%%EOF' % (len(objects) + 1, xref_pos)).encode('ascii'))
        return bytes(pdf)

    def _get_reservas_fecha(self):
        self.ensure_one()
        reservas = self.env['x_camping_reservamesas'].sudo().search([
            ('x_studio_fecha_1', '=', self.fecha),
        ], order='x_studio_hora_1 asc, x_name asc')
        if not reservas:
            raise UserError(_('No hay reservas de mesa para la fecha seleccionada.'))
        return reservas

    def action_print(self):
        """Return the independent report action for the new ReservaMesas model.

        This intentionally uses the report integrated in this module, not the
        old Studio report. It mirrors the old Studio action structure but with:
        - active_model: x_camping_reservamesas
        - report_name: odoo_restaurant_table_reservation.studio_report_docume_188a2614-b0c8-47d2-ba4c-6ce5f340e8f3
        """
        self.ensure_one()
        reservas = self._get_reservas_fecha()
        ids = reservas.ids

        return {
            'type': 'ir.actions.report',
            'report_type': 'qweb-pdf',
            'report_name': 'odoo_restaurant_table_reservation.studio_report_docume_188a2614-b0c8-47d2-ba4c-6ce5f340e8f3',
            'context': {
                'active_model': 'x_camping_reservamesas',
                'active_ids': ids,
                'active_id': ids and ids[0] or False,
            },
        }

    def action_download_pdf(self):
        """Manual PDF fallback that does not use ir.actions.report.

        This is useful only when the workstation/direct-print path is not available.
        """
        self.ensure_one()
        reservas = self._get_reservas_fecha()

        pdf_content = self._ticket_pdf_bytes(reservas, self.fecha)

        fecha_txt = self.fecha.strftime('%d-%m-%Y')
        nombre = 'ticketmesas-%s.pdf' % fecha_txt

        adjunto = self.env['ir.attachment'].sudo().create({
            'name': nombre,
            'type': 'binary',
            'datas': base64.b64encode(pdf_content).decode('utf-8'),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % adjunto.id,
            'target': 'self',
        }
