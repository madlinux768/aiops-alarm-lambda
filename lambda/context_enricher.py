"""Enrich alarm context with CloudWatch metrics and resource tags."""
import logging
import boto3
from typing import Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

cloudwatch = boto3.client('cloudwatch')
tagging = boto3.client('resourcegroupstaggingapi')


def enrich_alarm_context(alarm_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich alarm with recent metrics and resource tags.
    
    Args:
        alarm_data: Parsed alarm data
        
    Returns:
        Enriched alarm data with metrics and tags
    """
    # Get resource tags
    tags = _get_alarm_tags(alarm_data['alarm_arn'])
    
    # Check if webhook is enabled
    webhook_enabled = tags.get('DevOpsAgentEnabled', 'true').lower() == 'true'
    
    # Get priority (from tags or default)
    priority = tags.get('DevOpsAgentPriority', _default_priority(alarm_data))
    
    # Get service name (from tags or alarm name)
    service_name = tags.get('DevOpsAgentService', _extract_service_name(alarm_data))
    
    # Get recent metric data
    recent_metrics = _get_recent_metrics(alarm_data)
    
    return {
        **alarm_data,
        'webhook_enabled': webhook_enabled,
        'priority': priority,
        'service_name': service_name,
        'tags': tags,
        'recent_metrics': recent_metrics
    }


def _get_alarm_tags(alarm_arn: str) -> Dict[str, str]:
    """Get tags for CloudWatch alarm."""
    try:
        response = cloudwatch.list_tags_for_resource(ResourceARN=alarm_arn)
        return {tag['Key']: tag['Value'] for tag in response.get('Tags', [])}
    except Exception as e:
        logger.warning(f"Failed to get alarm tags: {e}")
        return {}


def _get_recent_metrics(alarm_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get recent metric data points."""
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        response = cloudwatch.get_metric_statistics(
            Namespace=alarm_data['namespace'],
            MetricName=alarm_data['metric_name'],
            Dimensions=[
                {'Name': k, 'Value': v} 
                for k, v in alarm_data['dimensions'].items()
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=alarm_data['period'],
            Statistics=[alarm_data['statistic']]
        )
        
        datapoints = sorted(
            response.get('Datapoints', []),
            key=lambda x: x['Timestamp'],
            reverse=True
        )[:10]
        
        return [
            {
                'timestamp': dp['Timestamp'].isoformat(),
                'value': dp.get(alarm_data['statistic'], 0)
            }
            for dp in datapoints
        ]
    except Exception as e:
        logger.warning(f"Failed to get recent metrics: {e}")
        return []


def _default_priority(alarm_data: Dict[str, Any]) -> str:
    """Determine default priority based on alarm characteristics."""
    metric = alarm_data['metric_name']
    namespace = alarm_data['namespace']
    
    # HIGH priority conditions
    if namespace == 'AWS/RDS' and 'CPU' in metric:
        return 'HIGH'
    elif namespace == 'AWS/DynamoDB' and 'SystemErrors' in metric:
        return 'HIGH'
    elif namespace == 'AWS/ApplicationELB' and '4XX' in metric:
        return 'HIGH'
    
    # MEDIUM priority conditions
    elif namespace == 'AWS/ECS' and ('CPU' in metric or 'Memory' in metric):
        return 'MEDIUM'
    elif namespace == 'AWS/NATGateway':
        return 'MEDIUM'
    
    # Default to LOW
    return 'LOW'


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
