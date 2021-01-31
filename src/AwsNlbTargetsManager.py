import boto3
import sys
import botocore
import logging

class AwsNlbTargetsManager:

    def __init__(self, region, port, dry_run, logger):
        self.region = region
        self.dry_run = dry_run
        self.port = port
        self.elbv2_client = boto3.client('elbv2', region)
        self.logger = logger


    def _get_nlb_arn(self, nlb_name):
        elbs = self.elbv2_client.describe_load_balancers(Names=[nlb_name])
        return elbs.get('LoadBalancers')[0].get('LoadBalancerArn')


    def _get_nlb_target_group(self, nlb_arn):
        target_groups = self.elbv2_client.describe_target_groups(
            LoadBalancerArn=nlb_arn,
            PageSize=1
        )
        return target_groups.get('TargetGroups')[0].get('TargetGroupArn')


    def _get_nb_target_ips(self, target_group_arn):
        target_health = self.elbv2_client.describe_target_health(
            TargetGroupArn=target_group_arn
        )
        targets = target_health.get('TargetHealthDescriptions')
        ip_addresses = []
        for target in targets:
            ip_addresses.append(target.get('Target').get('Id'))
        return ip_addresses


    def _build_targets_from_ips(self, ip_addresses):
        targets = []
        for ip in ip_addresses:
            targets.append({ 'Id': ip, 'Port': self.port})
        
        return targets


    def _register_nlb_targets(self, target_group_arn, target_ips):
        targets = self._build_targets_from_ips(target_ips)

        return self.elbv2_client.register_targets(
            TargetGroupArn = target_group_arn,
            Targets = targets
        )


    def _deregister_nlb_targets(self, target_group_arn, target_ips):
        targets = self._build_targets_from_ips(target_ips)

        return self.elbv2_client.deregister_targets(
            TargetGroupArn = target_group_arn,
            Targets = targets
        )


    def _get_network_interfaces(self, alb_name):
        client = boto3.client('ec2', self.region)
        network_interfaces = client.describe_network_interfaces(
            Filters=[
                {
                    'Name': 'description',
                    'Values': [
                        f'*app/{alb_name}/*',
                    ]
                },
            ],
            DryRun=False
        ).get('NetworkInterfaces')

        ip_addresses = []
        for ni in network_interfaces:
            ip_addresses.append(ni.get('PrivateIpAddress'))

        return ip_addresses


    def _get_missing_elements(self, main_array, test_array):
        missing_elements = []
        main_array_set = set(main_array)
        
        for element in test_array:
            if element not in main_array_set:
                missing_elements.append(element)

        return missing_elements


    def sync_ip_addresses_from_alb(self, nlb_name, alb_name):
        try:
            if self.dry_run:
                self.logger.info('Running mode: dry run')

            nlb_arn = self._get_nlb_arn(nlb_name)
            self.logger.info(f'NLB arn: {nlb_arn}')
            
            nlb_target_group_arn = self._get_nlb_target_group(nlb_arn)
            self.logger.info(f'Target group arn: {nlb_target_group_arn}')
            
            nlb_target_ip_addresses = self._get_nb_target_ips(nlb_target_group_arn)
            self.logger.info(f'NLB targets IP addresses: {nlb_target_ip_addresses}')

            alb_ip_addresses = self._get_network_interfaces(alb_name)
            self.logger.info(f'ALB IP addresses: {alb_ip_addresses}')

            ip_addresses_to_register = self._get_missing_elements(nlb_target_ip_addresses, alb_ip_addresses)
            self.logger.info(f'IP addresses to register to NLB targets: {ip_addresses_to_register}')

            ip_addresses_to_deregister = self._get_missing_elements(alb_ip_addresses, nlb_target_ip_addresses)
            self.logger.info(f'IP addresses to deregister from NLB targets: {ip_addresses_to_deregister}')
            
            if self.dry_run == False:
                if ip_addresses_to_register:
                    self.logger.info(f'Registering IP addresses: {ip_addresses_to_register}')
                    self._register_nlb_targets(nlb_target_group_arn, ip_addresses_to_register)
                if ip_addresses_to_deregister:
                    self.logger.info(f'Deregistering IP addresses: {ip_addresses_to_deregister}')
                    self._deregister_nlb_targets(nlb_target_group_arn, ip_addresses_to_deregister)

        except botocore.exceptions.NoCredentialsError:
            e = sys.exc_info()[0]
            self.logger.error(f'Problem with credentials: {e}')
            raise
        except: 
            e = sys.exc_info()[0]
            self.logger.error(f"A general exception: {e}")
            raise


if __name__ == "__main__":
    region = 'eu-west-1'
    nlb_name = 'test-nlb-name'
    alb_name = 'test-alb-name'
    port = 80
    dry_run = True

    logging.basicConfig(format='[%(levelname)s] %(message)s')
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    client = AwsNlbTargetsManager(region, port, dry_run, logger)
    client.sync_ip_addresses_from_alb(nlb_name, alb_name)
