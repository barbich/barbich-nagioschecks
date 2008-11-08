#!/usr/bin/python
# based on check_snmp_win.pl from http://nagios.manubulon.com/
# check some compaq stuff
# you will need the python extension which is coming with netsnmp www.net-snmp.org/ 

import os,sys,re
from optparse import OptionParser
from pprint import pprint
import syslog
import pkg_resources
from pkg_resources import require
from time import time
from stat import ST_MTIME
import cPickle as pickle

nagios_states={'OK':0,'WARNING':1,'CRITICAL':2,'UNKNOWN':3,'DEPENDENT':4}
invert_nagios_states= dict([(v, k) for k, v in nagios_states.iteritems()])

my_state='UNKNOWN'
response_text="NO OUTPUT"

debug=False


class NagiosError(Exception):
     def __init__(self, msg):
         self.msg = msg
     def __str__(self):
         return repr(self.msg)

def xor_state(a='UNKNOWN',b='UNKNOWN'):
     if not type(a) is int:
          na=nagios_states[a]
     else:
          na=a
     if not type(b) is int:
          nb=nagios_states[b]
     else:
          nb=b
     state=max(na,nb)
     return invert_nagios_states[state]

def arg_parse():
#"Usage: $Name [-v] -H <host> -C <snmp_community> [-2]
# [-p <port>] -n <name>[,<name2] [-T=service] [-r] [-s]
# [-N=<n>] [-t <timeout>] [-V]\n";
     usage="%prog [options] arg"
     parser = OptionParser(usage)
     parser.add_option("-H", "--hostname", dest="hostname",help="name or IP address of host to check",default='localhost')
     parser.add_option("-v", "--verbose", dest="verbose",action="store_true",help="print extra debugging information (and lists all services)",default=False)
     parser.add_option("-C", "--community", dest="community",help="community name for the host's SNMP agent (implies SNMP v1 or v2c with option)",default='public')
     parser.add_option("-2", "--v2c", dest="version",action="store_true",help="Use snmp v2c",default=False)
     parser.add_option("-p", "--port", dest="port",type="int",help="SNMP port (Default 161)",default=161)
     parser.add_option("-t", "--timeout", dest="timeout",type="int",help="timeout for SNMP in seconds (Default: 5)",default=5)
     parser.add_option("-L", "--longresponse", dest="longresponse",action="store_true",help="Return long response text",default=False)
     ### Specifics
     parser.add_option("--psu", dest="check",action="store_const",help="Check Power Supply Status",const=0)
     parser.add_option("--power", dest="check",action="store_const",help="Check Power Supply Status",const=0)
     parser.add_option("--temp", dest="check",action="store_const",help="Check Temperature Status",const=1)
     parser.add_option("--fan", dest="check",action="store_const",help="Check FAN Status",const=2)
     parser.add_option("--cpu", dest="check",action="store_const",help="Check CPU Status",const=3)
     parser.add_option("--log", dest="check",action="store_const",help="Check Logical Drive Status",const=4)
     parser.add_option("--phy", dest="check",action="store_const",help="Check Physical Drive Status",const=5)
     parser.add_option("--smart", dest="check",action="store_const",help="Check Physical Drive Smart Status",const=6)
     ### version

     (options, args) = parser.parse_args(args=sys.argv[1:])
     if options.check is None:
          parser.error("One option must be specified.")
     if len(args)!=0:
          parser.error("Error in command line options")
     if options.version:
          options.version=2
     else:
          options.version=1
     options.timeout=options.timeout*100000

     return options

########################################################################################################
# Plugin specific stuff goes here
########################################################################################################

try:
    #import netsnmp
     from pkg_resources import require
     require("netsnmp-python")
     import netsnmp
except:
     print 'ERROR: netsnmp python library not installed'
     sys.exit(nagios_states[my_sate])

snmp_oids={
     "SysUptime"                        :      ".1.3.6.1.2.1.1.3.0",
     0  :      ".1.3.6.1.4.1.232.6.2.9.3.1.4.0", #CPQHLTH-MIB::cpqHeFltTolPowerSupplyCondition.0.X
     1  :      ".1.3.6.1.4.1.232.6.2.6.8.1.6.0", #CPQHLTH-MIB::cpqHeTemperatureCondition
     2  :      ".1.3.6.1.4.1.232.6.2.6.7.1.9.0", #CPQHLTH-MIB::cpqHeFltTolFanCondition.0
     3  :      ".1.3.6.1.4.1.232.1.2.2.1.1.6", #CPQSTDEQ-MIB::cpqSeCpuStatus
     4  :      ".1.3.6.1.4.1.232.3.2.3.1.1.4", #CPQIDA-MIB::cpqDaLogDrvStatus
     5  :      ".1.3.6.1.4.1.232.3.2.5.1.1.6", #CPQIDA-MIB::cpqDaPhyDrvStatus
     6  :      ".1.3.6.1.4.1.232.3.2.5.1.1.57", #CPQIDA-MIB::cpqDaPhyDrvSmartStatus
}

