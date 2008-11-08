# Create your views here.
try:
    from django.http import HttpResponse
    from django.shortcuts import render_to_response
except:
    import pprint
    
import re,os
import simplejson

nagios_hosts={}
color_table=['#00FF66','#FF3300','#FF6666','#6666FF']

class NagiosNode:
    __name=''
    __oid=0
    __parents=[]
    __childrens=[]
    __data=[]
    __adjacencies=[]
    # Nagios specific
    __hoststatus=0
    __services=[]
    
    def __init__(self,name,oid):
        self.__name=name
        self.__oid=oid
        
    def parents(self,parents=None):
        if parents:
            self.__parents=parents
        return self.__parents
        
    def childrens(self,childrens=None):
        if childrens:
            self.__childrens=childrens
        return self.__childrens

    def adjacencies(self,adjacencies=None):
        if adjacencies:
            self.__adjacencies=adjacencies
        return self.__adjacencies
    
    def add_adjacencies(self,adj=None):
        if adjacencies:
            self.__adjacencies.append(adjacencies)
            
    def hoststatus(self,s=None):
        if s:
            self.__hoststatus=s
        return self.__hoststatus

    def gethoststatus(self):
        return self.__hoststatus
    
    def name(self):
        return self.__name
    def id(self):
        return self.__oid
    
    def __str__(self):
        return self.__name
    
    def __repr__(self):
        r="%s:\nparents:%s\nchildrens:%s\nStatus: %s" % (self.__name,self.__parents,self.__childrens,self.__hoststatus)
        return r

def uniq(alist):
    set = {}
    map(set.__setitem__, alist, [])
    return set.keys()

# Do a simple tree structure
def get_tree(start):
    h=nagios_hosts[start]
    r={}
    r['id']=h.id()
    r['name']=h.name()
    r['children']=[]
    try:
        r['data']=[
            {'key':'weight','value':'1'},
            {'key':'color','value':color_table[h.hoststatus()]}
        ]
    except:
        pprint.pprint(h)
        pprint.pprint(color_table)
        raise
    for i in h.childrens():
        r['children'].append(get_tree(i))
    return r

def generate_tree(start_host='sancho',parenting=True,json=True):
    nagios_obj_name='/usr/local/nagios/var/tmpdir/objects.cache'
    nagios_obj_f=open(nagios_obj_name,'r')
    nagios_obj=nagios_obj_f.readlines()
    nagios_obj_f.close()
    
    try:
        nagios_sts_name='/usr/local/nagios/var/status.dat'
        nagios_sts_f=open(nagios_sts_name,'r')
        nagios_sts=nagios_sts_f.readlines()
        nagios_sts_f.close()
    except:
        nagios_sts=[]
    in_host=False
    in_hostgroup=False
    in_hostgroup_fetch=False
    hostname=None
    parents=None
    nagios_parenting={}
    
    childrens={}
    get_hostname=re.compile('\s*host_name\s*(.*)$')
    get_hostgroupname=re.compile('\s*hostgroup_name\s*(.*)$')
    get_parents=re.compile('\s*parents\s*(.*)$')
    myid=0
    for ll in nagios_obj:
        l=ll.strip()
        if 'define host {' in l:
            in_host=True
            continue
        if '}' in l and in_host:
            in_host=False
            hostname=None
            parents=None
            continue
        if in_host:
            if l.startswith('host_name'):
                myid+=1
                hostname=get_hostname.match(l).groups()[0]
                if not hostname in nagios_hosts:
                    nagios_hosts[hostname]=NagiosNode(hostname,myid)
            if l.startswith('parents'):
                parents=get_parents.match(l).groups()[0]
                if hostname:
                    #nagios_parenting[hostname]=parents.split(',')
                    parents_list=parents.split(',')
                    # With want to have a single parent for each node?!
                    if not parenting:
                        parents_list=(parents_list[0],)
                    nagios_hosts[hostname].parents(parents_list)
                    for p in parents_list:
                        if p in childrens:
                            childrens[p].append(hostname)
                        else:
                            childrens[p]=[hostname]
    # Calculating childrens for root
    for h in nagios_hosts:
        if h in childrens:
            try:
                nagios_hosts[h].childrens(childrens[h])
            except:
                print "Hmmm , parent given but it seems not to exist. (%s)" % h
                raise
    # Filling in the status informations
    in_host=False
    for ll in nagios_sts:
        l=ll.strip()
        if l == 'hoststatus {':
            in_host=True
            continue
        if l == '}':
            if hostname in nagios_hosts:
                nagios_hosts[hostname].hoststatus(lstate)
            in_host=False
            hostname=None
            lstate=None
            #cstate=None
            #tstate=None
            continue
        if in_host:
            if l.startswith('host_name='):
                hostname=l.replace('host_name=','')
            #if ll.startswith('current_state='):
            #    try:
            #        cstate=int(ll.replace('current_state=',''))
            #    except:
            #        cstate=3
            #if ll.startswith('state_type='):
            #    try:
            #        tstate=int(ll.replace('state_type=',''))
            #    except:
            #        tstate=1
            if l.startswith('last_hard_state='):
                try:
                    lstate=int(l.replace('last_hard_state=',''))
                except:
                    lstate=1
            
    if start_host in nagios_hosts:
        r=get_tree(start_host)
    else:
        r={}
    if json:
        json=simplejson.dumps(r)
        return json
    return r
    
def tree(request,start='sancho'):
    json=generate_tree(start,parenting=True)
    return render_to_response('raw.html', { 'json' : json })

def stree(request,start='sancho'):
    json=generate_tree(start,parenting=False)
    return render_to_response('raw.html', { 'json' : json })

# Do a graph structure
def get_treenodes(start):
    r=[start['name']]
    for h in start['children']:
        r=r+get_treenodes(h)
    return r

def get_graph(start):
    h=nagios_hosts[start]
    r={}
    r['id']=h.id()
    r['name']=h.name()
    r['children']=[]
    r['data']=[]
    for i in h.childrens():
        r['children'].append(get_graph(i))
    return r

def generate_graph(start_host='sancho',json=True):
    std_tree=generate_tree(start_host=start_host,parenting=True,json=False)
    # get nodes from tree, this ensures we only have does which we have interrest in
    treenodes_m=get_treenodes(std_tree)
    treenodes=uniq(treenodes_m)
    #s.sort()
    resp=[]
    for el in treenodes:
        childrens=nagios_hosts[el].childrens()
        parents=nagios_hosts[el].parents()
        adj=childrens+parents
        adj=uniq(adj)
        r={}
        r['id']=nagios_hosts[el].id()
        r['name']=nagios_hosts[el].name()
        r['data']=[]
        r['adjacencies']=[]
        for a in adj:
            if a in treenodes:
                r['adjacencies'].append(a)
        resp.append(r)

    if json:
        json=simplejson.dumps(resp)
        return json
    return resp

def graph(request,start='sancho'):
    json=generate_graph(start,json=True)
    return render_to_response('raw.html', { 'json' : json })

if __name__=="__main__":
    json=generate_tree('sancho',json=True,parenting=False)
    #pprint.pprint(json)
    pprint.pprint(nagios_hosts['int-ps-a'])
    #pprint.pprint(nagios_hosts['sancho'])
    #j=generate_graph('quijote',json=True)
    #pprint.pprint(j)
    #s=get_treenodes(j)
    #pprint.pprint(s)
    print "-"*10
    #pprint.pprint(j[1])