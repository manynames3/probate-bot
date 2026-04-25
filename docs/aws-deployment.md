# AWS Deployment Notes

## Recommendation

For this project, the lowest-cost AWS deployment that keeps Playwright scraping functional is:

- one Amazon Lightsail Linux instance for the web app and worker
- Amazon S3 for exported files
- Amazon Route 53 for DNS

This is cheaper than an ECS plus ALB stack and less operationally awkward than trying to force Playwright into Lambda first.

## Why Not Start on Lambda

Lambda was considered because the scraper behaves like a job runner:

- submit scrape
- run work
- store results
- return status or export

That sounds serverless-friendly, but Playwright changes the picture:

- browser automation is more stable in containers or VMs
- jobs can run for minutes rather than milliseconds
- county portals are slow and fragile, so retries and waits are normal
- job orchestration matters more than request-per-request elasticity

Lambda is still possible later, but it is not the cheapest total engineering path for this project.

## Cheapest Practical Stack

### Option A: Lightsail starter

- Lightsail instance
- S3 exports
- Route 53 DNS

Estimated monthly cost:

- roughly $8 to $20 per month

Best for:

- one operator
- low traffic
- moderate scrape volume
- fast launch at minimal cost

### Option B: Managed AWS app stack

- S3 plus CloudFront frontend
- App Runner API
- ECS Fargate workers
- SQS queue
- DynamoDB metadata store
- Route 53 DNS

Estimated monthly cost:

- roughly $30 to $80 per month at low usage

Best for:

- multiple users
- cleaner service separation
- easier future scaling

### Option C: Traditional ECS plus ALB

- ECS Fargate API
- ECS Fargate workers
- Application Load Balancer
- SQS
- DynamoDB or RDS

Estimated monthly cost:

- roughly $60 to $150 per month at low usage

Best for:

- teams that already want a more standard AWS container platform

## Why Lightsail Wins on Cost

The main reason is fixed overhead.

With Lightsail, the app, worker, and browser runtime live on one small box. With ECS and an ALB, you start paying baseline service costs even before meaningful traffic arrives. For a scraper app with low traffic and one operator, that overhead is unnecessary.

## Upgrade Path

Start on Lightsail first. Move to App Runner plus Fargate only when one of these becomes true:

- the web UI and workers compete too much for CPU or memory
- you need concurrent scraping jobs
- you want isolated worker processes
- you need managed scaling and cleaner failure domains

## Source Pricing References

- AWS App Runner pricing: https://aws.amazon.com/apprunner/pricing/
- AWS Fargate pricing: https://aws.amazon.com/fargate/pricing/
- Elastic Load Balancing pricing: https://aws.amazon.com/elasticloadbalancing/pricing/
- Amazon DynamoDB pricing: https://aws.amazon.com/dynamodb/pricing/
- Amazon SQS pricing: https://aws.amazon.com/sqs/pricing/
- Amazon Route 53 pricing: https://aws.amazon.com/route53/pricing/
- Amazon CloudWatch pricing: https://aws.amazon.com/cloudwatch/pricing/
- Amazon S3 pricing: https://aws.amazon.com/s3/pricing/
- Amazon Lightsail pricing: https://aws.amazon.com/lightsail/pricing/
