"""
Email utility functions for the HirePro application.
"""
import logging
from typing import List, Dict, Union, Optional

logger = logging.getLogger(__name__)

def send_email(
    subject: str,
    body: str,
    to_email: Union[str, List[str]],
    from_email: Optional[str] = None,
    cc: Optional[Union[str, List[str]]] = None,
    bcc: Optional[Union[str, List[str]]] = None,
    reply_to: Optional[Union[str, List[str]]] = None,
    template_name: Optional[str] = None,
    template_context: Optional[Dict] = None,
    attachments: Optional[List[Dict]] = None,
    html_content: Optional[str] = None,
    priority: Optional[str] = 'normal',
):
    """
    Generic email sending function.
    Currently just logs the email details since SMTP is not configured.
    
    Args:
        subject (str): Email subject line
        body (str): Plain text content
        to_email (str or list): Recipient email(s)
        from_email (str, optional): Sender email address
        cc (str or list, optional): CC recipient(s)
        bcc (str or list, optional): BCC recipient(s)
        reply_to (str or list, optional): Reply-to email(s)
        template_name (str, optional): Name of the template to use
        template_context (dict, optional): Context variables for the template
        attachments (list, optional): List of attachment dicts with filename, content, mimetype
        html_content (str, optional): HTML content if different from plain text body
        priority (str, optional): Email priority (low, normal, high)
    
    Returns:
        bool: True if email printing/sending was successful
    """
    # Convert list emails to strings for display
    if isinstance(to_email, list):
        to_email_str = ', '.join(to_email)
    else:
        to_email_str = to_email
        
    cc_str = ', '.join(cc) if isinstance(cc, list) else cc
    bcc_str = ', '.join(bcc) if isinstance(bcc, list) else bcc
    reply_to_str = ', '.join(reply_to) if isinstance(reply_to, list) else reply_to
    
    # Print email details for debugging
    logger.info('-' * 80)
    logger.info('EMAIL WOULD BE SENT:')
    logger.info(f'Subject: {subject}')
    logger.info(f'To: {to_email_str}')
    if from_email:
        logger.info(f'From: {from_email}')
    if cc:
        logger.info(f'CC: {cc_str}')
    if bcc:
        logger.info(f'BCC: {bcc_str}')
    if reply_to:
        logger.info(f'Reply-To: {reply_to_str}')
    logger.info(f'Body: {body}')
    if html_content:
        logger.info(f'HTML Content: {"Yes - HTML content available" if html_content else "None"}')
    if template_name:
        logger.info(f'Template: {template_name}')
        if template_context:
            logger.info(f'Template Context: {template_context}')
    if attachments:
        logger.info(f'Attachments: {[a.get("filename") for a in attachments if "filename" in a]}')
    logger.info(f'Priority: {priority}')
    logger.info('-' * 80)
    
    # Print to console as well for immediate visibility
    print('-' * 80)
    print('EMAIL WOULD BE SENT:')
    print(f'Subject: {subject}')
    print(f'To: {to_email_str}')
    if from_email:
        print(f'From: {from_email}')
    if cc:
        print(f'CC: {cc_str}')
    if bcc:
        print(f'BCC: {bcc_str}')
    if reply_to:
        print(f'Reply-To: {reply_to_str}')
    print(f'Body: {body}')
    if html_content:
        print(f'HTML Content: {"Yes - HTML content available" if html_content else "None"}')
    if template_name:
        print(f'Template: {template_name}')
        if template_context:
            print(f'Template Context: {template_context}')
    if attachments:
        print(f'Attachments: {[a.get("filename") for a in attachments if "filename" in a]}')
    print(f'Priority: {priority}')
    print('-' * 80)
    
    return True
