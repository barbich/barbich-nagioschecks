#!/usr/bin/env python
import sys,os,re
import MySQLdb

DB_HOST='localhost'
DB_USER='snmptt'
DB_PASS='MySuperPass'
DB_NAME='snmptt'


if __name__=="__main__":
    db=MySQLdb.connect(DB_HOST,DB_USER,DB_PASS,DB_NAME)
    Cursor = db.cursor(MySQLdb.cursors.DictCursor)
    query="select * from snmptraps where enable=1;"
    Cursor.execute(query)
    result_set=Cursor.fetchall()
    for r in result_set:
        #print "%s" % row['eventid']
        print """#MIB: %s
EVENT %s %s "%s" %s
FORMAT %s
EXEC %s
SDESC
EDESC
""" % (r['MIB'],r['eventname'],r['eventid'],r['category'],r['severity'],r['format'],r['exec'])
        pass
    Cursor.close()
    db.close()
