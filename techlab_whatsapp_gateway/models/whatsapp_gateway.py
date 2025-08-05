import json
import logging
import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.queue_job.job import job

_logger = logging.getLogger(__name__)


class WhatsAppGateway(models.Model):
    """Abstract base class for WhatsApp gateways"""
    _name = 'whatsapp.gateway'
    _description = 'WhatsApp Gateway'
    _order = 'name'

    name = fields.Char(string='Gateway Name', required=True)
    type = fields.Selection([
        ('external_rest', 'External REST API'),
        ('meta_cloud_api', 'Meta Cloud API'),
    ], string='Gateway Type', required=True)
    active = fields.Boolean(string='Active', default=True)
    
    # Computed fields
    log_count = fields.Integer(string='Log Count', compute='_compute_log_count')
    
    @api.depends()
    def _compute_log_count(self):
        """Compute the number of logs for this gateway"""
        for gateway in self:
            gateway.log_count = self.env['whatsapp.gateway.log'].search_count([
                ('gateway_id', '=', gateway.id)
            ])
    
    def action_view_logs(self):
        """Action to view gateway logs"""
        return {
            'name': _('Gateway Logs'),
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.gateway.log',
            'view_mode': 'tree,form',
            'domain': [('gateway_id', '=', self.id)],
            'context': {'default_gateway_id': self.id},
        }

    @job(channel='root.whatsapp')
    def send_whatsapp_async(self, message, phone_number, model=None, res_id=None, template_id=None):
        """
        Send WhatsApp message asynchronously
        Dispatches to appropriate gateway implementation
        """
        try:
            # Clean phone number
            phone_number = self._clean_phone_number(phone_number)
            
            # Dispatch to specific gateway implementation
            if self.type == 'external_rest':
                gateway = self.env['whatsapp.external.gateway'].browse(self.id)
                response = gateway._send_external_message(message, phone_number)
            elif self.type == 'meta_cloud_api':
                gateway = self.env['whatsapp.meta.gateway'].browse(self.id)
                response = gateway._send_meta_message(message, phone_number)
            else:
                raise UserError(_('Unknown gateway type: %s') % self.type)
            
            # Log success
            self._log_message(message, phone_number, 'success', 
                            response.get('status_code', 200), 
                            response.get('response_body', ''), 
                            model, res_id)
            
            # Write to chatter if model and res_id provided
            if model and res_id:
                self._write_to_chatter(model, res_id, message, phone_number, True)
                
            return True
            
        except Exception as e:
            _logger.error('WhatsApp send error: %s', str(e))
            
            # Log error
            self._log_message(message, phone_number, 'error', 
                            getattr(e, 'status_code', 500), 
                            str(e), model, res_id)
            
            # Write error to chatter
            if model and res_id:
                self._write_to_chatter(model, res_id, message, phone_number, False, str(e))
                
            raise
    
    def _clean_phone_number(self, phone_number):
        """Clean and format phone number"""
        if not phone_number:
            raise UserError(_('Phone number is required'))
        
        # Remove common separators and spaces
        cleaned = ''.join(filter(str.isdigit, phone_number))
        
        # Add international prefix if missing
        if not cleaned.startswith('39') and len(cleaned) == 10:  # Italian numbers
            cleaned = '39' + cleaned
        elif not cleaned.startswith('+'):
            cleaned = '+' + cleaned
            
        return cleaned
    
    def _log_message(self, message, phone_number, status, response_code, response_body, model=None, res_id=None):
        """Create log entry for message"""
        self.env['whatsapp.gateway.log'].create({
            'gateway_id': self.id,
            'type': self.type,
            'message': message,
            'phone_number': phone_number,
            'status': status,
            'response_code': str(response_code),
            'response_body': response_body,
            'res_model': model,
            'res_id': res_id,
        })
    
    def _write_to_chatter(self, model, res_id, message, phone_number, success, error_msg=None):
        """Write message to record chatter"""
        try:
            record = self.env[model].browse(res_id)
            if record.exists():
                if success:
                    body = _('WhatsApp message sent to %s: %s') % (phone_number, message)
                    subtype_xmlid = 'mail.mt_note'
                else:
                    body = _('WhatsApp message failed to %s: %s\nError: %s') % (phone_number, message, error_msg)
                    subtype_xmlid = 'mail.mt_comment'
                
                record.message_post(
                    body=body,
                    subtype_xmlid=subtype_xmlid,
                    author_id=self.env.user.partner_id.id,
                )
        except Exception as e:
            _logger.warning('Failed to write to chatter: %s', str(e))


