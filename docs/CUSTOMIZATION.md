# Customization Guide

## Overview

This guide shows how to customize the webhook integration for different alarm types, priorities, and deployment scenarios.

## Deployment Context

### Configure Your Deployment

Set deployment context in `terraform.tfvars`:

```hcl
deployment_name        = "production-ecommerce"
deployment_description = "Production e-commerce platform with ECS microservices, RDS Aurora, DynamoDB, and ElastiCache"
```

This context appears in every investigation, helping DevOps Agent understand what it's investigating.

**Examples:**
- `"production-api"` - Simple API deployment
- `"staging-ml-pipeline"` - ML pipeline in staging
- `"retail-store-ecs-mi"` - Retail application on ECS

---

## Priority Configuration

### Default Priority

Set the fallback priority in `terraform.tfvars`:

```hcl
default_priority = "MEDIUM"  # HIGH, MEDIUM, or LOW
```

### Built-in Priority Rules

The Lambda includes common priority mappings:

| Condition | Priority | Rationale |
|-----------|----------|-----------|
| RDS CPU > threshold | HIGH | Database performance critical |
| DynamoDB SystemErrors | HIGH | Data layer failures |
| ALB 4XX errors | HIGH | User-facing errors |
| Lambda Errors | HIGH | Function failures |
| ECS CPU/Memory | MEDIUM | Container resource issues |
| ALB 5XX errors | MEDIUM | Backend errors |
| NAT Gateway errors | MEDIUM | Network issues |

### Override Priority Per-Alarm

Tag individual alarms to override:

```bash
aws cloudwatch tag-resource \
  --resource-arn arn:aws:cloudwatch:REGION:ACCOUNT:alarm:MyAlarm \
  --tags Key=DevOpsAgentPriority,Value=HIGH
```

### Custom Priority Logic

Edit `lambda/context_enricher.py` function `_default_priority()`:

```python
def _default_priority(alarm_data: Dict[str, Any]) -> str:
    """Determine default priority based on alarm characteristics."""
    default_priority = os.environ.get('DEFAULT_PRIORITY', 'MEDIUM')
    
    metric = alarm_data.get('metric_name', '')
    namespace = alarm_data.get('namespace', '')
    
    # Add your custom rules here
    if namespace == 'AWS/ElastiCache' and 'CPUUtilization' in metric:
        return 'HIGH'
    elif namespace == 'Custom/MyApp' and 'ErrorRate' in metric:
        return 'HIGH'
    
    # ... existing rules ...
    
    return default_priority
```

---

## Service Name Mapping

### Automatic Extraction

The Lambda automatically extracts service names from:
1. Alarm tags (`DevOpsAgentService`)
2. Alarm name patterns
3. Resource dimensions (ClusterName, DBClusterIdentifier, etc.)

### Override Service Name Per-Alarm

```bash
aws cloudwatch tag-resource \
  --resource-arn arn:aws:cloudwatch:REGION:ACCOUNT:alarm:MyAlarm \
  --tags Key=DevOpsAgentService,Value="Payment-API"
```

### Custom Service Extraction

Edit `lambda/context_enricher.py` function `_extract_service_name()`:

```python
def _extract_service_name(alarm_data: Dict[str, Any]) -> str:
    """Extract service name from alarm name or dimensions."""
    alarm_name = alarm_data['alarm_name']
    
    # Add your custom patterns
    if 'payment' in alarm_name.lower():
        return 'Payment-Service'
    elif 'auth' in alarm_name.lower():
        return 'Auth-Service'
    
    # ... existing logic ...
```

---

## Alarm Type Examples

### Example 1: Lambda Function Errors

**Alarm Configuration:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "prod-payment-lambda-errors" \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=payment-processor \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold
```

**Tag for customization:**
```bash
aws cloudwatch tag-resource \
  --resource-arn arn:aws:cloudwatch:us-west-2:123456789012:alarm:prod-payment-lambda-errors \
  --tags Key=DevOpsAgentPriority,Value=HIGH \
         Key=DevOpsAgentService,Value="Payment-Service"
```

**Result**: HIGH priority investigation for "Payment-Service - Errors Alert"

---

### Example 2: DynamoDB Throttling

**Alarm Configuration:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "prod-orders-table-throttles" \
  --namespace AWS/DynamoDB \
  --metric-name UserErrors \
  --dimensions Name=TableName,Value=orders-table \
  --statistic Sum \
  --period 60 \
  --evaluation-periods 2 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold
```

