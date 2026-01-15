# Architecture

## Overview

Automated CloudWatch Alarm to AWS DevOps Agent investigation pattern using EventBridge and Lambda.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     AWS Account (Workload)                       │
│                                                                   │
│  ┌──────────────┐                                                │
│  │  CloudWatch  │                                                │
│  │    Alarms    │                                                │
│  │  (Multiple)  │                                                │
│  └──────┬───────┘                                                │
│         │ State Change to ALARM                                  │
│         ▼                                                         │
│  ┌──────────────┐                                                │
│  │  EventBridge │◄─── Captures ALL alarm state changes          │
│  │     Rule     │     No alarm modification needed               │
│  └──────┬───────┘                                                │
│         │ Trigger                                                │
│         ▼                                                         │
│  ┌──────────────────────────────────────────┐                   │
│  │         Lambda Function                   │                   │
│  │  ┌────────────────────────────────────┐  │                   │
│  │  │ 1. Parse alarm (SNS or EventBridge)│  │                   │
│  │  │ 2. Enrich context (tags, priority) │  │                   │
│  │  │ 3. Build webhook payload           │  │                   │
│  │  │ 4. HMAC v1 authentication          │  │                   │
│  │  │ 5. Call DevOps Agent webhook       │  │                   │
│  │  └────────────────────────────────────┘  │                   │
│  │                                            │                   │
│  │  Reads from:                               │                   │
│  │  • Secrets Manager (webhook credentials)  │                   │
│  │  • CloudWatch Tags (per-alarm config)     │                   │
│  │  • Environment Variables (deployment ctx) │                   │
│  └──────┬─────────────────────────────────────┘                   │
│         │                                                         │
│         │ HTTPS POST with HMAC signature                         │
│         ▼                                                         │
└─────────┼─────────────────────────────────────────────────────────┘
          │
          │ Cross-Account
          ▼
┌─────────────────────────────────────────────────────────────────┐
│              AWS DevOps Agent (Separate Account)                 │
│                                                                   │
│  ┌──────────────┐                                                │
│  │   Webhook    │                                                │
│  │   Endpoint   │                                                │
│  └──────┬───────┘                                                │
│         │                                                         │
│         ▼                                                         │
│  ┌──────────────┐                                                │
│  │ Investigation│◄─── Uses runbook for deployment                │
│  │   Created    │     Investigates in workload account           │
│  └──────────────┘                                                │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. EventBridge Rule
- **Purpose**: Capture all CloudWatch alarm state changes to ALARM
- **Benefit**: No need to modify individual alarms
- **Compatible**: Works with Application Insights-managed alarms

### 2. Lambda Function
- **Runtime**: Python 3.13
- **Timeout**: 60 seconds
- **Memory**: 256 MB
- **Modules**:
  - `handler.py` - Event routing (SNS/EventBridge)
  - `alarm_parser.py` - Parse alarm data
  - `context_enricher.py` - Tag lookup, priority mapping
  - `webhook_client.py` - HMAC auth, HTTP POST

### 3. Secrets Manager
- **Purpose**: Store webhook URL and secret
- **Security**: Encrypted at rest, IAM-controlled access
- **Rotation**: Supports manual rotation

### 4. Dead Letter Queue (SQS)
- **Purpose**: Capture failed Lambda invocations
- **Retention**: 14 days
- **Use**: Replay failed webhook calls

### 5. CloudWatch Logs
- **Retention**: 7 days
- **Content**: Full audit trail with payloads
- **Queries**: Filter for specific alarms or payloads

## Data Flow

1. **Alarm triggers** → State changes to ALARM
2. **EventBridge captures** → Sends event to Lambda
3. **Lambda parses** → Extracts alarm details
4. **Lambda enriches** → Adds tags, priority, service name
5. **Lambda builds payload** → Structured investigation request
6. **Lambda signs** → HMAC SHA-256 signature
7. **Lambda sends** → HTTPS POST to DevOps Agent
8. **DevOps Agent** → Creates investigation with context

## Security

- **Encryption**: SNS topic encrypted with KMS
- **Secrets**: Webhook credentials in Secrets Manager
- **IAM**: Least-privilege policies
- **Authentication**: HMAC v1 with timestamp replay protection
- **Audit**: Full CloudWatch Logs trail

## Scalability

- **Lambda**: Auto-scales with alarm volume
- **EventBridge**: Handles unlimited alarms
- **Cost**: Pay-per-invocation (typically <$1/month)
- **Latency**: <1 second from alarm to webhook

## Reliability

- **Dead Letter Queue**: Failed invocations captured
- **Retry**: Lambda automatic retry (2 attempts)
- **Idempotency**: Investigation ID includes timestamp
- **Monitoring**: CloudWatch metrics on Lambda
