# Deployment Guide

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform >= 1.0
- DevOps Agent webhook URL and secret
- CloudWatch alarms already configured in your account

## Deployment Scenarios

### Scenario 1: New Deployment (Recommended)

For customers starting fresh or adding to existing infrastructure.

**Steps:**

1. **Clone the repository**:
```bash
git clone https://github.com/madlinux768/aiops-alarm-lambda.git
cd aiops-alarm-lambda
```

2. **Configure variables**:
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
aws_region     = "us-west-2"  # Your region
project_name   = "devops-agent-webhook"

# Your deployment context
deployment_name        = "production-api"
deployment_description = "Production API with ECS, RDS, and ElastiCache"

# DevOps Agent webhook credentials
webhook_url    = "https://event-ai.us-east-1.api.aws/webhook/generic/YOUR_ID"
webhook_secret = "YOUR_SECRET"

# Testing mode
dry_run_mode = true  # Start with dry-run for testing
```

3. **Deploy infrastructure**:
```bash
terraform init
terraform plan
terraform apply
```

4. **Test with dry-run**:
```bash
# Trigger a test alarm
aws cloudwatch set-alarm-state \
  --alarm-name "YourAlarmName" \
  --state-value ALARM \
  --state-reason "Test trigger"

# Check logs for payload
aws logs tail /aws/lambda/devops-agent-webhook-handler --follow
```

5. **Enable production mode**:
```bash
# Edit terraform.tfvars
dry_run_mode = false

# Apply changes
terraform apply
```

---

### Scenario 2: Application Insights Integration

For customers using CloudWatch Application Insights (like the reference implementation).

**Challenge**: Application Insights manages alarms and overwrites manual changes.

**Solution**: This pattern uses EventBridge, which doesn't require modifying alarms.

**Steps:**

1. Deploy as in Scenario 1
2. No additional configuration needed!
3. EventBridge automatically captures all Application Insights alarms

**Note**: Application Insights alarms have limited metadata in EventBridge events. The Lambda extracts what's available and DevOps Agent fills in the rest during investigation.

---

### Scenario 3: Multi-Region Deployment

Deploy the pattern in multiple regions to handle regional alarms.

**Steps:**

1. **Deploy in primary region**:
```bash
cd terraform
terraform workspace new us-west-2
terraform apply -var="aws_region=us-west-2"
```

2. **Deploy in secondary region**:
```bash
terraform workspace new us-east-1
terraform apply -var="aws_region=us-east-1"
```

**Note**: Each region needs its own Lambda function and EventBridge rule. Use Terraform workspaces or separate state files.

---

### Scenario 4: Existing SNS Topic Integration

If you already have CloudWatch alarms sending to an SNS topic.

**Steps:**

1. Deploy the infrastructure
2. Add Lambda as SNS subscriber:
```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:REGION:ACCOUNT:your-existing-topic \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:REGION:ACCOUNT:function:devops-agent-webhook-handler
```

3. Grant SNS permission:
```bash
aws lambda add-permission \
  --function-name devops-agent-webhook-handler \
  --statement-id AllowSNSInvoke \
  --action lambda:InvokeFunction \
  --principal sns.amazonaws.com \
  --source-arn arn:aws:sns:REGION:ACCOUNT:your-existing-topic
```

---

## Post-Deployment

### Verify Deployment

```bash
# Check Lambda function
aws lambda get-function --function-name devops-agent-webhook-handler

# Check EventBridge rule
aws events list-rules --name-prefix devops-agent-webhook

# Check EventBridge targets
aws events list-targets-by-rule --rule devops-agent-webhook-alarm-state-change
```

### Test End-to-End

```bash
# Use test event file
aws lambda invoke \
  --function-name devops-agent-webhook-handler \
  --payload file://test-events/eventbridge-alb-4xx.json \
  /tmp/response.json

# Check response
cat /tmp/response.json

# Check logs
aws logs tail /aws/lambda/devops-agent-webhook-handler --since 2m
```

### Monitor Operations

```bash
# View recent invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=devops-agent-webhook-handler \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# Check for errors
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=devops-agent-webhook-handler \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# Check DLQ for failed invocations
aws sqs get-queue-attributes \
  --queue-url $(terraform output -raw dlq_url) \
  --attribute-names ApproximateNumberOfMessages
```

## Troubleshooting

### Lambda not triggering

```bash
# Check EventBridge rule is enabled
aws events describe-rule --name devops-agent-webhook-alarm-state-change

# Check Lambda has EventBridge permission
aws lambda get-policy --function-name devops-agent-webhook-handler
```

### Webhook failing

```bash
# Check Secrets Manager
aws secretsmanager get-secret-value --secret-id devops-agent-webhook-credentials

# Check Lambda logs for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/devops-agent-webhook-handler \
  --filter-pattern "ERROR"
```

### Investigation not created

```bash
# Verify webhook was called
aws logs filter-log-events \
  --log-group-name /aws/lambda/devops-agent-webhook-handler \
  --filter-pattern "Webhook sent successfully"

# Check payload format
aws logs filter-log-events \
  --log-group-name /aws/lambda/devops-agent-webhook-handler \
  --filter-pattern "Full webhook payload"
```

## Cleanup

```bash
cd terraform
terraform destroy
```

**Note**: This will delete all resources including logs. Export logs first if needed.
