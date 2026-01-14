# EventBridge rule to catch CloudWatch alarm state changes
# This bypasses the need to modify Application Insights-managed alarms

resource "aws_cloudwatch_event_rule" "alarm_state_change" {
  name        = "${var.project_name}-alarm-state-change"
  description = "Capture CloudWatch alarm state changes to ALARM"

  event_pattern = jsonencode({
    source      = ["aws.cloudwatch"]
    detail-type = ["CloudWatch Alarm State Change"]
    detail = {
      state = {
        value = ["ALARM"]
      }
    }
  })

  tags = {
    Name = "${var.project_name}-alarm-rule"
  }
}

resource "aws_cloudwatch_event_target" "lambda" {
  rule      = aws_cloudwatch_event_rule.alarm_state_change.name
  target_id = "DevOpsAgentWebhookLambda"
  arn       = aws_lambda_function.webhook_handler.arn
}

resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.webhook_handler.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.alarm_state_change.arn
}
