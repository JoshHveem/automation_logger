BEFORE YOU BEGIN
You will need to request a unique automation_id for any new automations
You will also need write rights to the automations.run_log table in the warehouse

CONFIG FILE
Each automation should have a single entry point in that automations folder. Additional helper files are fine. In the same location as the entry point, create automation.config.
automation.config should contain the automation's unique automation_id (see above). No other information is needed at this time.
{
    "automation_id": 1234
}

USE
Wrap your main logic in:
with AutomationRunLogger.from_config(<path to automation.config file>) as log:
this will guarantee information such as when it ran, how long it took, where it ran from, and whether it errored out. Additional information will require explicit calls of logging functions.

pass log to functions as needed to pass additional data to the run report

LOGGING FUNCTIONS
log.add_output
-pass any information about the run that would be of interest
log.add_flag
-pass information that should be investigated / resolved. Does not necessarily mean the automation failed, just that something didn't work right.
log.mark_failure
-flag this run as a failed run. This is not in place of log.add_flag, you may have one or the other or neither or both.

