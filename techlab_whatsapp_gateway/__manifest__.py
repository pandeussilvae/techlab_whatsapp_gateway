{
    'name': 'TechLab WhatsApp Gateway',
    'version': '18.0.1.0.0',
    'category': 'Communication',
    'summary': 'Send WhatsApp messages through external gateways and Meta Cloud API',
    'description': """
    WhatsApp Gateway Integration
    ============================
    
    This module provides asynchronous WhatsApp messaging capabilities through:
    * External REST API gateways (360dialog, Ultramsg, Gupshup, etc.)
    * Direct integration with WhatsApp Cloud API (Meta)
    
    Features:
    * Asynchronous message sending using queue.job
    * Template support with dynamic content
    * Comprehensive logging and response handling
    * Chatter integration for record-linked messages
    * Gateway management and configuration
    * Wizard for easy message sending
    """,
    'author': 'TechLab',
    'website': 'https://techlab.com',
    'depends': [
        'base',
        'queue_job',
        'mail',
        'crm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/whatsapp_gateway_views.xml',
        'views/whatsapp_gateway_log_views.xml',
        'views/whatsapp_template_views.xml',
        'views/whatsapp_menu.xml',
        'wizard/send_whatsapp_wizard_views.xml',
        'views/res_partner_views.xml',
        'views/crm_lead_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'external_dependencies': {
        'python': ['requests'],
    },
    'license': 'LGPL-3',
}