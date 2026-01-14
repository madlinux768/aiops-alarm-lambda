# SNS Topic for CloudWatch Alarms
resource "aws_sns_topic" "alarm_notifications" {
  name              = "${var.project_name}-alarms"
  display_name      = "DevOps Agent Webhook Alarm Notifications"
  kms_master_key_id = aws_kms_key.sns.id

  tags = {
    Name = "${var.project_name}-alarms"
  }
}

# SNS Topic Policy
resource "aws_sns_topic_policy" "alarm_notifications" {
  arn = aws_sns_topic.alarm_notifications.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudWatchAlarms"
        Effect = "Allow"
        Principal = {
          Service = "cloudwatch.amazonaws.com"
        }
        Action   = "SNS:Publish"
        Resource = aws_sns_topic.alarm_notifications.arn
      }
    ]
  })
}

# SNS Subscription to Lambda
resource "aws_sns_topic_subscription" "lambda" {
  topic_arn = aws_sns_topic.alarm_notifications.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.webhook_handler.arn
}

# KMS Key for SNS encryption
resource "aws_kms_key" "sns" {
  description             = "KMS key for SNS topic encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = {
    Name = "${var.project_name}-sns-key"
  }
}

resource "aws_kms_alias" "sns" {
  name          = "alias/${var.project_name}-sns"
  target_key_id = aws_kms_key.sns.key_id
}
