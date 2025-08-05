import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class WhatsAppTemplate(models.Model):
    """WhatsApp Message Template"""
    _name = 'whatsapp.template'
    _description = 'WhatsApp Template'
    _order = 'name'

    name = fields.Char(string='Template Name', required=True)
    model_id = fields.Many2one('ir.model', string='Related Model', required=True,
                              help='Model this template can be used with')
    model_name = fields.Char(related='model_id.model', store=True)
    
    gateway_type = fields.Selection([
        ('external_rest', 'External REST API'),
        ('meta_cloud_api', 'Meta Cloud API'),
        ('both', 'Both Types'),
    ], string='Gateway Type', default='both', required=True,
       help='Which gateway types this template is compatible with')
    
    gateway_id = fields.Many2one('whatsapp.gateway', string='Default Gateway',
                                help='Default gateway to use with this template')
    
    # Template content
    body = fields.Text(string='Message Body', required=True,
                      help='Template body with placeholders like ${object.field_name}')
    
    # Optional media support (for future extension)
    media_url = fields.Char(string='Media URL',
                           help='Optional media URL for images, PDFs, etc.')
    interactive_type = fields.Selection([
        ('none', 'None'),
        ('button', 'Button'),
        ('list', 'List'),
    ], string='Interactive Type', default='none',
       help='Type of interactive message (for Meta API)')
    
    # Preview and validation
    preview_text = fields.Html(string='Preview', compute='_compute_preview_text',
                              help='Preview of the template with sample data')
    field_placeholders = fields.Text(string='Available Fields', compute='_compute_field_placeholders',
                                    help='List of available field placeholders')
    
    active = fields.Boolean(string='Active', default=True)
    
    @api.depends('model_id')
    def _compute_field_placeholders(self):
        """Compute available field placeholders for the model"""
        for template in self:
            if template.model_id:
                model = self.env[template.model_id.model]
                fields_info = []
                
                # Get model fields
                for field_name, field in model._fields.items():
                    if field.type in ['char', 'text', 'html', 'selection', 'boolean', 
                                     'integer', 'float', 'monetary', 'date', 'datetime']:
                        fields_info.append(f"${{object.{field_name}}} - {field.string}")
                    elif field.type == 'many2one':
                        fields_info.append(f"${{object.{field_name}.name}} - {field.string}")
                
                # Add common computed fields
                fields_info.extend([
                    "${object.display_name} - Display Name",
                    "${object.create_date} - Creation Date",
                    "${object.write_date} - Last Update",
                    "${user.name} - Current User Name",
                    "${company.name} - Company Name",
                ])
                
                template.field_placeholders = '\n'.join(sorted(fields_info))
            else:
                template.field_placeholders = ''
    
    @api.depends('body', 'model_id')
    def _compute_preview_text(self):
        """Generate a preview of the template with sample data"""
        for template in self:
            if template.body and template.model_id:
                try:
                    # Create a sample object for preview
                    model = self.env[template.model_id.model]
                    sample_record = model.search([], limit=1)
                    
                    if sample_record:
                        preview = template._render_template_content(template.body, sample_record)
                        template.preview_text = f"<p><strong>Preview with {sample_record.display_name}:</strong></p><p>{preview}</p>"
                    else:
                        template.preview_text = "<p><em>No sample record available for preview</em></p>"
                except Exception as e:
                    template.preview_text = f"<p><em>Preview error: {str(e)}</em></p>"
            else:
                template.preview_text = "<p><em>No preview available</em></p>"
    
    @api.constrains('body')
    def _check_template_syntax(self):
        """Validate template syntax"""
        for template in self:
            if template.body:
                # Check for basic syntax errors in placeholders
                placeholders = re.findall(r'\$\{[^}]+\}', template.body)
                for placeholder in placeholders:
                    # Basic validation - should contain object.
                    if not placeholder.startswith('${object.') and not placeholder.startswith('${user.') and not placeholder.startswith('${company.'):
                        raise ValidationError(_('Invalid placeholder: %s. Use ${object.field_name}, ${user.field_name}, or ${company.field_name}') % placeholder)
    
    def render_template(self, record):
        """
        Render template with actual record data
        
        Args:
            record: Odoo record to use for rendering
            
        Returns:
            str: Rendered message content
        """
        if not record:
            raise UserError(_('No record provided for template rendering'))
        
        if record._name != self.model_name:
            raise UserError(_('Template is for model %s, but record is from %s') % (self.model_name, record._name))
        
        return self._render_template_content(self.body, record)
    
    def _render_template_content(self, content, record):
        """
        Internal method to render template content
        
        Args:
            content: Template content with placeholders
            record: Odoo record for data
            
        Returns:
            str: Rendered content
        """
        if not content:
            return ''
        
        rendered = content
        
        # Find all placeholders
        placeholders = re.findall(r'\$\{([^}]+)\}', content)
        
        for placeholder in placeholders:
            try:
                value = self._resolve_placeholder(placeholder, record)
                rendered = rendered.replace('${%s}' % placeholder, str(value) if value is not None else '')
            except Exception as e:
                # Log the error but continue with other placeholders
                rendered = rendered.replace('${%s}' % placeholder, f'[Error: {str(e)}]')
        
        return rendered
    
    def _resolve_placeholder(self, placeholder, record):
        """
        Resolve a single placeholder to its value
        
        Args:
            placeholder: Placeholder string like 'object.name'
            record: Odoo record
            
        Returns:
            Value of the placeholder
        """
        parts = placeholder.split('.')
        
        if parts[0] == 'object':
            # Navigate through the object fields
            current = record
            for part in parts[1:]:
                if hasattr(current, part):
                    current = getattr(current, part)
                else:
                    raise ValueError(f'Field {part} not found')
                    
                # Handle None values
                if current is None:
                    return ''
                    
            return current
            
        elif parts[0] == 'user':
            # Current user fields
            current = self.env.user
            for part in parts[1:]:
                if hasattr(current, part):
                    current = getattr(current, part)
                else:
                    raise ValueError(f'User field {part} not found')
            return current
            
        elif parts[0] == 'company':
            # Company fields
            current = self.env.company
            for part in parts[1:]:
                if hasattr(current, part):
                    current = getattr(current, part)
                else:
                    raise ValueError(f'Company field {part} not found')
            return current
            
        else:
            raise ValueError(f'Unknown placeholder root: {parts[0]}')
    
    def action_test_template(self):
        """Action to test template rendering"""
        if not self.model_id:
            raise UserError(_('Please select a model first'))
        
        # Find a sample record
        model = self.env[self.model_id.model]
        sample_record = model.search([], limit=1)
        
        if not sample_record:
            raise UserError(_('No records found in model %s to test with') % self.model_id.name)
        
        try:
            rendered = self.render_template(sample_record)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Template Test'),
                    'message': _('Rendered message:\n\n%s') % rendered,
                    'type': 'success',
                    'sticky': True,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Template Error'),
                    'message': _('Error rendering template: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    def action_send_template(self):
        """Action to send template via wizard"""
        return {
            'name': _('Send WhatsApp Message'),
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.send.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_template_id': self.id,
                'default_gateway_id': self.gateway_id.id if self.gateway_id else False,
            }
        }