"""
Lambda handler for CloudWatch Alarm to DevOps Agent webhook integration.
Parses SNS alarm notifications, enriches context, and triggers investigations.
"""
import json
import logging
import os
from typing import Dict, Any

from alarm_parser import parse_alarm_message
from context_enricher import enrich_alarm_context
from webhook_client import send_webhook

# Configure logging
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Process CloudWatch alarm from SNS and trigger DevOps Agent webhook.
    
    Args:
        event: SNS event containing CloudWatch alarm
        context: Lambda context
        
    Returns:
        Response with status and details
    """
    logger.info(f"Processing {len(event.get('Records', []))} SNS records")
    
    results = []
    for record in event.get('Records', []):
        try:
            # Parse SNS message
            sns_message = json.loads(record['Sns']['Message'])
            logger.info(f"Processing alarm: {sns_message.get('AlarmName')}")
            
            # Parse alarm details
            alarm_data = parse_alarm_message(sns_message)
            
            # Check if webhook is enabled via tags
            if not alarm_data.get('webhook_enabled', True):
                logger.info(f"Webhook disabled for alarm: {alarm_data['alarm_name']}")
                continue
            
            # Enrich with CloudWatch metrics and tags
            enriched_data = enrich_alarm_context(alarm_data)
            
            # Send webhook
            response = send_webhook(enriched_data)
            
            results.append({
                'alarm_name': alarm_data['alarm_name'],
                'status': 'success',
                'webhook_response': response
            })
            
            logger.info(f"Successfully processed alarm: {alarm_data['alarm_name']}")
            
        except Exception as e:
            logger.error(f"Error processing record: {str(e)}", exc_info=True)
            results.append({
                'alarm_name': sns_message.get('AlarmName', 'unknown'),
                'status': 'error',
                'error': str(e)
            })
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': len(results),
            'results': results
        })
    }
