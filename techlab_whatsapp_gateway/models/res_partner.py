from odoo import models, fields, api, _


class ResPartner(models.Model):
    """Extend Partner model with WhatsApp functionality"""
    _inherit = 'res.partner'

    whatsapp_number = fields.Char(string='WhatsApp Number',
                                 help='WhatsApp phone number for this contact')
    whatsapp_log_count = fields.Integer(string='WhatsApp Messages',
                                       compute='_compute_whatsapp_log_count')

    @api.depends()
    def _compute_whatsapp_log_count(self):
        """Compute the number of WhatsApp messages sent to this partner"""
        for partner in self:
            partner.whatsapp_log_count = self.env['whatsapp.gateway.log'].search_count([
                ('res_model', '=', 'res.partner'),
                ('res_id', '=', partner.id)
            ])

    def action_send_whatsapp(self):
        """Action to send WhatsApp message to partner"""
        self.ensure_one()
        
        # Get phone number (prefer WhatsApp number, then mobile, then phone)
        phone_number = self.whatsapp_number or self.mobile or self.phone
        
        if not phone_number:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Phone Number'),
                    'message': _('No phone number found for %s. Please set a phone, mobile, or WhatsApp number.') % self.name,
                    'type': 'warning',
                }
            }
        
        return {
            'name': _('Send WhatsApp Message'),
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.send.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'res.partner',
                'active_id': self.id,
                'default_phone_number': phone_number,
            }
        }

    def action_view_whatsapp_logs(self):
        """Action to view WhatsApp logs for this partner"""
        return {
            'name': _('WhatsApp Messages for %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.gateway.log',
            'view_mode': 'tree,form',
            'domain': [('res_model', '=', 'res.partner'), ('res_id', '=', self.id)],
            'context': {'default_res_model': 'res.partner', 'default_res_id': self.id},
        }

    def get_whatsapp_phone(self):
        """Get the best phone number for WhatsApp"""
        self.ensure_one()
        return self.whatsapp_number or self.mobile or self.phone