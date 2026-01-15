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

variable "deployment_name" {
  description = "Deployment name to include in webhook context (e.g., 'retail-store-ecs-mi', 'production-api')"
  type        = string
  default     = ""
}

variable "deployment_description" {
  description = "Optional description of the deployment for webhook context"
  type        = string
  default     = ""
}

variable "default_priority" {
  description = "Default priority for investigations when not specified by tags or rules (HIGH, MEDIUM, LOW)"
  type        = string
  default     = "MEDIUM"
  validation {
    condition     = contains(["HIGH", "MEDIUM", "LOW"], var.default_priority)
    error_message = "Priority must be HIGH, MEDIUM, or LOW"
  }
}

variable "enable_alarm_updates" {
  description = "Whether to update existing CloudWatch alarms with SNS topic"
  type        = bool
  default     = false
}

variable "dry_run_mode" {
  description = "Enable dry-run mode to test without calling DevOps Agent webhook (saves investigation quota)"
  type        = bool
  default     = false
}
