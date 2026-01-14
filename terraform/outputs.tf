output "sns_topic_arn" {
  description = "ARN of SNS topic for CloudWatch alarm actions"
  value       = aws_sns_topic.alarm_notifications.arn
}

output "lambda_function_name" {
  description = "Name of Lambda function"
  value       = aws_lambda_function.webhook_handler.function_name
}

output "lambda_log_group" {
  description = "CloudWatch log group for Lambda"
  value       = aws_cloudwatch_log_group.lambda.name
}

output "dlq_url" {
  description = "URL of Dead Letter Queue"
  value       = aws_sqs_queue.dlq.url
}

output "secret_arn" {
  description = "ARN of Secrets Manager secret"
  value       = aws_secretsmanager_secret.webhook_credentials.arn
}

output "instructions" {
  description = "Next steps"
  value       = <<-EOT
    
    Deployment complete! ${var.dry_run_mode ? "🔵 DRY-RUN MODE ENABLED" : "✓ Production mode"}
    
    ${var.dry_run_mode ? "Webhook payloads will be logged but NOT sent to DevOps Agent.\nTo disable dry-run: set dry_run_mode=false and terraform apply\n" : ""}1. EventBridge automatically captures all alarm state changes
    
    2. Tag alarms to customize behavior (optional):
       aws cloudwatch tag-resource \
         --resource-arn <ALARM_ARN> \
         --tags Key=DevOpsAgentEnabled,Value=true \
                Key=DevOpsAgentPriority,Value=HIGH \
                Key=DevOpsAgentService,Value=YourService
    
    3. Test by triggering an alarm or use set-alarm-state:
       aws cloudwatch set-alarm-state --alarm-name <ALARM_NAME> \
         --state-value ALARM --state-reason "Test trigger"
    
    4. Monitor Lambda logs:
       aws logs tail ${aws_cloudwatch_log_group.lambda.name} --follow
    
    5. Query webhook payloads:
       aws logs filter-log-events \
         --log-group-name ${aws_cloudwatch_log_group.lambda.name} \
         --filter-pattern "Full webhook payload"
  EOT
}
