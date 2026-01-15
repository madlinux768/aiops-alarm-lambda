# CloudWatch Alarm to AWS DevOps Agent Integration

**Reference pattern** for automatically creating AWS DevOps Agent investigations from CloudWatch alarms using EventBridge, Lambda, and Terraform.

## Overview

This pattern enables automatic incident investigation by triggering AWS DevOps Agent webhooks when CloudWatch alarms enter ALARM state. Works with any CloudWatch alarm including those managed by Application Insights.

## Features

- **Zero alarm modification** - EventBridge captures all alarm state changes
- **Application Insights compatible** - Works with managed alarms
- **HMAC v1 authentication** - Production-ready security
- **Tag-based configuration** - Customize per-alarm behavior
- **Dry-run mode** - Test without consuming investigation quota
- **Comprehensive logging** - Full audit trail with payloads
- **Pure Terraform** - Single IaC tool for entire stack

## Architecture

```
CloudWatch Alarms → EventBridge → Lambda → DevOps Agent Webhook → Investigation
```

See [Architecture Documentation](docs/ARCHITECTURE.md) for detailed diagrams and component descriptions.

## Quick Start

### Option 1: Terraform (Recommended)

1. **Configure deployment**:
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit with your webhook credentials and deployment context
```

2. **Deploy**:
```bash
terraform init
terraform apply
```

### Option 2: AWS CDK (Python)

1. **Setup**:
```bash
cd cdk
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp cdk.context.json.example cdk.context.json
# Edit cdk.context.json with your values
```

2. **Deploy**:
```bash
cdk bootstrap  # First time only
cdk deploy
```

See [CDK README](cdk/README.md) for detailed CDK instructions.

---

**Done!** All alarms automatically trigger investigations when entering ALARM state.

See [Deployment Guide](docs/DEPLOYMENT.md) for detailed scenarios and [Customization Guide](docs/CUSTOMIZATION.md) for advanced configuration.

## Configuration

### Deployment Context

Provide context about your deployment in `terraform.tfvars`:

```hcl
deployment_name        = "production-api"
deployment_description = "Production API with ECS, RDS, and DynamoDB"
default_priority       = "MEDIUM"
```

### Per-Alarm Customization

Tag alarms to control behavior:

```bash
aws cloudwatch tag-resource \
  --resource-arn <ALARM_ARN> \
  --tags Key=DevOpsAgentEnabled,Value=true \
         Key=DevOpsAgentPriority,Value=HIGH \
         Key=DevOpsAgentService,Value=PaymentService
```

**Available Tags:**
- `DevOpsAgentEnabled`: "true|false" - Enable/disable webhook for this alarm
- `DevOpsAgentPriority`: "HIGH|MEDIUM|LOW" - Override default priority
- `DevOpsAgentService`: "ServiceName" - Custom service name for investigation

### Priority Mapping

Default priority rules (customizable):
- **HIGH**: RDS CPU, DynamoDB SystemErrors, ALB 4XX, Lambda Errors
- **MEDIUM**: ECS CPU/Memory, ALB 5XX, NAT Gateway errors
- **LOW/DEFAULT**: Everything else

## Testing

### Dry-Run Mode

Test without creating investigations:

```hcl
# terraform.tfvars
dry_run_mode = true
```

### Test Events

Use sample events without triggering alarms:

```bash
aws lambda invoke \
  --function-name devops-agent-webhook-handler \
  --payload file://test-events/eventbridge-alb-4xx.json \
  /tmp/response.json
```

### Review Payloads

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/devops-agent-webhook-handler \
  --filter-pattern "Full webhook payload"
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - Detailed architecture and data flow
- [Deployment Guide](docs/DEPLOYMENT.md) - Step-by-step deployment for different scenarios
- [Customization Guide](docs/CUSTOMIZATION.md) - Customize for your alarm types and priorities

## Project Structure

```
├── terraform/              # Terraform deployment (Option 1)
│   ├── main.tf            # Provider and data sources
│   ├── lambda.tf          # Lambda function and DLQ
│   ├── eventbridge.tf     # EventBridge rule for alarm capture
│   ├── sns.tf             # SNS topic (optional integration)
│   ├── iam.tf             # IAM roles and policies
│   ├── secrets.tf         # Secrets Manager for webhook credentials
│   ├── variables.tf       # Input variables
│   └── outputs.tf         # Stack outputs
├── cdk/                   # CDK Python deployment (Option 2)
│   ├── app.py             # CDK app entry point
│   ├── stacks/            # CDK stack definitions
│   └── README.md          # CDK-specific instructions
├── lambda/                # Lambda function code (shared)
│   ├── handler.py         # Main handler (SNS/EventBridge routing)
│   ├── webhook_client.py  # HMAC webhook client
│   ├── context_enricher.py # Tag lookup and priority mapping
│   └── alarm_parser.py    # Alarm message parser
├── test-events/           # Sample EventBridge events for testing
├── docs/                  # Documentation
└── README.md
```

## Use Cases

- **Multi-service deployments** - ECS, Lambda, RDS, DynamoDB alarms
- **Application Insights** - Works with managed alarms
- **Multi-region** - Deploy in each region
- **Existing SNS topics** - Integrate with current alarm actions
- **Custom metrics** - Support any CloudWatch namespace

## Requirements

- AWS CLI configured
- Terraform >= 1.0
- Python 3.13 (Lambda runtime)
- DevOps Agent webhook URL and secret
- CloudWatch alarms in your account

## Cost

Typical monthly cost: **<$1**
- Lambda: ~$0.20 (assuming 1000 invocations/month)
- EventBridge: Free (included)
- Secrets Manager: $0.40/secret/month
- CloudWatch Logs: ~$0.50 (7-day retention)

## License

MIT-0
