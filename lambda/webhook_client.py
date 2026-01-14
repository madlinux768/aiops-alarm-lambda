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
    logger.info(f"Sending webhook for alarm: {alarm_data.get('alarm_name', 'unknown')}")
    logger.info(f"Priority: {alarm_data.get('priority')}, Service: {alarm_data.get('service_name')}")
    
    # Get webhook credentials
    credentials = _get_webhook_credentials()
    
    # Build payload
    payload = _build_payload(alarm_data)
    
    logger.info(f"Webhook payload: title='{payload['title']}', priority={payload['priority']}")
    
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
            
            # Try to extract investigation ID from response
            try:
                response_json = json.loads(response_body) if response_body else {}
                investigation_id = response_json.get('id', 'N/A')
                logger.info(f"✓ Webhook successful: HTTP {status_code} | Investigation ID: {investigation_id}")
            except:
                logger.info(f"✓ Webhook successful: HTTP {status_code} | Response: {response_body[:200]}")
            
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
    """Build DevOps Agent webhook payload with essential context."""
    
    # Build comprehensive description with all context
    description_parts = [
        f"CloudWatch Alarm: {alarm_data['alarm_name']}",
        f"AWS Account: {alarm_data['account_id']}",
        f"Region: {alarm_data['region']}",
        f"",
        f"Metric: {alarm_data['namespace']}/{alarm_data['metric_name']}",
        f"Resource: {_format_dimensions(alarm_data['dimensions'])}",
        f"",
        f"Alarm Reason: {alarm_data['reason']}"
    ]
    
    if alarm_data.get('threshold'):
        description_parts.insert(6, f"Threshold: {alarm_data['threshold']}")
    
    description = "\n".join(description_parts)
    
    return {
        'eventType': 'incident',
        'incidentId': f"{alarm_data['alarm_name']}-{alarm_data['timestamp']}",
        'action': 'created',
        'priority': alarm_data['priority'],
        'title': f"{alarm_data['service_name']} - {alarm_data['metric_name']} Alert",
        'description': description,
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
                'threshold': alarm_data.get('threshold'),
                'state': alarm_data['state'],
                'previous_state': alarm_data['previous_state']
            }
        }
    }


def _format_dimensions(dimensions: Dict[str, str]) -> str:
    """Format dimensions dict into readable string."""
    if not dimensions:
        return "N/A"
    return ", ".join([f"{k}={v}" for k, v in dimensions.items()])


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
