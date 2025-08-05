from odoo import models, fields, api, _
from odoo.exceptions import UserError


class WhatsAppSendWizard(models.TransientModel):
    """Wizard for sending WhatsApp messages"""
    _name = 'whatsapp.send.wizard'
    _description = 'Send WhatsApp Message Wizard'

    # Gateway and template selection
    gateway_id = fields.Many2one('whatsapp.gateway', string='Gateway', required=True,
                                domain=[('active', '=', True)],
                                help='Select the gateway to send the message through')
    template_id = fields.Many2one('whatsapp.template', string='Template',
                                 help='Optional template to use for the message')
    
    # Message content
    message = fields.Text(string='Message', required=True,
                         help='The message content to send')
    phone_number = fields.Char(string='Phone Number', required=True,
                              help='Recipient phone number (with country code)')
    
    # Source record context (when called from a record)
    res_model = fields.Char(string='Source Model')
    res_id = fields.Integer(string='Source Record ID')
    res_name = fields.Char(string='Source Record', compute='_compute_res_name')
    
    # UI fields
    show_template_fields = fields.Boolean(string='Show Template Fields', compute='_compute_show_template_fields')
    template_preview = fields.Html(string='Template Preview', compute='_compute_template_preview')
    
    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        """Compute the name of the source record"""
        for wizard in self:
            if wizard.res_model and wizard.res_id:
                try:
                    record = self.env[wizard.res_model].browse(wizard.res_id)
                    if record.exists():
                        wizard.res_name = record.display_name
                    else:
                        wizard.res_name = _('Deleted Record')
                except Exception:
                    wizard.res_name = _('Invalid Record')
            else:
                wizard.res_name = ''
    
    @api.depends('template_id')
    def _compute_show_template_fields(self):
        """Show template-related fields when template is selected"""
        for wizard in self:
            wizard.show_template_fields = bool(wizard.template_id)
    
    @api.depends('template_id', 'res_model', 'res_id')
    def _compute_template_preview(self):
        """Generate template preview"""
        for wizard in self:
            if wizard.template_id and wizard.res_model and wizard.res_id:
                try:
                    record = self.env[wizard.res_model].browse(wizard.res_id)
                    if record.exists():
                        rendered = wizard.template_id.render_template(record)
                        wizard.template_preview = f"<p><strong>Template Preview:</strong></p><p>{rendered}</p>"
                    else:
                        wizard.template_preview = "<p><em>No record available for preview</em></p>"
                except Exception as e:
                    wizard.template_preview = f"<p><em>Preview error: {str(e)}</em></p>"
            else:
                wizard.template_preview = ""
    
    @api.model
    def default_get(self, fields_list):
        """Set default values from context"""
        defaults = super().default_get(fields_list)
        
        # Get context values
        context = self.env.context
        
        # Set source record information
        if context.get('active_model') and context.get('active_id'):
            defaults['res_model'] = context['active_model']
            defaults['res_id'] = context['active_id']
            
            # Try to get phone number from the record
            try:
                record = self.env[context['active_model']].browse(context['active_id'])
                if record.exists():
                    # Look for common phone fields
                    phone_fields = ['mobile', 'phone', 'phone_number', 'whatsapp_number']
                    for field in phone_fields:
                        if hasattr(record, field) and getattr(record, field):
                            defaults['phone_number'] = getattr(record, field)
                            break
            except Exception:
                pass
        
        # Set default gateway if specified
        if context.get('default_gateway_id'):
            defaults['gateway_id'] = context['default_gateway_id']
        
        # Set default template if specified
        if context.get('default_template_id'):
            defaults['template_id'] = context['default_template_id']
        
        return defaults
    
    @api.onchange('template_id')
    def _onchange_template_id(self):
        """Update message content when template changes"""
        if self.template_id:
            # Set default gateway from template if not already set
            if self.template_id.gateway_id and not self.gateway_id:
                self.gateway_id = self.template_id.gateway_id
            
            # Render template if we have a source record
            if self.res_model and self.res_id:
                try:
                    record = self.env[self.res_model].browse(self.res_id)
                    if record.exists():
                        self.message = self.template_id.render_template(record)
                except Exception as e:
                    self.message = f"Template error: {str(e)}"
            else:
                # Use template body as-is if no record context
                self.message = self.template_id.body
    
    @api.onchange('gateway_id', 'template_id')
    def _onchange_gateway_template_compatibility(self):
        """Check gateway and template compatibility"""
        if self.gateway_id and self.template_id:
            if (self.template_id.gateway_type != 'both' and 
                self.template_id.gateway_type != self.gateway_id.type):
                return {
                    'warning': {
                        'title': _('Gateway/Template Mismatch'),
                        'message': _('The selected template is designed for %s gateways, but you selected a %s gateway.') % (
                            dict(self.template_id._fields['gateway_type'].selection)[self.template_id.gateway_type],
                            dict(self.gateway_id._fields['type'].selection)[self.gateway_id.type]
                        )
                    }
                }
    
    def action_send_message(self):
        """Send the WhatsApp message"""
        self.ensure_one()
        
        if not self.message.strip():
            raise UserError(_('Message content is required'))
        
        if not self.phone_number.strip():
            raise UserError(_('Phone number is required'))
        
        try:
            # Queue the message for asynchronous sending
            job = self.gateway_id.with_delay().send_whatsapp_async(
                message=self.message,
                phone_number=self.phone_number,
                model=self.res_model,
                res_id=self.res_id,
                template_id=self.template_id.id if self.template_id else None
            )
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Message Queued'),
                    'message': _('WhatsApp message has been queued for sending. Job ID: %s') % job.uuid,
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            raise UserError(_('Failed to queue message: %s') % str(e))
    
    def action_preview_message(self):
        """Preview the message content"""
        self.ensure_one()
        
        if not self.message:
            raise UserError(_('No message content to preview'))
        
        # Show a notification with the message preview
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Message Preview'),
                'message': _('Message to be sent:\n\n%s\n\nTo: %s') % (self.message, self.phone_number),
                'type': 'info',
                'sticky': True,
            }
        }
    
    def action_test_gateway(self):
        """Test gateway connectivity"""
        self.ensure_one()
        
        if not self.gateway_id:
            raise UserError(_('Please select a gateway first'))
        
        # Send a test message
        test_message = "Test message from Odoo WhatsApp Gateway"
        
        try:
            job = self.gateway_id.with_delay().send_whatsapp_async(
                message=test_message,
                phone_number=self.phone_number,
                model=None,
                res_id=None,
                template_id=None
            )
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Test Message Queued'),
                    'message': _('Test message has been queued for sending. Job ID: %s') % job.uuid,
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Gateway Test Failed'),
                    'message': _('Failed to test gateway: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }