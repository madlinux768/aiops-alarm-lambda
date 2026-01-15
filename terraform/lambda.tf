# Lambda Function
resource "aws_lambda_function" "webhook_handler" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${var.project_name}-handler"
  role             = aws_iam_role.lambda.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime          = "python3.13"
  timeout          = 60
  memory_size      = 256

  environment {
    variables = {
      SECRET_ARN             = aws_secretsmanager_secret.webhook_credentials.arn
      LOG_LEVEL              = "INFO"
      DRY_RUN                = var.dry_run_mode ? "true" : "false"
      DEPLOYMENT_NAME        = var.deployment_name
      DEPLOYMENT_DESCRIPTION = var.deployment_description
      DEFAULT_PRIORITY       = var.default_priority
    }
  }

  dead_letter_config {
    target_arn = aws_sqs_queue.dlq.arn
  }

  tags = {
    Name = "${var.project_name}-handler"
  }

  depends_on = [
    aws_iam_role_policy.lambda
  ]
}

# Lambda permission for SNS
resource "aws_lambda_permission" "sns" {
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.webhook_handler.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.alarm_notifications.arn
}

# Package Lambda code
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda"
  output_path = "${path.module}/.terraform/lambda.zip"
}

# Dead Letter Queue
resource "aws_sqs_queue" "dlq" {
  name                      = "${var.project_name}-dlq"
  message_retention_seconds = 1209600 # 14 days
  kms_master_key_id         = "alias/aws/sqs"

  tags = {
    Name = "${var.project_name}-dlq"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project_name}-handler"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-logs"
  }
}
