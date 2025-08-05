from odoo import models, fields, api, _


class CrmLead(models.Model):
    """Extend CRM Lead model with WhatsApp functionality"""
    _inherit = 'crm.lead'

    whatsapp_log_count = fields.Integer(string='WhatsApp Messages',
                                       compute='_compute_whatsapp_log_count')

    @api.depends()
    def _compute_whatsapp_log_count(self):
        """Compute the number of WhatsApp messages sent for this lead"""
        for lead in self:
            lead.whatsapp_log_count = self.env['whatsapp.gateway.log'].search_count([
                ('res_model', '=', 'crm.lead'),
                ('res_id', '=', lead.id)
            ])

    def action_send_whatsapp(self):
        """Action to send WhatsApp message for lead"""
        self.ensure_one()
        
        # Get phone number from lead or partner
        phone_number = self.mobile or self.phone
        if not phone_number and self.partner_id:
            phone_number = self.partner_id.get_whatsapp_phone()
        
        if not phone_number:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Phone Number'),
                    'message': _('No phone number found for %s. Please set a phone or mobile number.') % self.name,
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
                'active_model': 'crm.lead',
                'active_id': self.id,
                'default_phone_number': phone_number,
            }
        }

    def action_view_whatsapp_logs(self):
        """Action to view WhatsApp logs for this lead"""
        return {
            'name': _('WhatsApp Messages for %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.gateway.log',
            'view_mode': 'tree,form',
            'domain': [('res_model', '=', 'crm.lead'), ('res_id', '=', self.id)],
            'context': {'default_res_model': 'crm.lead', 'default_res_id': self.id},
        }