#!/usr/bin/env python
import boto.ec2
import boto.ec2.elb
import re
import sys
from zabbix_api import ZabbixAPI, Already_Exists

# Vars
region = "eu-west-1"
zabbix_srv = "http://example.com/zabbix"
zabbix_usr = "admin"
zabbix_pwd = "password"

try:
    connection_ec2 = boto.ec2.connect_to_region(region, profile_name="prod")
    connection_elb = boto.ec2.elb.connect_to_region(region, profile_name="prod")
    my_instances = connection_ec2.get_all_instances()
except:
    connection_ec2 = boto.ec2.connect_to_region(region)
    connection_elb = boto.ec2.elb.connect_to_region(region)
    my_instances = connection_ec2.get_all_instances()


def aws_check_status(host_ip):
    for instance in my_instances:
        try:
            inst_ip = instance.instances[0].private_ip_address
            if re.search(host_ip, inst_ip):
                if instance.instances[0].state == 'running':
                    return True
        except: KeyError


def find_ip(host_zabbix):
    try:
        ip_tmp = re.search(r"([0-9]{1,3}-[0-9]{1,3}-[0-9]{1,3}-[0-9]{1,3})", host_zabbix)
        ip_raw = ip_tmp.group(1)
        ip_host = re.sub('-', '.', ip_raw)
    except:
        ip_host = ""
    if re.search("^[0-9]", ip_host):
        return ip_host
    else:
        print "not an aws instance"
        sys.exit()


def zabbix_delete():
    z = ZabbixAPI(server = zabbix_srv)
    z.login(zabbix_usr, zabbix_pwd)
    for trigger in z.trigger.get({"output": [ "triggerid", "description", "priority" ], "filter": { "value": 1 }, "sortfield": "priority", "sortorder": "DESC"}):
        if trigger["description"] == 'Zabbix agent on {HOST.NAME} is unreachable for 5 minutes':
            trigmsg = z.trigger.get({"triggerids": trigger["triggerid"], "selectHosts": "extend"})
            for tm in trigmsg:
                for l in tm['hosts']:
                    host_ip = find_ip(l['host'])
                    if aws_check_status(host_ip) != True:
                        print l['name'], l['hostid']
                        print "Will kill host " + l['hostid'] + " " + l['host'] + trigger["description"]
                        z.host.delete( [int(l['hostid'])] )
                    else:
                        print "instance is running"


def main():
    zabbix_delete()


if __name__ == "__main__":
    main()

