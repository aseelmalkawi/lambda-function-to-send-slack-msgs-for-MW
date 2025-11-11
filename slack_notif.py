import json
import urllib3
import boto3
from datetime import datetime, timedelta

http = urllib3.PoolManager()
ssm = boto3.client('ssm')
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/your_url"

def lambda_handler(event, context):
    details = event.get("detail", {})
    region = event.get("region", {})
    window_execution_id = details.get("window-execution-id")
    window_id = details.get("window-id")
    status = details.get('status', 'UNKNOWN')
    start_time = details.get("start-time", "UNKNOWN")
    end_time = details.get("end-time", "UNKNOWN")
  
    # mw name
    resp = ssm.describe_maintenance_windows()
    id_to_name = {w['WindowId']: w['Name'] for w in resp['WindowIdentities']}
    window_name = id_to_name.get(window_id, 'Unknown')
  
    # targets totals
    # 1. querying the task_id inside the mw exec
    task_id = ssm.describe_maintenance_window_execution_tasks(
    WindowExecutionId=window_execution_id
    )['WindowExecutionTaskIdentities'][0]['TaskExecutionId']
  
    # 2. querying the invocation inside it
    invocations = ssm.describe_maintenance_window_execution_task_invocations(
        WindowExecutionId=window_execution_id,
        TaskId=task_id
    )['WindowExecutionTaskInvocationIdentities']
  
    # 3. fetching the command ID inside the invocation
    command_id = invocations[0]['ExecutionId']
    # 4. fetching the data attached to the run command
    resp = ssm.list_commands(CommandId=command_id)
    cmd = resp['Commands'][0]
    total = cmd.get('TargetCount', 0)
    failed = cmd.get('ErrorCount', 0)
    print(f"Command: {command_id}, Status: {cmd['Status']}, Targets: {cmd['TargetCount']}, Errors: {cmd['ErrorCount']}")

    # Slack message
    slack_message = {
        "text": (
            f"🛠 *Maintenance Window Execution Update*\n"
            f"• *Account:* RxSense\n"
            f"• *Region:* {region}\n"
            f"• *Maintenance Window:* {window_name}\n"
            f"• *Execution ID:* {window_execution_id}\n"
            f"• *Status:* *{status}*\n"
            f"• *Started At:* {start_time}\n"
            f"• *Ended At:* {end_time}\n"
            # f"• *Tasks:* {instance_count}"
            f"• *Tasks failed:* {failed}/{total} failed"
        )
    }
    try:
        http.request(
            "POST",
            SLACK_WEBHOOK_URL,
            body=json.dumps(slack_message),
            headers={"Content-Type": "application/json"}
        )
    except Exception as e:
        return {"statusCode": 500, "body": f"Error sending Slack message: {e}"}
    return {"statusCode": 200, "body": "Slack message sent successfully"}
