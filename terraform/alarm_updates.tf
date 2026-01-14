# Update existing CloudWatch alarms with SNS topic action
# Note: These alarms are managed by Application Insights and WILL be overwritten
# Use EventBridge integration instead (see eventbridge.tf)

# Application Insights automatically manages these alarms and will remove
# any manual changes. The EventBridge rule in eventbridge.tf provides a
# better solution by catching ALL alarm state changes without modifying alarms.
