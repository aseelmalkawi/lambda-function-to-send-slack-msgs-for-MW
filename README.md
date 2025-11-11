# AWS Systems Manager Maintenance Window Slack Notifier

This Lambda function sends Slack notifications when AWS Systems Manager Maintenance Window executions complete, providing detailed status updates including success/failure counts.

## Overview

The function is triggered by EventBridge when a Maintenance Window execution changes state. It retrieves execution details from SSM and posts a formatted message to Slack with the execution status and results.

## Architecture

```
EventBridge Rule (Maintenance Window Execution State-change Notification)
         ↓
    Lambda Function
         ↓
   Slack Webhook
```

## EventBridge Rule Pattern

You can filter for other statuses, but MWs end with these.

```json
{
  "source": ["aws.ssm"],
  "detail-type": ["Maintenance Window Execution State-change Notification"],
  "detail": {
    "status": ["SUCCESS", "FAILED", "TIMED_OUT", "CANCELLED"]
  }
}
```

## Lambda Function Features

- Retrieves maintenance window name from window ID
- Fetches execution task and invocation details
- Counts total targets and failed targets
- Formats and sends structured Slack notifications
- Includes execution metadata (region, start/end times, status)

## Required IAM Permissions

### Lambda Execution Role

The Lambda function requires the following IAM policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudWatchLogsAccess",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Sid": "SSMReadAccess",
      "Effect": "Allow",
      "Action": [
        "ssm:DescribeMaintenanceWindows",
        "ssm:DescribeMaintenanceWindowExecutionTasks",
        "ssm:DescribeMaintenanceWindowExecutionTaskInvocations",
        "ssm:ListCommands"
      ],
      "Resource": "*"
    }
  ]
}
```

### EventBridge Rule Permissions

EventBridge needs permission to invoke the Lambda function. This is automatically configured when you add the Lambda as a target, but the equivalent policy is:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowEventBridgeInvoke",
      "Effect": "Allow",
      "Principal": {
        "Service": "events.amazonaws.com"
      },
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:REGION:ACCOUNT_ID:function:FUNCTION_NAME",
      "Condition": {
        "ArnLike": {
          "AWS:SourceArn": "arn:aws:events:REGION:ACCOUNT_ID:rule/RULE_NAME"
        }
      }
    }
  ]
}
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SLACK_WEBHOOK_URL` | Slack incoming webhook URL | Yes |

> **⚠️ Security Note:** Consider moving the Slack webhook URL to AWS Secrets Manager or Lambda environment variables for better security.

## Deployment

### Prerequisites

- AWS CLI configured with appropriate credentials (for programmatic use if wanted)
- Slack incoming webhook URL
- Existing SSM Maintenance Window(s)

### Step 1: Create Lambda Function

1. Create a new Lambda function in the AWS Console
2. Runtime: Python 3.9 or later
3. Copy the provided Lambda code
4. Set the timeout to at least 30 seconds
5. Attach the IAM role with the permissions listed above

### Step 2: Add Lambda Layer (if needed)

The `urllib3` library is included in the Lambda Python runtime, so no additional layers are required.

### Step 3: Create EventBridge Rule

1. Navigate to Amazon EventBridge in the AWS Console
2. Create a new rule with the event pattern shown above
3. Add the Lambda function as a target

### Step 4: Configure Slack Webhook

1. Create an incoming webhook in your Slack workspace via the Slack API portal. Might ned approval from Slack admins.
2. Update the `SLACK_WEBHOOK_URL` in the Lambda code or use environment variables

## Slack Notification Format

The function sends formatted Slack messages with the following information:

```
🛠 Maintenance Window Execution Update
• Account: RxSense
• Region: us-east-1
• Maintenance Window: Weekly Patching Window
• Execution ID: `abc123-def456-ghi789`
• Status: SUCCESS
• Started At: 2025-11-11T10:00:00Z
• Ended At: 2025-11-11T10:30:00Z
• Tasks failed: 0/10 failed
```

## Troubleshooting

### Lambda Function Errors

- **Permission Denied**: Verify IAM role has all required SSM permissions
- **Timeout**: Increase Lambda timeout if dealing with large maintenance windows, or optimise the code to take less time
- **Slack Message Failed**: Verify webhook URL is correct and accessible

### No Notifications Received

- Check if the EventBridge rule is enabled. The event used specifically is the one that triggers EventBridge when the MW changes statuses.
- Verify the Lambda function has a resource-based policy allowing EventBridge invocation
- Check CloudWatch Logs for Lambda execution errors

## Sample Event

Example EventBridge event payload that triggers the Lambda function:

```json
{
  "version": "0",
  "id": "12345678-1234-1234-1234-123456789012",
  "detail-type": "Maintenance Window Execution State-change Notification",
  "source": "aws.ssm",
  "account": "123456789012",
  "time": "2025-11-11T10:30:00Z",
  "region": "us-east-1",
  "resources": [],
  "detail": {
    "window-execution-id": "abc123-def456-ghi789",
    "window-id": "mw-0123456789abcdef",
    "status": "SUCCESS",
    "start-time": "2025-11-11T10:00:00Z",
    "end-time": "2025-11-11T10:30:00Z"
  }
}
```

You need to retrieve the data exactly by its name in JSON. Refer to AWS EventBridge docs to ensure attribute names.

## Dependencies

- `boto3`: AWS SDK for Python (included in Lambda runtime)
- `urllib3`: HTTP client for Slack webhook calls (included in Lambda runtime)

## Security Best Practices

1. **Secrets Management**: Store Slack webhook URL in AWS Secrets Manager
2. **Least Privilege**: Restrict IAM permissions to specific maintenance windows if possible
3. **VPC Configuration**: Consider deploying Lambda in VPC if accessing private resources
4. **Encryption**: Enable encryption at rest for Lambda environment variables

## Cost Considerations

- Lambda invocations: One per maintenance window execution
- CloudWatch Logs: Storage for Lambda execution logs
- EventBridge: No additional cost for rule evaluations
