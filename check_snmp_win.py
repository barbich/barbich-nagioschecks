#!/usr/bin/env python
# based on check_snmp_win.pl from http://nagios.manubulon.com/
# 
# $Date$
# $Source$
# Description:
# this version uses disk caching for the result of snmpwalk
# Depends:
# netsnmp python bindings, requires netsnmp 5.4.1
"""Simple plugin to retrieve service status information from a windows host running SNMP.

__author__ = $Author$
__version__ = 
"""

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
    """Dummy Nagios Error class derived fromstandard exceptions."""
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

def xor_state(a='UNKNOWN',b='UNKNOWN'):
    """Returns the less good state from two Nagios states. We consider that OK < WARNING < CRITICAL < UNKNOWN < DEPENDENT.
    @type a: text
    @param a: state of the service
    @type a: text
    @param a: state of the service
    @rtype:   state name
    @return:  the worst state from a or b
    """
    na=nagios_states[a]
    nb=nagios_states[b]
    state=max(na,nb)
    return invert_nagios_states[state]


def arg_parse():
    """Argument parsing function."""
    usage="%prog [options] arg"
    parser = OptionParser(usage)
    parser.add_option("-H", "--hostname", dest="hostname",help="name or IP address of host to check",default='localhost')
    parser.add_option("-v", "--verbose", dest="verbose",action="store_true",help="print extra debugging information (and lists all services)",default=False)
    parser.add_option("-C", "--community", dest="community",help="community name for the host's SNMP agent (implies SNMP v1 or v2c with option)",default='public')
    parser.add_option("-2", "--v2c", dest="version",action="store_true",help="Use snmp v2c",default=False)
    parser.add_option("-p", "--port", dest="port",type="int",help="SNMP port (Default 161)",default=161)
    parser.add_option("-n", "--name", dest="name",help="Comma separated names of services (regular expressions can be used for every one). By default, it is not case sensitive.",default=None)
    parser.add_option("-N", "--number", dest="number",help="Compare matching services with <n> instead of the number of names provided.",type="int",default=1)
    parser.add_option("-s", "--showall", dest="showall",help="Show all services in the output, instead of only the non-active ones.",action="store_true",default=False)
    parser.add_option("-r", "--noregexp", dest="noregexp",help="Do not use regexp to match NAME in service description..",action="store_true",default=False)
    parser.add_option("--nocache", dest="nocache",help="Do not use caching of snmpwalk",action="store_true",default=False)
    parser.add_option("-t", "--timeout", dest="timeout",type="int",help="timeout for SNMP in seconds (Default: 5)",default=5)
    ### version

    (options, args) = parser.parse_args(args=sys.argv[1:])
    if len(args)!=0: parser.error("Error in command line options")
    if options.name is None : raise NagiosError,"Option name not defined."
    if options.number<0: raise NagiosError,"Invalid number of services."
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
    # try to import the pytho
    from pkg_resources import require
    import pkg_resources
    require("netsnmp-python")
    import netsnmp
except:
    print 'ERROR: netsnmp python library not installed'
    sys.exit(nagios_states[my_state])

# Generic windows OIDs
snmp_oids={
    "process_table":'.1.3.6.1.2.1.25.4.2.1',
    "index_table":'.1.3.6.1.2.1.25.4.2.1.1',
    "run_name_table":'.1.3.6.1.2.1.25.4.2.1.2',
    "run_path_table":'.1.3.6.1.2.1.25.4.2.1.4',
    "proc_mem_table":'.1.3.6.1.2.1.25.5.1.1.2', # Kbytes
    "proc_cpu_table":'.1.3.6.1.2.1.25.5.1.1.1', # Centi sec of CPU
    "proc_run_state":'.1.3.6.1.2.1.25.4.2.1.7',
    # Windows SNMP DATA
    "win_serv_table":'1.3.6.1.4.1.77.1.2.3.1', # Windows services table
    "win_serv_name":'.1.3.6.1.4.1.77.1.2.3.1.1', # Name of the service
    # Install state : uninstalled(1), install-pending(2), uninstall-pending(3), installed(4)
    "win_serv_inst":'.1.3.6.1.4.1.77.1.2.3.1.2',
    # Operating state : active(1),  continue-pending(2),  pause-pending(3),  paused(4)
    "win_serv_state":'.1.3.6.1.4.1.77.1.2.3.1.3',
    #"win_serv_state_label": ['active', 'continue-pending', 'pause-pending', 'paused'],
    # Can be uninstalled : cannot-be-uninstalled(1), can-be-uninstalled(2)
    "win_serv_uninst":'.1.3.6.1.4.1.77.1.2.3.1.4'
}
win_serv_state_label= { 1 : 'active', 2:'continue-pending', 3:'pause-pending', 4: 'paused', 99: 'UNAVAILABLE'}
# SNMP Datas for processes (MIB II)

########################################################################################################


