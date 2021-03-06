#!/usr/bin/python

#######################################################
#                                                     #
#  Copyright Masterchain Grazcoin Grimentz 2013-2014  #
#  https://github.com/grazcoin/mastercoin-tools       #
#  https://masterchain.info                           #
#  masterchain@@bitmessage.ch                         #
#  License AGPLv3                                     #
#                                                     #
#######################################################

import subprocess
import json
import simplejson
import sys
import operator
import time
from msc_utils_parsing import *

def main():
    msc_globals.init()

    # get all tx of exodus address
    history=get_history(exodus_address)
    # sort
    history.sort(key=output_height)
    # parse result checking for exodus bootstrap entries
    for tx_dict in history:
        block=tx_dict['output_height']
        value=tx_dict['value']
        try:
            tx_hash=tx_dict['output'].split(':')[0]
            tx_output_index=tx_dict['output'].split(':')[1]
        except KeyError, IndexError:
            error("Cannot parse tx_dict:" + str(tx_dict))

        # interesting addresses are only those within exodus bootstrap blocks
        if int(block) >= first_exodus_bootstrap_block and int(block) <= last_exodus_bootstrap_block:
            (block_timestamp,err)=get_block_timestamp(int(block))
            if block_timestamp == None:
                error('failed to get timestamp: '+err)
            try:
                tx_sec_before_deadline=exodus_bootstrap_orig_deadline-block_timestamp
            except TypeError:
                error('bad block timestamp')
            # bonus is 10% for a week
            bonus=max((tx_sec_before_deadline+0.0)/(3600*24*7*10.0)*100,0)
            dacoins=str('{:.0f}'.format(int(value)*(100+bonus)))
            json_tx=get_tx(tx_hash)
            # give dacoins to highest contributing address.
            output_dict={} # dict to collect outputs per address
            for i in json_tx['inputs']:
                output_value=get_value_from_output(i['previous_output'])
                if output_value==None:
                    error('failed get_value_from_output')                
                if output_dict.has_key(i['address']):
                    output_dict[i['address']]+=output_value
                else:
                    output_dict[i['address']]=output_value
            # the winning address is the one with highest contributions
            address=max(output_dict.iteritems(), key=operator.itemgetter(1))[0]
            # output info about the tx generally
            (block,index)=get_tx_index(tx_hash)
            parsed=bootstrap_dict_per_tx(block, tx_hash, address, value, dacoins)
            parsed['block']=block
            parsed['index']=index
            parsed['method']='exodus'
            parsed['invalid']=False
            parsed['tx_time']=str(block_timestamp)+'000'
            try:
                filename='tx/'+parsed['tx_hash']+'.json'
                atomic_json_dump(parsed, filename)
            except IndexError:
                info("cannot parse 'tx_hash' in "+tx_hash)


if __name__ == "__main__":
        main()