descriptions = {
     5: { #descrphyDriveStatus = {
     1: [2,"Drive not recognizable"],
     2: [0,"normal operation mode"],
     3: [2,"failed, drive should be replaced"],
     4: [2,"predictive Failure, drive should be replaced"],
     },

     4: { #descrlogDriveStatus = {
     1: [2,"other"],
     2: [0,"normal operation mode"],
     3: [2,"fault tolerance mode of the logical drive can handle without data loss"],
     4: [2,"logical drive unconfigured"],
     5: ["using Interim Recovery Mode (at least one physical drive has failed)"],
     6: ["ready for Automatic Data Recovery"],
     7: ["Automatic Data Recovery in progress"],
     8: ["wrong physical drive was replaced"],
     9: ["physical drive is not responding"],
     10: ["drive array enclosure is overheating"],
     11: ["drive array enclosure has overheated and is shutdown"],
     12: ["Automatic Data Expansion in progress"],
     13: ["Logical Drive Unavailable"],
     14: ["Automatic Data Expansion is ready"]
     },

     3: {#desccpqSeCpuStatus = {
     1: [2,"The status of the CPU could not be determined."],
     2: [0,"The CPU is functioning normally."],
     3: [2,"The CPU is in a pre-failure warrantee state."],
     4: [2,"The CPU is in a failed state."],
     5: [2,"The CPU has been disabled during power-on-self-test."]
     },

     2: {#desccpqHeFltTolFanCondition = {
     1: [2,"Fan status detection is not supported by this system or driver."],
     2: [0,"The fan is operating properly."],
     3: [2,"A redundant fan is not operating properly."],
     4: [2,"A non-redundant fan is not operating properly."]
     },

     1: {#desccpqHeTemperatureCondition = {
     1: [2,"Temperature could not be determined."],
     2: [0,"The temperature sensor is within normal operating range."],
     3: [2,"The temperature sensor is outside of normal operating range."],
     4: [2,"The temperature sensor detects a condition that could permanently damage the system."]
     },

     0: {#desccpqHeFltTolPowerSupplyCondition = {
     1: [2,"The status could not be determined or not present."],
     2: [0,"The power supply is operating normally."],
     3: [2,"A temperature sensor, fan or other power supply component is outside of normal operating range."],
     4: [2,"A power supply component detects a condition that could permanently damage the system."]
     },

     6: {
     1: [2,"The agent is unable to determine if the status of S.M.A.R.T predictive failure monitoring for this drive."],
     2: [0,"Indicates the drive is functioning properly."],
     3: [2,"Indicates that the drive has a S.M.A.R.T predictive failure"]
     }
}
# SNMP Datas for processes (MIB II)



########################################################################################################


if __name__=="__main__":
     #syslog.syslog(pprint.saferepr(sys.path))
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
        print my_state,':',msg
        sys.exit(nagios_states[my_state])
     except:
          response_text="Errors in parameters submitted to command."
          my_state='UNKNOWN'
          if debug: raise
     else:
          if debug:
               pprint(options)
          try:
               netsnmp.verbose=0
               snmp_session=netsnmp.Session(
                    DestHost=options.hostname,
                    Community=options.community,
                    Version=options.version,
                    RemotePort=options.port,
                    Timeout=options.timeout,
                    Retries=2
                )
               snmp_session.UseNumeric=1
          except:
               response_text='SNMP session establishing failed.'
               print my_state,':',response_text
               sys.exit(nagios_states[my_state])

          try:
               # get local AS for this router
               varoids=netsnmp.VarList(netsnmp.Varbind(snmp_oids[options.check]))
               res=snmp_session.walk(varoids)
               if res is None or len(res)==0:
                    if debug:
                         print varoids
                    my_state='CRITICAL'
                    raise NagiosError,"SNMP query error: no value returned."
               response_text_l=()
               my_state='OK'
               desc=descriptions[options.check]
               #pprint(res)
               for rr in range(len(res)):
                    # get status
                    r=int(res[rr])
                    i=varoids[rr].iid
                    s=desc[r][0]
                    t=desc[r][1]
                    my_state=xor_state(my_state,s)
                    response_text_l += ("ID %s:%s" % (i,t),)
               response_text='\n'.join(response_text_l)
          except NagiosError, msg:
               print my_state,':',msg
               sys.exit(nagios_states[my_state])
          except:
               raise
               response_text='SNMP request failed or other error.'
               print my_state,':',response_text
               sys.exit(nagios_states[my_state])
     print response_text
     sys.exit(nagios_states[my_state])