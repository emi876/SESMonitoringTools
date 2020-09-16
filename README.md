Things to remember in gettings things to work for the notification manager

1) Create a KMS key. Let SNS and SES have access to decrypt key. Configured on the KMS key IAM.
2) Create an SNS notification that is encrypted with above key.
3) Create an SQS queue that subscribes to above notification.
4) Create an AWS Lambda function that can read the queue and put the code in "notification-manager" in it

Emails to test with on SES console:

complaint@simulator.amazonses.com
bounce@simulator.amazonses.com

