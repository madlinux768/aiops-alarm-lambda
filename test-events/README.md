# Test Events

Sample EventBridge events for testing the Lambda function without triggering real alarms.

## Usage

### Test with dry-run mode (no webhook call):

```bash
# Enable dry-run in terraform.tfvars
dry_run_mode = true
terraform apply

# Invoke Lambda with test event
aws lambda invoke \
  --function-name devops-agent-webhook-handler \
  --region us-west-2 \
  --payload file://test-events/eventbridge-alb-4xx.json \
  /tmp/response.json

# View the response
cat /tmp/response.json

# Check logs for full payload
aws logs tail /aws/lambda/devops-agent-webhook-handler --region us-west-2 --since 1m
```

### Test with real webhook call:

```bash
# Disable dry-run
dry_run_mode = false
terraform apply

# Invoke Lambda (will create real investigation)
aws lambda invoke \
  --function-name devops-agent-webhook-handler \
  --region us-west-2 \
  --payload file://test-events/eventbridge-rds-cpu.json \
  /tmp/response.json
```

## Available Test Events

- `eventbridge-alb-4xx.json` - ALB 4XX error rate alarm
- `eventbridge-rds-cpu.json` - RDS CPU utilization alarm

## Creating New Test Events

1. Trigger a real alarm or use `set-alarm-state`
2. Check Lambda logs for "Full EventBridge event"
3. Copy the JSON and save as new test event file
