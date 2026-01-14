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
    
    Deployment complete! Next steps:
    
    1. Add SNS topic to your CloudWatch alarms:
       aws cloudwatch put-metric-alarm --alarm-name <ALARM_NAME> \
         --alarm-actions ${aws_sns_topic.alarm_notifications.arn}
    
    2. Tag alarms to enable webhook (optional):
       aws cloudwatch tag-resource \
         --resource-arn <ALARM_ARN> \
         --tags Key=DevOpsAgentEnabled,Value=true \
                Key=DevOpsAgentPriority,Value=HIGH \
                Key=DevOpsAgentService,Value=YourService
    
    3. Test with a sample alarm:
       aws sns publish --topic-arn ${aws_sns_topic.alarm_notifications.arn} \
         --message file://test-alarm.json
    
    4. Monitor Lambda logs:
       aws logs tail ${aws_cloudwatch_log_group.lambda.name} --follow
  EOT
}