class WhatsAppExternalGateway(models.Model):
    """External REST API Gateway for WhatsApp"""
    _name = 'whatsapp.external.gateway'
    _description = 'WhatsApp External Gateway'
    _inherits = {'whatsapp.gateway': 'gateway_id'}
    
    gateway_id = fields.Many2one('whatsapp.gateway', required=True, ondelete='cascade')
    
    # REST API Configuration
    url = fields.Char(string='API URL', required=True, 
                     help='The REST API endpoint URL')
    method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST'),
    ], string='HTTP Method', default='POST', required=True)
    
    recipient_param = fields.Char(string='Recipient Parameter', default='to',
                                 help='Parameter name for recipient phone number')
    message_param = fields.Char(string='Message Parameter', default='message',
                               help='Parameter name for message content')
    api_key_param = fields.Char(string='API Key Parameter', 
                               help='Parameter name for API key (optional)')
    api_key_value = fields.Char(string='API Key Value',
                               help='API key value for authentication')
    
    headers = fields.Text(string='HTTP Headers', 
                         help='JSON string of HTTP headers')
    params_template = fields.Text(string='Parameters Template',
                                 help='JSON template with {phone}, {message}, {api_key} placeholders',
                                 default='{"to": "{phone}", "message": "{message}"}')
    
    @api.model
    def create(self, vals):
        """Set gateway type on creation"""
        vals['type'] = 'external_rest'
        return super().create(vals)
    
    @api.constrains('headers', 'params_template')
    def _check_json_fields(self):
        """Validate JSON fields"""
        for record in self:
            if record.headers:
                try:
                    json.loads(record.headers)
                except json.JSONDecodeError:
                    raise ValidationError(_('Headers must be valid JSON'))
            
            if record.params_template:
                try:
                    json.loads(record.params_template)
                except json.JSONDecodeError:
                    raise ValidationError(_('Parameters template must be valid JSON'))
    
    def _send_external_message(self, message, phone_number):
        """Send message through external REST API"""
        try:
            # Prepare headers
            headers = {'Content-Type': 'application/json'}
            if self.headers:
                try:
                    custom_headers = json.loads(self.headers)
                    headers.update(custom_headers)
                except json.JSONDecodeError:
                    _logger.warning('Invalid headers JSON for gateway %s', self.name)
            
            # Prepare parameters
            params = {}
            if self.params_template:
                try:
                    template = json.loads(self.params_template)
                    # Replace placeholders
                    params_str = json.dumps(template)
                    params_str = params_str.replace('{phone}', phone_number)
                    params_str = params_str.replace('{message}', message)
                    if self.api_key_value and '{api_key}' in params_str:
                        params_str = params_str.replace('{api_key}', self.api_key_value)
                    params = json.loads(params_str)
                except json.JSONDecodeError:
                    _logger.warning('Invalid params template for gateway %s', self.name)
            
            # Add individual parameters if specified
            if self.recipient_param and phone_number:
                params[self.recipient_param] = phone_number
            if self.message_param and message:
                params[self.message_param] = message
            if self.api_key_param and self.api_key_value:
                params[self.api_key_param] = self.api_key_value
            
            # Make HTTP request
            if self.method == 'GET':
                response = requests.get(self.url, params=params, headers=headers, timeout=30)
            else:
                response = requests.post(self.url, json=params, headers=headers, timeout=30)
            
            response.raise_for_status()
            
            return {
                'status_code': response.status_code,
                'response_body': response.text,
                'success': True
            }
            
        except requests.exceptions.RequestException as e:
            _logger.error('External gateway request failed: %s', str(e))
            raise UserError(_('Failed to send WhatsApp message: %s') % str(e))


class WhatsAppMetaGateway(models.Model):
    """Meta Cloud API Gateway for WhatsApp"""
    _name = 'whatsapp.meta.gateway'
    _description = 'WhatsApp Meta Gateway'
    _inherits = {'whatsapp.gateway': 'gateway_id'}
    
    gateway_id = fields.Many2one('whatsapp.gateway', required=True, ondelete='cascade')
    
    # Meta Cloud API Configuration
    phone_number_id = fields.Char(string='Phone Number ID', required=True,
                                 help='WhatsApp Business phone number ID from Meta')
    access_token = fields.Char(string='Access Token', required=True,
                              help='Meta access token for authentication')
    sender_name = fields.Char(string='Sender Name',
                             help='Business name displayed to recipients')
    
    endpoint_template = fields.Char(string='API Endpoint', 
                                   compute='_compute_endpoint_template',
                                   help='Generated API endpoint URL')
    
    @api.depends('phone_number_id')
    def _compute_endpoint_template(self):
        """Compute Meta API endpoint"""
        for record in self:
            if record.phone_number_id:
                record.endpoint_template = f'https://graph.facebook.com/v18.0/{record.phone_number_id}/messages'
            else:
                record.endpoint_template = ''
    
    @api.model
    def create(self, vals):
        """Set gateway type on creation"""
        vals['type'] = 'meta_cloud_api'
        return super().create(vals)
    
    def _send_meta_message(self, message, phone_number):
        """Send message through Meta Cloud API"""
        try:
            # Remove + from phone number for Meta API
            clean_phone = phone_number.lstrip('+')
            
            # Prepare headers
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
            }
            
            # Prepare payload according to Meta API spec
            payload = {
                'messaging_product': 'whatsapp',
                'to': clean_phone,
                'type': 'text',
                'text': {
                    'body': message
                }
            }
            
            # Make API request
            response = requests.post(
                self.endpoint_template,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            
            return {
                'status_code': response.status_code,
                'response_body': response.text,
                'success': True
            }
            
        except requests.exceptions.RequestException as e:
            _logger.error('Meta gateway request failed: %s', str(e))
            raise UserError(_('Failed to send WhatsApp message via Meta: %s') % str(e))