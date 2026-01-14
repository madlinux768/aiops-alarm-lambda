# DevOps Agent Webhook Integration

Automated CloudWatch Alarm to AWS DevOps Agent Investigation pattern using pure Terraform.

## Architecture

```
CloudWatch Alarms → SNS Topic → Lambda Function → DevOps Agent Webhook → Investigation
```

## Features

- **HMAC v1 Authentication**: Secure webhook calls with timestamp-based signatures
- **Context Enrichment**: Automatically gathers CloudWatch metrics and resource tags
- **Tag-Based Configuration**: Control behavior via alarm tags
- **Dead Letter Queue**: Failed invocations captured for replay
- **Pure Terraform**: Single IaC tool for entire stack

## Quick Start

### Prerequisites

- AWS CLI configured
- Terraform >= 1.0
- Python 3.13 (for Lambda runtime)
- DevOps Agent webhook URL and secret

### Deploy

1. **Configure variables**:
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your webhook credentials
```

2. **Deploy infrastructure**:
```bash
terraform init
terraform plan
terraform apply
```

3. **Done!** EventBridge automatically captures all alarm state changes.

### Important: Application Insights Compatibility

If your alarms are managed by CloudWatch Application Insights (like the example alarms), Application Insights will periodically overwrite any manual changes to alarm actions. This solution uses **EventBridge** instead, which captures alarm state changes without modifying the alarms themselves.

## Configuration

### EventBridge Integration (Recommended)

The solution uses **EventBridge** to capture ALL CloudWatch alarm state changes automatically. This works perfectly with Application Insights-managed alarms since it doesn't require modifying the alarms themselves.

**How it works:**
- EventBridge rule catches any alarm transitioning to ALARM state
- Lambda is triggered automatically
- No need to modify individual alarms or add SNS actions

### Alarm Tags (Optional)

Tag your CloudWatch alarms to control behavior:

- `DevOpsAgentEnabled`: "true" (enable webhook for this alarm)
- `DevOpsAgentPriority`: "HIGH|MEDIUM|LOW" (override default priority)
- `DevOpsAgentService`: "ServiceName" (custom service name for investigation)

Example:
```bash
aws cloudwatch tag-resource \
  --resource-arn arn:aws:cloudwatch:us-west-2:123456789012:alarm:MyAlarm \
  --tags Key=DevOpsAgentEnabled,Value=true \
         Key=DevOpsAgentPriority,Value=HIGH \
         Key=DevOpsAgentService,Value=RetailStore-API
```

### Priority Mapping

Default priority based on alarm type:
- **HIGH**: RDS CPU >90%, DynamoDB SystemErrors, ALB 4XX >70%
- **MEDIUM**: ECS CPU/Memory >90%, NAT Gateway errors
- **LOW**: Capacity warnings

## Testing

Test the Lambda function:
```bash
# Trigger a test alarm
aws sns publish \
  --topic-arn $(terraform output -raw sns_topic_arn) \
  --message file://test-alarm.json

# Monitor logs
aws logs tail $(terraform output -raw lambda_log_group) --follow
```

## Project Structure

```
├── terraform/
│   ├── main.tf              # Provider and data sources
│   ├── lambda.tf            # Lambda function and DLQ
│   ├── sns.tf               # SNS topic and encryption
│   ├── iam.tf               # IAM roles and policies
│   ├── secrets.tf           # Secrets Manager
│   ├── variables.tf         # Input variables
│   ├── outputs.tf           # Stack outputs
│   └── backend.tf           # Remote state config
├── lambda/
│   ├── handler.py           # Main Lambda handler
│   ├── webhook_client.py    # HMAC webhook client
│   ├── context_enricher.py  # Metrics and tags enrichment
│   ├── alarm_parser.py      # SNS message parser
│   └── requirements.txt     # Python dependencies
└── README.md
```

## Cleanup

```bash
cd terraform
terraform destroy
```

## License

MIT-0
