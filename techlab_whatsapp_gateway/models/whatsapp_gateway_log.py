from odoo import models, fields, api, _


class WhatsAppGatewayLog(models.Model):
    """Log model for WhatsApp message tracking"""
    _name = 'whatsapp.gateway.log'
    _description = 'WhatsApp Gateway Log'
    _order = 'timestamp desc'
    _rec_name = 'phone_number'

    gateway_id = fields.Many2one('whatsapp.gateway', string='Gateway', required=True, ondelete='cascade')
    type = fields.Selection([
        ('external_rest', 'External REST API'),
        ('meta_cloud_api', 'Meta Cloud API'),
    ], string='Gateway Type', required=True)
    
    message = fields.Text(string='Message Content', required=True)
    phone_number = fields.Char(string='Phone Number', required=True)
    
    status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
    ], string='Status', required=True)
    
    response_code = fields.Char(string='Response Code')
    response_body = fields.Text(string='Response Body')
    timestamp = fields.Datetime(string='Timestamp', default=fields.Datetime.now, required=True)
    
    # Optional link to source record
    res_model = fields.Char(string='Source Model')
    res_id = fields.Integer(string='Source Record ID')
    res_name = fields.Char(string='Source Record', compute='_compute_res_name', store=True)
    
    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        """Compute the name of the source record"""
        for log in self:
            if log.res_model and log.res_id:
                try:
                    record = self.env[log.res_model].browse(log.res_id)
                    if record.exists():
                        log.res_name = record.display_name
                    else:
                        log.res_name = _('Deleted Record')
                except Exception:
                    log.res_name = _('Invalid Record')
            else:
                log.res_name = ''
    
    def action_view_source_record(self):
        """Action to view the source record"""
        if not self.res_model or not self.res_id:
            return
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_retry_send(self):
        """Retry sending the message"""
        if self.status == 'success':
            return
        
        gateway = self.gateway_id
        if gateway and gateway.active:
            # Enqueue the message again
            gateway.with_delay().send_whatsapp_async(
                self.message,
                self.phone_number,
                self.res_model,
                self.res_id
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Message queued for retry'),
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Gateway is not active or does not exist'),
                    'type': 'warning',
                }
            }