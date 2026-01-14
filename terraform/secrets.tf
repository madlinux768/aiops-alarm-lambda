# Secrets Manager for webhook credentials
resource "aws_secretsmanager_secret" "webhook_credentials" {
  name                    = "${var.project_name}-credentials"
  description             = "DevOps Agent webhook URL and secret for HMAC authentication"
  recovery_window_in_days = 7

  tags = {
    Name = "${var.project_name}-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "webhook_credentials" {
  secret_id = aws_secretsmanager_secret.webhook_credentials.id
  secret_string = jsonencode({
    url    = var.webhook_url
    secret = var.webhook_secret
  })
}
