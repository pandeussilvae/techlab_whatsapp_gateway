# TechLab WhatsApp Gateway

## 📋 Overview

The **TechLab WhatsApp Gateway** module provides comprehensive WhatsApp messaging capabilities for Odoo 18 Community Edition. It enables asynchronous message sending through multiple gateway types with full logging, template support, and chatter integration.

## ✨ Features

### 🔌 Gateway Support
- **External REST API Gateways**: Support for third-party providers like 360dialog, Ultramsg, Gupshup, etc.
- **Meta Cloud API**: Direct integration with WhatsApp Cloud API from Meta/Facebook
- **Flexible Configuration**: Customizable parameters, headers, and authentication methods

### 🚀 Asynchronous Processing
- **Queue.job Integration**: All messages are sent asynchronously using the queue_job framework
- **Reliable Delivery**: Automatic retry mechanisms for failed messages
- **Performance**: Non-blocking message sending for better user experience

### 📝 Template System
- **Dynamic Templates**: Create reusable message templates with placeholder support
- **Field Mapping**: Automatic field resolution from Odoo records
- **Preview Functionality**: Test templates before sending
- **Multi-Model Support**: Templates can be created for any Odoo model

### 📊 Comprehensive Logging
- **Detailed Logs**: Track all message attempts with full request/response data
- **Status Monitoring**: Real-time delivery status tracking
- **Error Handling**: Comprehensive error logging and debugging information
- **Analytics**: Message statistics and success rates

### 💬 Chatter Integration
- **Automatic Logging**: Messages automatically logged in record chatter
- **Context Awareness**: Links messages to specific records
- **Activity Tracking**: Full audit trail of WhatsApp communications

### 🎯 CRM Integration
- **Partner Integration**: Send WhatsApp messages directly from partner records
- **Lead Integration**: WhatsApp messaging from CRM leads
- **Smart Phone Detection**: Automatic phone number detection from various fields

## 🛠️ Installation

1. **Install Dependencies**:
   ```bash
   pip install requests
   ```

2. **Install queue_job Module**:
   - Install the `queue_job` module from OCA (Odoo Community Association)
   - Configure queue workers

3. **Install Module**:
   - Copy the `techlab_whatsapp_gateway` folder to your Odoo addons directory
   - Update the module list
   - Install the module from Apps menu

## ⚙️ Configuration

### External REST Gateway Setup

1. **Navigate to WhatsApp > Gateways > External REST**
2. **Create New Gateway**:
   - **Name**: Your gateway name
   - **URL**: API endpoint URL
   - **Method**: GET or POST
   - **Parameters**: Configure recipient, message, and API key parameters
   - **Headers**: JSON formatted HTTP headers
   - **Template**: JSON template with placeholders

#### Example Configuration (360dialog):
```json
Headers:
{
  "Content-Type": "application/json",
  "D360-API-KEY": "your_api_key_here"
}

Parameters Template:
{
  "to": "{phone}",
  "text": {
    "body": "{message}"
  },
  "type": "text"
}
```

### Meta Cloud API Gateway Setup

1. **Navigate to WhatsApp > Gateways > Meta Cloud API**
2. **Create New Gateway**:
   - **Name**: Your gateway name
   - **Phone Number ID**: From your Meta Business account
   - **Access Token**: Your Meta access token
   - **Sender Name**: Business name displayed to recipients

## 📋 Usage

### Sending Messages from Records

1. **From Partner/Lead**: Click the "Send WhatsApp" button
2. **Select Gateway**: Choose your configured gateway
3. **Choose Template** (optional): Select a pre-defined template
4. **Compose Message**: Write or edit your message
5. **Send**: Message will be queued for asynchronous delivery

### Creating Templates

1. **Navigate to WhatsApp > Templates > Message Templates**
2. **Create Template**:
   - **Name**: Template name
   - **Model**: Target Odoo model
   - **Gateway Type**: Compatible gateway types
   - **Body**: Message content with placeholders

#### Template Placeholders:
- `${object.name}`: Record name
- `${object.email}`: Record email
- `${user.name}`: Current user name
- `${company.name}`: Company name

### Monitoring Messages

1. **View Logs**: WhatsApp > Message Logs > All Messages
2. **Filter by Status**: Success/Error
3. **Retry Failed**: Click "Retry" on failed messages
4. **View Details**: Full request/response information

## 🔧 API Reference

### Gateway Methods

#### `send_whatsapp_async(message, phone_number, model=None, res_id=None, template_id=None)`
- **Purpose**: Send WhatsApp message asynchronously
- **Parameters**:
  - `message`: Message content
  - `phone_number`: Recipient phone number
  - `model`: Source model name (optional)
  - `res_id`: Source record ID (optional)
  - `template_id`: Template ID (optional)

### Template Methods

#### `render_template(record)`
- **Purpose**: Render template with record data
- **Parameters**:
  - `record`: Odoo record for data extraction
- **Returns**: Rendered message content

## 🧪 Testing

### Gateway Testing
1. Use the "Test Gateway" button in the send wizard
2. Verify connectivity and authentication
3. Check logs for successful delivery

### Template Testing
1. Use "Test Template" button in template form
2. Verify placeholder resolution
3. Check preview generation

## 🔒 Security

### Access Rights
- **Users**: Read access to gateways and logs, full access to templates and wizard
- **System Administrators**: Full access to all models

### Data Protection
- **API Keys**: Stored with password field protection
- **Access Tokens**: Secured fields for sensitive data
- **Audit Trail**: Complete logging of all activities

## 🐛 Troubleshooting

### Common Issues

#### Message Not Sending
1. Check gateway configuration
2. Verify API credentials
3. Check queue_job worker status
4. Review error logs

#### Template Not Working
1. Verify placeholder syntax
2. Check field availability on model
3. Test with sample record

#### Phone Number Issues
1. Ensure international format (+country_code)
2. Check number validation rules
3. Verify field mapping

### Debugging
1. **Enable Debug Mode**: Check detailed error messages
2. **Review Logs**: WhatsApp > Message Logs for detailed information
3. **Check Workers**: Ensure queue_job workers are running
4. **API Testing**: Use external tools to test API endpoints

## 🚀 Performance Optimization

### Queue Workers
- Configure multiple queue workers for high volume
- Use dedicated channels for WhatsApp messages
- Monitor worker performance

### Database Optimization
- Regular cleanup of old logs
- Index optimization for frequently queried fields
- Archive old unsuccessful attempts

## 🔮 Future Extensions

### Planned Features
- **Media Support**: Images, PDFs, documents
- **Interactive Messages**: Buttons, lists, quick replies
- **Webhook Support**: Incoming message handling
- **Message Templates**: Meta-approved template support
- **Bulk Messaging**: Mass message campaigns
- **Analytics Dashboard**: Advanced reporting and analytics

## 📞 Support

### Documentation
- This README file
- Inline code documentation
- Model field help texts

### Community Support
- Odoo Community Forums
- GitHub Issues (if applicable)
- Local Odoo user groups

## 📄 License

This module is licensed under LGPL-3.

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 🏷️ Version History

### v1.0.0
- Initial release
- External REST gateway support
- Meta Cloud API integration
- Template system
- Async messaging with queue_job
- Comprehensive logging
- CRM integration

---

**TechLab WhatsApp Gateway** - Professional WhatsApp integration for Odoo 18