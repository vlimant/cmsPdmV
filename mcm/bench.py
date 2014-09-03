from rest import restful,database
import pprint
import json

from TaskChainDict import TaskChainDict
d = TaskChainDict()

arg='SUS-Fall13wmLHE-00011'
#answer=json.loads( d.GET(arg, scratch='', upto='1') )
answer=json.loads( d.GET(arg, scratch='') )

## massage it
answer['Requestor']='vlimant'
answer['Task1']['RequestNumEvents']=50000

dtext=json.dumps( answer )
open('%s_dict.json'% arg,'w').write( dtext )

pprint.pprint( answer )
