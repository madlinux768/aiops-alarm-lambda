"""Enrich alarm context with CloudWatch metrics and resource tags."""
import logging
import os
import boto3
from typing import Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

cloudwatch = boto3.client('cloudwatch')
tagging = boto3.client('resourcegroupstaggingapi')


def enrich_alarm_context(alarm_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich alarm with resource tags for priority and service mapping.
    
    Args:
        alarm_data: Parsed alarm data
        
    Returns:
        Enriched alarm data with priority and service name
    """
    # Get resource tags
    tags = _get_alarm_tags(alarm_data['alarm_arn']) if alarm_data.get('alarm_arn') else {}
    
    # Check if webhook is enabled
    webhook_enabled = tags.get('DevOpsAgentEnabled', 'true').lower() == 'true'
    
    # Get priority (from tags or default)
    priority = tags.get('DevOpsAgentPriority', _default_priority(alarm_data))
    
    # Get service name (from tags or alarm name)
    service_name = tags.get('DevOpsAgentService', _extract_service_name(alarm_data))
    
    logger.info(f"Enriched: priority={priority}, service={service_name}, tags_found={len(tags)}")
    
    return {
        **alarm_data,
        'webhook_enabled': webhook_enabled,
        'priority': priority,
        'service_name': service_name,
        'tags': tags
    }


def _get_alarm_tags(alarm_arn: str) -> Dict[str, str]:
    """Get tags for CloudWatch alarm."""
    if not alarm_arn:
        return {}
    
    try:
        response = cloudwatch.list_tags_for_resource(ResourceARN=alarm_arn)
        return {tag['Key']: tag['Value'] for tag in response.get('Tags', [])}
    except Exception as e:
        logger.warning(f"Failed to get alarm tags: {e}")
        return {}


def _get_recent_metrics(alarm_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get recent metric data points (removed - DevOps Agent will investigate metrics)."""
    return []


def _default_priority(alarm_data: Dict[str, Any]) -> str:
    """Determine default priority based on alarm characteristics."""
    # Check for environment variable override
    default_priority = os.environ.get('DEFAULT_PRIORITY', 'MEDIUM')
    
    metric = alarm_data.get('metric_name', '')
    namespace = alarm_data.get('namespace', '')
    
    # HIGH priority conditions (common critical scenarios)
    if namespace == 'AWS/RDS' and 'CPU' in metric:
        return 'HIGH'
    elif namespace == 'AWS/DynamoDB' and 'SystemErrors' in metric:
        return 'HIGH'
    elif namespace == 'AWS/ApplicationELB' and '4XX' in metric:
        return 'HIGH'
    elif namespace == 'AWS/Lambda' and 'Errors' in metric:
        return 'HIGH'
    
    # MEDIUM priority conditions
    elif namespace == 'AWS/ECS' and ('CPU' in metric or 'Memory' in metric):
        return 'MEDIUM'
    elif namespace == 'AWS/NATGateway':
        return 'MEDIUM'
    elif namespace == 'AWS/ApplicationELB' and '5XX' in metric:
        return 'MEDIUM'
    
    # Use configured default for everything else
    return default_priority


def _extract_service_name(alarm_data: Dict[str, Any]) -> str:
    """Extract service name from alarm name or dimensions."""
    # Try to extract from alarm name
    alarm_name = alarm_data['alarm_name']
    
    # Remove common prefixes
    for prefix in ['ApplicationInsights/', 'AWS/', 'ECS/']:
        alarm_name = alarm_name.replace(prefix, '')
    
    # Get first meaningful part
    parts = alarm_name.split('/')
    if len(parts) > 1:
        return parts[0]
    
    # Fallback to dimension values
    dimensions = alarm_data['dimensions']
    if 'ClusterName' in dimensions:
        return dimensions['ClusterName']
    elif 'DBClusterIdentifier' in dimensions:
        return dimensions['DBClusterIdentifier']
    elif 'TableName' in dimensions:
        return dimensions['TableName']
    elif 'LoadBalancer' in dimensions:
        return dimensions['LoadBalancer'].split('/')[-1]
    
    return alarm_data['service_type']
