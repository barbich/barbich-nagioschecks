#!/usr/bin/env python
# Small script to be executed from snmptt to handle checkpoint SNMPTRAPs and send them to Nagios
# This needs the Nagios NSCA plugin to be installed and configured

import sys,time,os,re


if __name__=="__main__":
    Nagios_commandfile='/usr/local/nagios/var/rw/nagios.cmd'
    echo_command="/bin/echo"
    nsca_command="/usr/local/nagios/bin/send_nsca"
    command_line=''
    try:
        cmd_params=sys.argv[1]
    except:
        print "Missing arguments"
        sys.exit(1)
    try:
        log=open('/tmp/checkpoint2nagios.log','a')
        log.write(cmd_params)
        log.write('\n\n')
        log.close
        # format of cmd_params looks like:
        # .1.3.6.1.4.1.2620.1.1.11.0 (unknown):18Jun2008 12:15:20        zeus       <    snmptrap System Alert message: CPU usage on quijote is more than 21% (currently 23%); Object: quijote; Event: Exception; Parameter: cpu_usage; Condition: is more than 21; Current value: 23; product: System Monitor;
        msg=re.search('System Alert message: (.*); ',cmd_params).groups()[0].split(';')[0]
        host=re.search('System Alert message: (.*); ',cmd_params).groups()[0].split(';')[1].split(':')[1].strip()
        now=int(time.time())
        state=1
        command_line='%s "%s;%s;%s;%s" | %s -H sherlock.ecmwf.int -d \; -c /usr/local/nagios/etc/send_nsca.cfg' % (echo_command,host,'Checkpoint Alarm',state,msg,nsca_command)
    except:
        print "Error processing arguments"
        raise
        sys.exit(1)
    try:
        os.system(command_line)
        print command_line
    except:
        print "Error writing to Nagios"
        sys.exit(1)
    sys.exit(0)
