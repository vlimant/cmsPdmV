#!/usr/bin/env python

from chained_request import chained_request
from json_base import json_base
from submission_details import submission_details
from approval import approval
from comment import comment
from request import request

class flow(json_base):
    def __init__(self, author_name, author_cmsid=-1, author_inst_code='', author_project='', json_input={}):
        self._json_base__schema = {
            '_id':'',
            'prepid':'', 
            'next_campaign':'', 
            'allowed_campaigns':[], 
            'request_actions':{}, 
            'description':'',
            'submission_details':submission_details().build(author_name,  author_cmsid,  author_inst_code,  author_project    ),
            }
        
        # update self according to json_input
        self.__update(json_input)
        self.__validate()

    def __validate(self):
        if not self._json_base__json:
            return 
        for key in self._json_base__schema:
            if key not in self._json_base__json:
                raise self.IllegalAttributeName(key)
    
    # for all parameters in json_input store their values 
    # in self._json_base__json
    def __update(self,  json_input):
        self._json_base__json = {}
        if not json_input:
            self._json_base__json = self._json_base__schema
        else:
            for key in self._json_base__schema:
                if key in json_input:
                    self._json_base__json[key] = json_input[key]
                else:
                    self._json_base__json[key] = self._json_base__schema[key]
            if '_rev' in json_input:
                self._json_base__json['_rev'] = json_input['_rev']
    
    def add_allowed_campaign(self,  cid):
        
        # import database connector
        try:
            from couchdb_layer.prep_database import database
        except ImportError as ex:
            print str(ex)
            return False
        
        # initialize database connector
        try:
            cdb = database('campaigns')
        except database.DatabaseAccessError as ex:
            print str(ex)
            return False
            
        # check campaign exists
        if not cdb.document_exists(cid):
            raise self.CampaignDoesNotExistException(cid)
        
        # check for duplicate
        allowed = self.get_attribute('allowed_campaigns')
        if cid in allowed:
            raise self.DuplicateCampaignEntry(cid)
        
        # append and make persistent
        allowed.append(cid)
        self.set_attribute('allowed_campaigns',  allowed)
        
        return True
        
    def remove_allowed_campaign(self,  cid):
        allowed = self.get_attribute('allowed_campaigns')
        if cid not in allowed:
            raise self.CampaignDoesNotExistException(cid)
        
        # remove it and make persistent
        allowed.remove(cid)
        self.set_attribute('allowed_campaigns',  allowed)
