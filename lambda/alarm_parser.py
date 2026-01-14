"""Parse CloudWatch alarm messages from SNS."""
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def parse_alarm_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse CloudWatch alarm message into structured format.
    
    Args:
        message: SNS message containing alarm data
        
    Returns:
        Parsed alarm data
    """
    alarm_name = message.get('AlarmName', 'Unknown')
    alarm_arn = message.get('AlarmArn', '')
    
    # Extract dimensions
    dimensions = {}
    trigger = message.get('Trigger', {})
    for dim in trigger.get('Dimensions', []):
        dimensions[dim['name']] = dim['value']
    
    # Determine service type from namespace
    namespace = trigger.get('Namespace', '')
    service_type = _extract_service_type(namespace, dimensions)
    
    # Parse state
    new_state = message.get('NewStateValue', 'UNKNOWN')
    old_state = message.get('OldStateValue', 'UNKNOWN')
    
    parsed_data = {
        'alarm_name': alarm_name,
        'alarm_arn': alarm_arn,
        'alarm_description': message.get('AlarmDescription', ''),
        'state': new_state,
        'previous_state': old_state,
        'reason': message.get('NewStateReason', ''),
        'timestamp': message.get('StateChangeTime', datetime.utcnow().isoformat()),
        'region': message.get('Region', message.get('AlarmArn', '').split(':')[3] if ':' in message.get('AlarmArn', '') else 'unknown'),
        'account_id': message.get('AWSAccountId', ''),
        'metric_name': trigger.get('MetricName', ''),
        'namespace': namespace,
        'dimensions': dimensions,
        'service_type': service_type,
        'threshold': trigger.get('Threshold'),
        'comparison_operator': trigger.get('ComparisonOperator', ''),
        'statistic': trigger.get('Statistic', ''),
        'period': trigger.get('Period', 300),
        'evaluation_periods': trigger.get('EvaluationPeriods', 1)
    }
    
    logger.info(f"Parsed alarm: {alarm_name} | {namespace}/{trigger.get('MetricName', 'N/A')} | {new_state}")
    
    return parsed_data


def _extract_service_type(namespace: str, dimensions: Dict[str, str]) -> str:
    """Extract service type from namespace and dimensions."""
    if namespace == 'AWS/ECS':
        return 'ECS'
    elif namespace == 'AWS/RDS':
        return 'RDS'
    elif namespace == 'AWS/DynamoDB':
        return 'DynamoDB'
    elif namespace == 'AWS/ApplicationELB':
        return 'ALB'
    elif namespace == 'AWS/NATGateway':
        return 'NAT Gateway'
    elif namespace == 'ECS/ContainerInsights':
        return 'ECS'
    else:
        return namespace.replace('AWS/', '')
