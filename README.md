## AWS Network Load Balancer Targets Manager

The purpose of this python class is to sync AWS Application Load Balancer (ALB) IP addresses to Network Load Balancer (NLB) Target. This solves the issue with NLB targets being able to only target EC2 instances or IP addresses.

## How it works
The class has a method `sync_ip_addresses_from_alb(nlb_name, alb_name)` that does a couple of things:
- Fetches IP addresses from Network Interfaces by ALB name
- Fetches IP addresses from NLB Targets
- Registers ALB IP addresses as NLB Targets that are missing in NLB Targets list
- Deregisters NLB Targets that are missing in ALB IP addresses list

## Prerequisites
- NLB Targets must be of IP type
- ALB is consumed via the same port (e.g. HTTP 80)

## How to run

Example of importing the class and running the script:
```python
import logging
from NlbTargetsManager import NlbTargetsManager

logger = logging.getLogger()
default_port = 80

manager = NlbTargetsManager('eu-west-1', default_port, True, logger)
manager.sync_ip_addresses_from_alb('your-nlb-name', 'your-alb-name')
```

Example of running the class file directly:
1. Find `if __name__ == "__main__":` part and update variable names below it
2. Run `python NlbTargetsManager.py`