if __name__=="__main__":
    # try to use python psyco module , see http://psyco.sourceforge.net/
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
    # try to parse command line arguments
    try:
        options=arg_parse()
        if options.verbose: debug=True
        match_list=[]
        name_list=options.name.split(',')
    except NagiosError, msg:
       print my_state,':',msg
       sys.exit(nagios_states[my_state])
    except:
       response_text="Errors in parameters submitted to command."
       my_state='UNKNOWN'
       if debug: raise
    else:
        if debug: pprint(options)
        # create a netsnmp session to our destination host
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
            # force netsnmp to return numeric oids
            snmp_session.UseNumeric=1
        except:
            response_text='SNMP session establishing failed.'
            print my_state,':',response_text
            sys.exit(nagios_states[my_state])
        try:
            varoids=netsnmp.VarList(netsnmp.Varbind(snmp_oids["win_serv_name"]))
            progname=os.path.basename(sys.argv[0])
            if progname=='':
                progname='UNKNOWN_SCRIPT'
            cache_dir='/tmp/nagios-cache/'
            cache_filename=cache_dir+progname+'.'+options.hostname+'.cache'
            if os.path.exists(cache_dir) and not options.nocache:
                if os.path.exists(cache_filename) and time()-os.stat(cache_filename)[ST_MTIME]<300:
                    use_cache=True
                else:
                    if debug: print "Regenerating cache."
                    use_cache=False
            else:
                if not options.nocache:
                    os.makedirs(cache_dir)
                    use_cache=False
                else:
                    use_cache=True

            #if os.stat(pname)[ST_MTIME]:
            if use_cache and not options.nocache:
                if debug: print "Using cache"
                try:
                    cache_file=open(cache_filename,'r')
                    varoids=pickle.load(cache_file)
                    cache_file.close()
                    res='OK'
                except:
                    res=snmp_session.walk(varoids)
            else:
                if debug: print "Not using cache"
                res=snmp_session.walk(varoids)

            if res is None or len(res)==0:
                if debug: print varoids
                my_state='CRITICAL'
                raise NagiosError,"SNMP query error: no value returned."
            if not use_cache and not options.nocache:
                try:
                    cache_file=open(cache_filename,'w')
                    pickle.dump(varoids,cache_file)
                    cache_file.close()
                except:
                    #syslog.syslog('Caching error: '+str(sys.exc_info()[0])+' = '+str(sys.exc_info()[1]))
                    pass
            match_list=[]
            if options.noregexp:
                for k in varoids:
                    if debug: print k.val
                    for n in name_list:
                        if n in k.val:
                            match_list.append(k)
                            if debug: print "Found ",k.val
                if len(match_list)!=len(name_list):
                    my_state='CRITICAL'
                    raise NagiosError,"Some values were not found."
            else:
                name_list_re=map(lambda x: re.compile(x),name_list)
                for k in varoids:
                    if debug: print k.val
                    for n in name_list_re:
                        if n.search(k.val):
                            match_list.append(k)
                            if debug: print "Found ",k.val
                if len(match_list)!=len(name_list):
                    my_state='CRITICAL'
                    if debug:
                        print "matches:",len(match_list)
                        print "requested:",len(name_list)
                    raise NagiosError,"Incorrect number of services running."
            # found a match?
            services_states={}
            if len(match_list)>0:
                   #test_oid=match.tag.replace(snmp_oids["win_serv_name"],snmp_oids["win_serv_state"])
                   for match in match_list:
                        test_oid = netsnmp.Varbind(match.tag.replace(snmp_oids["win_serv_name"],snmp_oids["win_serv_state"]))
                        test_oid.iid=match.iid
                        res=netsnmp.snmpget(test_oid,
                                            DestHost=options.hostname,
                                            Community=options.community,
                                            Version=options.version,
                                            RemotePort=options.port,
                                            Timeout=options.timeout,
                                            Retries=2
                        )
                        if res is None or None in res:
                             if debug:
                                  print test_oid.val
                                  print test_oid.tag
                             services_states[match.val]=99
                        else:
                             services_states[match.val]=int(test_oid.val)
            else:
                   # no match
                   my_state='CRITICAL'
                   raise NagiosError,"SNMP query error: no value returned."
            # generate the output
            response_text=''
            my_state='OK'
            for service in services_states:
                   if services_states[service]!=1:
                        this_state='CRITICAL'
                   else:
                        this_state='OK'
                   my_state=xor_state(my_state,this_state)
                   if options.showall:
                        response_text=response_text +' '+ service+': '+win_serv_state_label[services_states[service]]
                   else:
                        if services_states[service]!=1:
                             response_text=response_text +' '+ service+':'+win_serv_state_label[services_states[service]]
            if response_text=='':
                   if len(services_states)==1:
                        response_text='Service running'
                   else:
                        response_text='Services running'
            if debug: pprint(services_states)
        except NagiosError, msg:
            print my_state,':',msg
            sys.exit(nagios_states[my_state])
        except:
            response_text='SNMP request failed.'
            print my_state,':',response_text
            sys.exit(nagios_states[my_state])
    print my_state,':',response_text
    sys.exit(nagios_states[my_state])
    