**Tag for customization:**
```bash
aws cloudwatch tag-resource \
  --resource-arn arn:aws:cloudwatch:us-west-2:123456789012:alarm:prod-orders-table-throttles \
  --tags Key=DevOpsAgentPriority,Value=MEDIUM \
         Key=DevOpsAgentService,Value="Orders-Service"
```

---

### Example 3: Custom Application Metrics

**Alarm Configuration:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "prod-checkout-failure-rate" \
  --namespace MyApp/Checkout \
  --metric-name FailureRate \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 0.05 \
  --comparison-operator GreaterThanThreshold
```

**Customize priority logic** in `context_enricher.py`:
```python
# Add to _default_priority()
if namespace == 'MyApp/Checkout' and 'FailureRate' in metric:
    return 'HIGH'
```

---

## Disable Webhook for Specific Alarms

Tag alarms to skip webhook:

```bash
aws cloudwatch tag-resource \
  --resource-arn arn:aws:cloudwatch:REGION:ACCOUNT:alarm:MyAlarm \
  --tags Key=DevOpsAgentEnabled,Value=false
```

---

## Testing Strategies

### Strategy 1: Dry-Run Mode

Test without creating investigations:

```hcl
# terraform.tfvars
dry_run_mode = true
```

All payloads logged to CloudWatch for review.

### Strategy 2: Test Events

Use sample events without triggering real alarms:

```bash
aws lambda invoke \
  --function-name devops-agent-webhook-handler \
  --payload file://test-events/eventbridge-alb-4xx.json \
  /tmp/response.json
```

### Strategy 3: Canary Alarms

Create test alarms that trigger on demand:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "test-canary-alarm" \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=test-function \
  --statistic Average \
  --period 60 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold

# Trigger it
aws cloudwatch set-alarm-state \
  --alarm-name "test-canary-alarm" \
  --state-value ALARM \
  --state-reason "Canary test"
```

---

## Advanced Customization

### Add Custom Metadata

Edit `lambda/webhook_client.py` in `_build_payload()`:

```python
'data': {
    'metadata': {
        # ... existing fields ...
        'environment': 'production',
        'team': 'platform',
        'cost_center': 'engineering',
        'runbook_url': 'https://wiki.company.com/runbooks/...'
    }
}
```

### Integrate with Existing Monitoring

Forward to multiple destinations:

```python
# In handler.py, after send_webhook()
if alarm_data['priority'] == 'HIGH':
    # Also send to PagerDuty, Slack, etc.
    send_to_pagerduty(alarm_data)
```

### Filter Alarms

Only process specific alarm patterns:

```python
# In handler.py, before enrichment
if 'test' in alarm_data['alarm_name'].lower():
    logger.info("Skipping test alarm")
    return {'statusCode': 200, 'body': 'Skipped'}
```

---

## Cost Optimization

### Reduce Lambda Invocations

Filter EventBridge rule to specific alarm patterns:

```hcl
# In eventbridge.tf
event_pattern = jsonencode({
  source      = ["aws.cloudwatch"]
  detail-type = ["CloudWatch Alarm State Change"]
  detail = {
    state = {
      value = ["ALARM"]
    }
    alarmName = [{
      prefix = "prod-"  # Only production alarms
    }]
  }
})
```

### Adjust Log Retention

```hcl
# In lambda.tf
retention_in_days = 3  # Reduce from 7 days
```

---

## Security Hardening

### Restrict IAM Permissions

Edit `terraform/iam.tf` to limit CloudWatch access:

```hcl
{
  Sid    = "CloudWatchMetrics"
  Effect = "Allow"
  Action = [
    "cloudwatch:GetMetricStatistics"
  ]
  Resource = "*"
  Condition = {
    StringEquals = {
      "aws:RequestedRegion" = var.aws_region
    }
  }
}
```

### Enable VPC Integration

Add VPC configuration to Lambda:

```hcl
# In lambda.tf
vpc_config {
  subnet_ids         = var.private_subnet_ids
  security_group_ids = [aws_security_group.lambda.id]
}
```

### Rotate Webhook Credentials

```bash
# Update secret
aws secretsmanager update-secret \
  --secret-id devops-agent-webhook-credentials \
  --secret-string '{"url":"NEW_URL","secret":"NEW_SECRET"}'

# Lambda automatically picks up new values on next invocation
```
