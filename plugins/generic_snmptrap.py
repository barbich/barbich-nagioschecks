#!/usr/bin/env python
# Script to be used with snmptt to be executed when handling traps and send a status to Nagios
# You will need to have Nagios NSCA to be installed.
# You will need to have snmptt installed and configured

import sys,time,os,re
from optparse import OptionParser
import marshal

debug=False
Nagios_commandfile='/usr/local/nagios/var/rw/nagios.cmd'
echo_command="/bin/echo"
nsca_command="/usr/local/nagios/bin/send_nsca"

# Which severity levels are we sending back to Nagios?
severitylist={
    'INFORMATIONAL':0,
    'Normal':0,
    'OK':0,
    'MAJOR':1,
    'MINOR':1,
    'WARNING':1,
    'CRITICAL':2
    }
nagios_states={'OK':0,'WARNING':1,'CRITICAL':2,'UNKNOWN':3,'DEPENDENT':4}


class NagiosError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)


def arg_parse():
    usage="%prog [options] [args]"
    parser = OptionParser(usage)
    parser.add_option("-H", "--hostname", dest="hostname",help="name or IP address of host to check",default='localhost')
    parser.add_option("-v", "--verbose", dest="verbose",action="store_true",help="print extra debugging information (and lists all services)",default=False)
    parser.add_option("-d", "--datetime", dest="datetime",help="Event date and time",default=None)
    parser.add_option("-e", "--eventname", dest="eventname",help="Event name defined in .conf file of matched entry.",default='UNKNOWN')
    parser.add_option("-s", "--severity", dest="severity",help="Severity.",default='INFORMATIONAL')
    parser.add_option("-c", "--category", dest="category",help="Category.",default='Status Events')
    parser.add_option("-m", "--message", dest="message",help="Translated FORMAT line",default='NONE')

    ### version

    (options, args) = parser.parse_args(args=sys.argv[1:])
    if len(args)!=0:
        parser.error("Error in command line options")
    if options.hostname is None : raise NagiosError,"Option hostname not defined."
    if options.datetime is None : raise NagiosError,"Option datetime not defined."
    if options.eventname is None : raise NagiosError,"Option eventname not defined."
    return options

def log(s=''):
    global logfile
    try:
        logfile.write(s)
    except:
        pass

if __name__=="__main__":
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
    try:
        options=arg_parse()
        if options.verbose:
            debug=True
    except NagiosError, msg:
        print 'Error:',msg
        sys.exit(-1)
    except:
        response_text="Errors in parameters submitted to command."
        raise

    command_line=''
    try:
        os.stat(Nagios_commandfile)
    except:
        print "Error accessing nagios command file, is nagios running?"
        raise
    try:
        os.stat(nsca_command)
    except:
        print "Error accessing nagios nsca command file, is nsca installed?"
        raise


    try:
        # Writing to log file
        logfile=open('/var/log/snmptrap2nagios.log','a')
    except:
        pass
    # try to retrieve the nagiosname from the hostname using the local cache DB
    # this is a marshall of a simple list 'SNMP HOSTNAME' => 'NAGIOS HOSTNAME'
    try:
        snmptthostnames=open('/usr/local/nagios/libexec/ECMWF/snmptt2nagioshosts.db')
        nagioshostnames=marshal.load(snmptthostnames)
    except:
        print "WARNING: couldn't read snmptt to nagios hostnames file. Continuing ..."
    # Translate the snmptt name to a nagios valid name
    if options.hostname in nagioshostnames and nagioshostnames[options.hostname]!='':
        hostname=nagioshostnames[options.hostname]
    else:
        hostname=options.hostname

    # Logging stuff ...
    cmd_params="hostname: %s\ndatetime:%s\neventname:%s\nseverity:%s %s\nmessage:%s\n" % (hostname,options.datetime,options.eventname,options.severity,options.category,options.message)
    log(cmd_params)

    try:
        pass
        # format of cmd_params looks like:
        # .1.3.6.1.4.1.2620.1.1.11.0 (unknown):18Jun2008 12:15:20        zeus       <    snmptrap System Alert message: CPU usage on quijote is more than 21% (currently 23%); Object: quijote; Event: Exception; Parameter: cpu_usage; Condition: is more than 21; Current value: 23; product: System Monitor;
        #msg=re.search('System Alert message: (.*); ',cmd_params).groups()[0].split(';')[0]
        #host=re.search('System Alert message: (.*); ',cmd_params).groups()[0].split(';')[1].split(':')[1].strip()
        #now=int(time.time())
        if options.severity in severitylist:
            state=severitylist[options.severity]
        else:
            state=severity['INFORMATIONAL']
        command_line='%s "%s;%s;%s;%s" | %s -H sherlock.ecmwf.int -d \; -c /usr/local/nagios/etc/send_nsca.cfg' % (echo_command,hostname,options.category,state,options.message,nsca_command)
        #log.write(command_line)
        log.write('\n')
    except:
        log.write('Error creating command line')
        log.close()
        raise
        sys.exit(1)
    try:
        os.system(command_line)
        #print command_line
    except:
        log.write('Error running command line')
        log.close
        sys.exit(1)
    log.write('\n')
    log.close
    sys.exit(0)
