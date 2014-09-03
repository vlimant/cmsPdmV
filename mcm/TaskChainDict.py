from json import dumps
from rest import database
from json_layer.request import request
from json_layer.chained_request import chained_request
#from json_layer.chained_campaign import chained_campaign

class TaskChainDict:
    def GET(self, *args, **argv):
        crn = args[0]
        crdb = database('chained_requests')
        ccdb = database('chained_campaigns')
        rdb = database('requests')
        def request_to_tasks( r , base, depend):
            ts=[]
            for si in range(len(r.get_attribute('sequences'))):
                task_dict={"TaskName": "%s_%d"%( r.get_attribute('prepid'), si),
                           "KeepOutput" : True,
                           "ConfigCacheID" : None,
                           "GlobalTag" : r.get_attribute('sequences')[si]['conditions'],
                           "CMSSWVersion" : r.get_attribute('cmssw_release'),
                           "ScramArch": r.get_scram_arch(),
                           "PrimaryDataset" : r.get_attribute('dataset_name'),
                           "AcquisitionEra" : r.get_attribute('member_of_campaign'),
                           "ProcessingString" : r.get_processing_string(si),
                           "ProcessingVersion" : r.get_attribute('version'),
                           "TimePerEvent" : r.get_attribute("time_event"),
                           "SizePerEvent" : r.get_attribute('size_event'),
                           "Memory" : r.get_attribute('memory'),
                           "FilterEfficiency" : r.get_efficiency()
                           }
                if len(r.get_attribute('config_id'))>si:
                    task_dict["ConfigCacheID"] = r.get_attribute('config_id')[si]

                if len(r.get_attribute('keep_output'))>si:
                    task_dict["KeepOutput"] = r.get_attribute('keep_output')[si]

                if r.get_attribute('pileup_dataset_name'):
                    task_dict["MCPileup"] = r.get_attribute('pileup_dataset_name')
                    
                if si==0:
                    if base:
                        task_dict.update({"SplittingAlgo"  : "EventBased",
                                          "RequestNumEvents" : r.get_attribute('total_events'),
                                          "Seeding" : "AutomaticSeeding",
                                          "EventsPerLumi" : 100,
                                          "LheInputFiles" : r.get_attribute('mcdb_id')>0
                                          })
                    else:
                        if depend:
                            task_dict.update({"SplittingAlgo"  : "EventAwareLumiBased",
                                              "InputFromOutputModule" : None,
                                              "InputTask" : None})
                        else:
                            task_dict.update({"SplittingAlgo"  : "EventAwareLumiBased",
                                              "InputDataset" : r.get_attribute('input_dataset')})
                else:
                    task_dict.update({"SplittingAlgo"  : "EventAwareLumiBased",
                                      "InputFromOutputModule" : ts[-1]['output_'],
                                      "InputTask" : ts[-1]['TaskName']})
                task_dict['output_'] = "%soutput"%(r.get_attribute('sequences')[si]['eventcontent'][0])
                task_dict['priority_'] = r.get_attribute('priority')
                ts.append(task_dict)    
            return ts

        if not crdb.document_exists(crn):
            ## it's a request actually
            mcm_r = rdb.get( crn )
            mcm_crs = crdb.query(query="root_request==%s"% crn)
            if len(mcm_crs)==0:  return dumps({})

            tasktree = {}

            ignore_status=False
            if 'scratch' in argv:
                ignore_status = True
            veto_point=None
            if 'upto' in argv:
                veto_point=int(argv['upto'])

            for mcm_cr in mcm_crs:
                starting_point=mcm_cr['step']
                if ignore_status: starting_point=0
                for (ir,r) in enumerate(mcm_cr['chain']):
                    if (ir<starting_point):
                        continue ## ad no task for things before what is already done
                    if veto_point and (ir>veto_point):
                        continue

                    mcm_r = request( rdb.get( r ) )
                    if mcm_r.get_attribute('status')=='done' and not ignore_status:
                        continue
                    if not r in tasktree:
                        tasktree[r] = { 
                            'next' : [],
                            'dict' : [],
                            'rank' : ir 
                            }
                    base=(ir==0) ## there is only one that needs to start from scratch
                    depend=(ir>starting_point) ## all the ones later than the starting point depend on a previous task
                    if ir<(len(mcm_cr['chain'])-1):
                        tasktree[r]['next'].append( mcm_cr['chain'][ir+1])

                    tasktree[r]['dict'] = request_to_tasks( mcm_r, base, depend )

            for (r,item) in tasktree.items():
                for n in item['next']:
                    if not n in tasktree: continue
                    tasktree[n]['dict'][0].update({"InputFromOutputModule" : item['dict'][-1]['output_'],
                                                       "InputTask" : item['dict'][-1]['TaskName']})
        

            wma={
                "RequestType" : "TaskChain",
                "inputMode" : "couchDB",
                "Group" : "ppd",
                "Requestor": "pdmvserv",
                "OpenRunningTimeout" : 43200,
                "TaskChain" : 0,
                "ProcessingVersion": 1,
                "RequestPriority" : 0,
                }

            task=1
            for (r,item) in sorted(tasktree.items(), key=lambda d: d[1]['rank']):
                for d in item['dict']:
                    if d['priority_'] > wma['RequestPriority']:  wma['RequestPriority'] = d['priority_']
                    for k in d.keys():
                        if k.endswith('_'):
                            d.pop(k)
                    wma['Task%d'%task] = d
                    task+=1
            wma['TaskChain'] = task-1

            if wma['TaskChain'] == 0:
                return dumps({})

            for item in ['CMSSWVersion','ScramArch','TimePerEvent','SizePerEvent','GlobalTag','Memory']:
                wma[item] = wma['Task%d'% wma['TaskChain']][item]

            wma['Campaign' ] = wma['Task1']['AcquisitionEra']
            wma['PrepID' ] = 'task_'+wma['Task1']['TaskName'].split('_')[0]
            wma['RequestString' ] = wma['PrepID']
            return dumps(wma)
