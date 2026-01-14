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
    Process CloudWatch alarm from SNS or EventBridge and trigger DevOps Agent webhook.
    
    Args:
        event: SNS event or EventBridge event containing CloudWatch alarm
        context: Lambda context
        
    Returns:
        Response with status and details
    """
    # Detect event source
    if 'Records' in event:
        # SNS event
        logger.info(f"Processing {len(event.get('Records', []))} SNS records")
        return _process_sns_event(event)
    elif 'detail-type' in event and event['detail-type'] == 'CloudWatch Alarm State Change':
        # EventBridge event
        logger.info("Processing EventBridge alarm state change")
        return _process_eventbridge_event(event)
    else:
        logger.error(f"Unknown event type: {event}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Unknown event type'})
        }


def _process_sns_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Process SNS event containing CloudWatch alarm."""
    results = []
    for record in event.get('Records', []):
        try:
            sns_message = json.loads(record['Sns']['Message'])
            logger.info(f"Processing alarm: {sns_message.get('AlarmName')}")
            
            alarm_data = parse_alarm_message(sns_message)
            
            if not alarm_data.get('webhook_enabled', True):
                logger.info(f"Webhook disabled for alarm: {alarm_data['alarm_name']}")
                continue
            
            enriched_data = enrich_alarm_context(alarm_data)
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


def _process_eventbridge_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Process EventBridge alarm state change event."""
    try:
        detail = event['detail']
        alarm_name = detail['alarmName']
        logger.info(f"Processing alarm: {alarm_name}")
        
        # Convert EventBridge format to SNS-like format
        sns_format = {
            'AlarmName': alarm_name,
            'AlarmArn': detail.get('configuration', {}).get('metrics', [{}])[0].get('metricStat', {}).get('metric', {}).get('namespace', ''),
            'NewStateValue': detail['state']['value'],
            'OldStateValue': detail['previousState']['value'],
            'NewStateReason': detail['state']['reason'],
            'StateChangeTime': detail['state']['timestamp'],
            'Region': event['region'],
            'AWSAccountId': event['account'],
            'Trigger': detail.get('configuration', {})
        }
        
        alarm_data = parse_alarm_message(sns_format)
        
        if not alarm_data.get('webhook_enabled', True):
            logger.info(f"Webhook disabled for alarm: {alarm_name}")
            return {'statusCode': 200, 'body': json.dumps({'skipped': True})}
        
        enriched_data = enrich_alarm_context(alarm_data)
        response = send_webhook(enriched_data)
        
        logger.info(f"Successfully processed alarm: {alarm_name}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'alarm_name': alarm_name,
                'status': 'success',
                'webhook_response': response
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing EventBridge event: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'error': str(e)
            })
        }
