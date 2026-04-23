### Steps for CodeQL manual validation

- Get the unique queries/rules
- Select the related (to crypto-api misuse) queries
- Filter results based on the related queries and extract the actual findings from the sarif file to the json file the field `validation_status`
- Get the method name using the line number available for each alerts/findings
- To automatically label, 1) match file name, 2) match method name, 3) match alert details / API signature.
- During labelling, match according to the discussion. 1) if same number of similar type of alerts, mark all of them, 2) if not similar number of alerts, then label the similar number of alerts as ground truth.
