"""CDK stack for DevOps Agent webhook integration."""
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    SecretValue,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_sqs as sqs,
    aws_kms as kms,
    aws_secretsmanager as secretsmanager,
    aws_events as events,
    aws_events_targets as targets,
    aws_logs as logs,
    CfnOutput
)
from constructs import Construct
import json


class DevOpsAgentWebhookStack(Stack):
    """Stack for CloudWatch Alarm to DevOps Agent webhook integration."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        deployment_name: str,
        deployment_description: str,
        default_priority: str,
        dry_run_mode: bool,
        webhook_url: str,
        webhook_secret: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # KMS key for SNS encryption
        sns_key = kms.Key(
            self, "SNSKey",
            description="KMS key for SNS topic encryption",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.DESTROY
        )

        # SNS Topic for alarm notifications (optional integration)
        alarm_topic = sns.Topic(
            self, "AlarmTopic",
            display_name="DevOps Agent Webhook Alarm Notifications",
            master_key=sns_key
        )

        # Allow CloudWatch to publish
        alarm_topic.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowCloudWatchAlarms",
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("cloudwatch.amazonaws.com")],
                actions=["SNS:Publish"],
                resources=[alarm_topic.topic_arn]
            )
        )

        # Dead Letter Queue
        dlq = sqs.Queue(
            self, "DLQ",
            queue_name="devops-agent-webhook-dlq",
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.KMS_MANAGED
        )

        # Secrets Manager for webhook credentials
        webhook_secret_obj = secretsmanager.Secret(
            self, "WebhookCredentials",
            secret_name="devops-agent-webhook-cdk-credentials",
            description="DevOps Agent webhook URL and secret for HMAC authentication",
            secret_string_value=SecretValue.unsafe_plain_text(
                json.dumps({"url": webhook_url, "secret": webhook_secret})
            )
        )

        # Lambda function
        webhook_function = lambda_.Function(
            self, "WebhookHandler",
            function_name="devops-agent-webhook-handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("../lambda"),
            timeout=Duration.seconds(60),
            memory_size=256,
            environment={
                "SECRET_ARN": webhook_secret_obj.secret_arn,
                "LOG_LEVEL": "INFO",
                "DRY_RUN": "true" if dry_run_mode else "false",
                "DEPLOYMENT_NAME": deployment_name,
                "DEPLOYMENT_DESCRIPTION": deployment_description,
                "DEFAULT_PRIORITY": default_priority
            },
            dead_letter_queue=dlq,
            log_retention=logs.RetentionDays.ONE_WEEK
        )

        # Grant Lambda permissions
        webhook_secret_obj.grant_read(webhook_function)
        
        webhook_function.add_to_role_policy(
            iam.PolicyStatement(
                sid="CloudWatchMetrics",
                effect=iam.Effect.ALLOW,
                actions=[
                    "cloudwatch:GetMetricStatistics",
                    "cloudwatch:GetMetricData"
                ],
                resources=["*"]
            )
        )
        
        webhook_function.add_to_role_policy(
            iam.PolicyStatement(
                sid="ResourceTagging",
                effect=iam.Effect.ALLOW,
                actions=[
                    "tag:GetResources",
                    "cloudwatch:ListTagsForResource"
                ],
                resources=["*"]
            )
        )

        dlq.grant_send_messages(webhook_function)

        # SNS subscription (optional)
        alarm_topic.add_subscription(
            subs.LambdaSubscription(webhook_function)
        )

        # EventBridge rule for alarm state changes
        alarm_rule = events.Rule(
            self, "AlarmStateChangeRule",
            rule_name="devops-agent-webhook-alarm-state-change",
            description="Capture CloudWatch alarm state changes to ALARM",
            event_pattern=events.EventPattern(
                source=["aws.cloudwatch"],
                detail_type=["CloudWatch Alarm State Change"],
                detail={
                    "state": {
                        "value": ["ALARM"]
                    }
                }
            )
        )

        alarm_rule.add_target(targets.LambdaFunction(webhook_function))

        # Outputs
        CfnOutput(
            self, "SNSTopicArn",
            value=alarm_topic.topic_arn,
            description="ARN of SNS topic for CloudWatch alarm actions"
        )

        CfnOutput(
            self, "LambdaFunctionName",
            value=webhook_function.function_name,
            description="Name of Lambda function"
        )

        CfnOutput(
            self, "LambdaLogGroup",
            value=webhook_function.log_group.log_group_name,
            description="CloudWatch log group for Lambda"
        )

        CfnOutput(
            self, "DLQUrl",
            value=dlq.queue_url,
            description="URL of Dead Letter Queue"
        )

        CfnOutput(
            self, "SecretArn",
            value=webhook_secret_obj.secret_arn,
            description="ARN of Secrets Manager secret"
        )

        mode_msg = "🔵 DRY-RUN MODE" if dry_run_mode else "✓ Production mode"
        CfnOutput(
            self, "Instructions",
            value=f"""
Deployment complete! {mode_msg}

1. EventBridge automatically captures all alarm state changes

2. Tag alarms to customize behavior (optional):
   aws cloudwatch tag-resource --resource-arn <ALARM_ARN> \\
     --tags Key=DevOpsAgentEnabled,Value=true \\
            Key=DevOpsAgentPriority,Value=HIGH \\
            Key=DevOpsAgentService,Value=YourService

3. Test: aws cloudwatch set-alarm-state --alarm-name <ALARM_NAME> \\
     --state-value ALARM --state-reason "Test trigger"

4. Monitor: aws logs tail {webhook_function.log_group.log_group_name} --follow
""",
            description="Next steps"
        )
