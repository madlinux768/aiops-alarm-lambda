variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-west-2"
}

variable "webhook_url" {
  description = "DevOps Agent webhook URL"
  type        = string
  sensitive   = true
}

variable "webhook_secret" {
  description = "DevOps Agent webhook secret for HMAC signing"
  type        = string
  sensitive   = true
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "devops-agent-webhook"
}

variable "enable_alarm_updates" {
  description = "Whether to update existing CloudWatch alarms with SNS topic"
  type        = bool
  default     = false
}
