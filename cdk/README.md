# CDK Deployment Option

AWS CDK (Python) implementation of the DevOps Agent webhook integration pattern.

## Prerequisites

- Python 3.9+
- AWS CDK CLI: `npm install -g aws-cdk`
- AWS CLI configured

## Setup

1. **Create virtual environment**:
```bash
cd cdk
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure context**:
```bash
cp cdk.context.json.example cdk.context.json
# Edit cdk.context.json with your values
```

## Deploy

```bash
# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy stack
cdk deploy
```

## Configuration

### Option 1: Context File (Recommended)

Edit `cdk.context.json`:
```json
{
  "deployment_name": "production-api",
  "deployment_description": "Production API deployment",
  "default_priority": "MEDIUM",
  "dry_run_mode": false,
  "webhook_url": "https://...",
  "webhook_secret": "...",
  "region": "us-west-2",
  "account": "123456789012"
}
```

### Option 2: Command Line

```bash
cdk deploy \
  -c deployment_name="production-api" \
  -c deployment_description="Production API" \
  -c default_priority="MEDIUM" \
  -c dry_run_mode=false \
  -c webhook_url="https://..." \
  -c webhook_secret="..." \
  -c region="us-west-2"
```

## Testing

### Dry-Run Mode

```bash
cdk deploy -c dry_run_mode=true
```

### Diff Changes

```bash
cdk diff
```

### Synthesize CloudFormation

```bash
cdk synth
```

## Cleanup

```bash
cdk destroy
```

## CDK vs Terraform

Both implementations are functionally identical:

| Feature | CDK | Terraform |
|---------|-----|-----------|
| Language | Python | HCL |
| State Management | CloudFormation | Terraform State |
| Type Safety | Strong (Python) | Moderate (HCL) |
| AWS Native | Yes | No |
| Learning Curve | Moderate | Low |
| Ecosystem | AWS-focused | Multi-cloud |

**Choose CDK if:**
- You prefer Python over HCL
- Your team uses CDK for other infrastructure
- You want AWS-native tooling

**Choose Terraform if:**
- You prefer declarative HCL
- You use Terraform for other infrastructure
- You need multi-cloud support

## Structure

```
cdk/
├── app.py                  # CDK app entry point
├── stacks/
│   └── webhook_stack.py    # Main stack definition
├── cdk.json                # CDK configuration
├── cdk.context.json        # Your configuration (gitignored)
├── requirements.txt        # Python dependencies
└── README.md
```

## Notes

- Lambda code is shared with Terraform implementation (../lambda)
- Both deployments can coexist in different accounts/regions
- CDK generates CloudFormation templates
- Stack name: `DevOpsAgentWebhookStack`
