"""DevOps Agent webhook client with HMAC v1 authentication."""
import json
import logging
import os
import hmac
import hashlib
import base64
from datetime import datetime
from typing import Dict, Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import boto3

logger = logging.getLogger(__name__)

secretsmanager = boto3.client('secretsmanager')


def send_webhook(alarm_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send webhook to DevOps Agent with HMAC authentication.
    
    Args:
        alarm_data: Enriched alarm data
        
    Returns:
        Webhook response
    """
    # Get webhook credentials
    credentials = _get_webhook_credentials()
    
    # Build payload
    payload = _build_payload(alarm_data)
    
    # Generate HMAC signature
    timestamp = datetime.utcnow().isoformat() + 'Z'
    signature = _generate_hmac_signature(payload, timestamp, credentials['secret'])
    
    # Send request
    try:
        request = Request(
            credentials['url'],
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'x-amzn-event-timestamp': timestamp,
                'x-amzn-event-signature': signature
            },
            method='POST'
        )
        
        with urlopen(request, timeout=30) as response:
            status_code = response.getcode()
            response_body = response.read().decode('utf-8')
            
            logger.info(f"Webhook response: {status_code}")
            
            return {
                'status_code': status_code,
                'body': response_body
            }
            
    except HTTPError as e:
        logger.error(f"HTTP error: {e.code} - {e.reason}")
        raise
    except URLError as e:
        logger.error(f"URL error: {e.reason}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise


def _get_webhook_credentials() -> Dict[str, str]:
    """Get webhook URL and secret from Secrets Manager."""
    secret_arn = os.environ['SECRET_ARN']
    
    try:
        response = secretsmanager.get_secret_value(SecretId=secret_arn)
        return json.loads(response['SecretString'])
    except Exception as e:
        logger.error(f"Failed to get webhook credentials: {e}")
        raise


def _build_payload(alarm_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build DevOps Agent webhook payload."""
    # Format recent metrics for description
    metrics_summary = ""
    if alarm_data.get('recent_metrics'):
        metrics_summary = "\n\nRecent metric values:\n"
        for m in alarm_data['recent_metrics'][:5]:
            metrics_summary += f"- {m['timestamp']}: {m['value']}\n"
    
    return {
        'eventType': 'incident',
        'incidentId': f"{alarm_data['alarm_name']}-{alarm_data['timestamp']}",
        'action': 'created',
        'priority': alarm_data['priority'],
        'title': f"{alarm_data['service_name']} - {alarm_data['metric_name']} Alert",
        'description': f"{alarm_data['reason']}{metrics_summary}",
        'timestamp': alarm_data['timestamp'],
        'service': alarm_data['service_name'],
        'data': {
            'metadata': {
                'region': alarm_data['region'],
                'account_id': alarm_data['account_id'],
                'alarm_name': alarm_data['alarm_name'],
                'alarm_arn': alarm_data['alarm_arn'],
                'service_type': alarm_data['service_type'],
                'metric_name': alarm_data['metric_name'],
                'namespace': alarm_data['namespace'],
                'dimensions': alarm_data['dimensions'],
                'threshold': alarm_data['threshold'],
                'state': alarm_data['state'],
                'previous_state': alarm_data['previous_state']
            }
        }
    }


def _generate_hmac_signature(payload: Dict[str, Any], timestamp: str, secret: str) -> str:
    """Generate HMAC SHA-256 signature for webhook authentication."""
    payload_str = json.dumps(payload)
    message = f"{timestamp}:{payload_str}"
    
    signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    return base64.b64encode(signature).decode('utf-8')
