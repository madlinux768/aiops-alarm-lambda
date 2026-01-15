#!/usr/bin/env python3
"""CDK app for DevOps Agent webhook integration."""
import aws_cdk as cdk
from stacks.webhook_stack import DevOpsAgentWebhookStack

app = cdk.App()

# Get context values
deployment_name = app.node.try_get_context("deployment_name") or ""
deployment_description = app.node.try_get_context("deployment_description") or ""
default_priority = app.node.try_get_context("default_priority") or "MEDIUM"
dry_run_mode = app.node.try_get_context("dry_run_mode") or False
webhook_url = app.node.try_get_context("webhook_url")
webhook_secret = app.node.try_get_context("webhook_secret")

if not webhook_url or not webhook_secret:
    raise ValueError("webhook_url and webhook_secret must be provided in cdk.context.json or via -c flags")

DevOpsAgentWebhookStack(
    app,
    "DevOpsAgentWebhookStack",
    deployment_name=deployment_name,
    deployment_description=deployment_description,
    default_priority=default_priority,
    dry_run_mode=dry_run_mode,
    webhook_url=webhook_url,
    webhook_secret=webhook_secret,
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-west-2"
    ),
    tags={
        "Project": "DevOpsAgentWebhook",
        "Environment": "Prod",
        "ManagedBy": "CDK",
        "auto-delete": "no"
    }
)

app.synth()
