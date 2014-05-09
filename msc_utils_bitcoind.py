#!/usr/bin/python1

##########################################################################
#                                                                        #
#  Usage information and action required:                                #
#                                                                        #
#  1. To establish a JSON-RPC connection to a running, address indexed   #
#     bitcoind client, please define:                                    #

rpcuser='your_rpc_username'
rpcpassword='your_rpc_password'
rpcconnect='127.0.0.1'
rpcport='8332'

#  2. Replace "msc_utils_obelisk" with "msc_utils_bitcoind" in L14 of    #
#     msc_utils_parsing.py                                               #
#                                                                        #
#                                                                        #
#                                                                        #
#  Please be aware this wrapper only works in combination with a         #
#  customized bitcoind client with the following features:               #
#                                                                        #
#    "getrawtransaction" includes "position" in verbosed output          #
#    "getrawtransaction" includes "blockheight" in verbosed output       #
#    RPC call: getallbalance "address" (minconf, maxreqsigs)             #
#    RPC call: listalltransactions "address" (verbose, skip, count)      #
#                                                                        #
#                                                                        #
#  This wrapper was tested with mastercoin-tools and:                    #
#                                                                        #
#    Git:                                                                #
#      https://github.com/dexX7/bitcoin.git                              #
#                                                                        #
#    Branch:                                                             #
#      0.9.1-addrindex-extended (based on release v0.9.1)                #
#      master-addrindex-extended (based on current master)               #
#                                                                        #
#                                                                        #
#  Sample bitcoin.conf:                                                  #
#                                                                        #
#    server=1                                                            #
#    txindex=1                                                           #
#    addrindex=1                                                         #
#    rpcuser=your_rpc_username                                           #
#    rpcpassword=your_rpc_password                                       #
#    rpcport=8332                                                        #
#    rpcconnect=127.0.0.1                                                #
#                                                                        #
#                                                                        #
#  It may be required to install "python-bitcoinrpc":                    #
#                                                                        #
#    https://pypi.python.org/pypi/python-bitcoinrpc/0.1 to install       #
#                                                                        #
#                                                                        #
#  Please note:                                                          #
#                                                                        #
#    This is experimental and not all methods of the original            #
#    sx/obelisk connector are implemented, so this may not work          #
#    with Omniwallet.                                                    #
#                                                                        #
##########################################################################


import simplejson as json
import re
import os
import msc_globals
from msc_utils_bitcoin import *
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

address_index_not_available = '''
No RPC connection to a bitcoind client with an enabled address index 
and the needed RPC calls could be established.

Please note that this is very experimental and you need a customized 
version of bitcoind. The following clients were tested in combination 
with mastercoin-tools:

Git:
  https://github.com/dexX7/bitcoin.git

Branch:
  0.9.1-addrindex-extended (based on release v0.9.1)
  master-addrindex-extended (based on current master)

Please see the top of msc_utils_bitcoind.py for details.
'''

# some options
http_timeout = 120

# establish rpc connection to bitcoind
rpc = AuthServiceProxy('http://%s:%s@%s:%s' \
    % (rpcuser, rpcpassword, rpcconnect, rpcport), None, http_timeout)

# temporary store data for even faster lookup
blocktimes_storage = {}
transactions_storage = {}
parsed_tx_storage = {}

cache_parsed_txs = True
cache_blocktimes = True
cache_transactions = True

# uses rpc.getblockcount
def get_last_height():
    blockcount = 0
    try:
        blockcount = rpc.getblockcount()
    except JSONRPCException as e:
        info(e.error['message'])
        error('could not fetch last block height')
    return str(blockcount)

# uses rpc.getblockhash, rpc.getblock
def get_block_timestamp(height):
    height = int(height)    
    print height
    # try to restore from temporary storage
    if height in blocktimes_storage:
        return (blocktimes_storage[height], None)
    blocktime = None
    err = None
    try:
        blockhash = rpc.getblockhash(int(height))
        block = rpc.getblock(blockhash)
        blocktime = block['time']
        # store temporary for later usage and fast lookup
        if cache_blocktimes:
            blocktimes_storage[height] = blocktime
    except JSONRPCException as e:
        info(e.error['message'])
        err = 'could not fetch block time for height '+str(height)
        error(err)
    except (ValueError, TypeError) as e:
        info(str(e))
        err = 'could not fetch block time for height '+str(height)
        error(err)
    return (blocktime, err)

# uses rpc.getrawtransaction
def get_raw_tx(tx_hash, verbosed=0):
    raw_tx = None
    # try to restore from temporary storage
    if tx_hash in transactions_storage:
        tx = transactions_storage[tx_hash]
        if verbosed:
            return tx
        else:
            try:
                return tx['hex']
            except KeyError:
                # for some reason the entry seems to be broken
                error('could not lookup '+tx_hash)
                del transactions_storage[tx_hash]
                pass
    try:
        raw_tx = rpc.getrawtransaction(tx_hash, verbosed)
        # store temporary for later usage and fast lookup
        if cache_transactions and verbosed:
            transactions_storage[tx_hash] = raw_tx
    except JSONRPCException as e:
        info(e.error['message'])
        error('could not get raw transaction for '+tx_hash)
    return raw_tx

# uses rpc.decoderawtransaction
def get_json_tx(raw_tx, tx_hash='unknown hash'):
    if raw_tx == None or raw_tx == '':
        # is this ever reached?
        info(raw_tx)
        info(tx_hash)
        error('neither raw transaction nor transaction hash were provided')
    tx = None
    # try to fetch transaction via txid, it's faster than decoding, if cached
    if tx_hash != 'unknown hash':
        return get_tx(tx_hash)
    # otherwise stick to decoding
    else:
        try:
            tx = rpc.decoderawtransaction(raw_tx)
        except JSONRPCException as e:
            info(str(e))
            error('could not fetch transaction for txid '+tx_hash)
            return None
    if tx == None:
        error('could not fetch transaction for txid '+tx_hash)
        return None
    parsed_tx = parse_transaction(tx)
    return parsed_tx

# uses rpc.listalltransactions
def get_history(addr, skip=0, count=1000):
    all_output_infos = []
    do_loop = True
    while do_loop:
        try:
            debug('skip: %i, count: %i for %s' % (skip, count, addr))
            all_transactions = rpc.listalltransactions(addr, 1, skip, count)
        except JSONRPCException as e:
            info(e.error['message'])
            error('could not fetch history for '+addr)
        len_before = len(all_output_infos)
        for tx in all_transactions:
            output_info = parse_as_output_to(addr, tx)
            all_output_infos.extend(output_info)
        len_after = len(all_output_infos)
        debug('added %i new transactions' % (len_after-len_before))
        skip = skip + count
        # continue unless no more new results are fetched
        do_loop = len_after > len_before
    return all_output_infos

# uses rpc.getallbalance
def get_balance_single(address):
    try:
        raw_balance = rpc.getallbalance(address)
        return \
        {
            'address': address,
            'paid': to_satoshi(raw_balance)
        }
    except Exception as e:
        info(str(e))
        error('balance error for '+str(address))
        return None


# no more rpc calls from here on
def get_balance(addr_batch_str):
    all_balances = []
    try:
        all_addresses = addr_batch_str.split(' ')
    except:
        info(addr_batch_str)
        error('invalid input format, must be "1address 1address 1address"')
    for address in all_addresses:
        if len(address):
            balance = get_balance_single(address)
            if balance != None:
                all_balances.append(balance)
    return all_balances

def get_tx(tx_hash):
    # try to restore from temporary storage
    if tx_hash in parsed_tx_storage:
        parsed_tx = parsed_tx_storage[tx_hash]
        if parsed_tx != None:
            debug('restored parsed transaction from cache for txid '+tx_hash)
            return parsed_tx
    tx = get_raw_tx(tx_hash, 1)
    if tx == None:
        error('could not get transaction (None) for '+tx_hash)
        return None
    parsed_tx = parse_transaction(tx)
    return parsed_tx

def get_tx_index(tx_hash):
    blockheight = None
    position = None
    try:
        tx = get_raw_tx(tx_hash, 1)
        if 'blockheight' not in tx or 'position' not in tx:
            # is this ever reached?
            info(tx)
            error('blockheight or position missing in tx info output')
        blockheight = tx['blockheight']
        position = tx['position']
    except (KeyError, TypeError) as e:
        info(tx)
        error('could not fetch blockheight or position for '+tx_hash)
    return (blockheight, position)

def get_value_from_output(tx_and_number):
    output = get_vout_from_output(tx_and_number)
    if output != None:
        if 'value' not in output:
            info(output)
            error('no value found for '+tx_and_number)
        return output['value']
    else:
        error('no output found for '+tx_and_number)
        return None

def get_address_from_output(tx_and_number):
    output = get_vout_from_output(tx_and_number)
    if output != None:
        if 'address' not in output:
            info(output)
            error('no address found for '+tx_and_number)
        return output['address']
    else:
        error('no output found for '+tx_and_number)
        return None

def get_vout_from_output(tx_and_number):
    try:
        tx_hash=tx_and_number.split(':')[0]
        number=int(tx_and_number.split(':')[1])
    except IndexError:
        error('index error for '+tx_and_number)
        return None
    json_tx=get_tx(tx_hash)
    if json_tx==None:
        error('failed getting json_tx (None) for '+tx_hash)
        return None
    try:
        all_outputs=json_tx['outputs']
    except TypeError:
        error('bad outputs parsing on: '+json_tx)
        return None
    try:
        output=all_outputs[number]
    except IndexError:
        error('not a valid vout number: '+str(number))
        return None
    return output

def parse_vin(raw_input):
    address = None
    if 'coinbase' in raw_input:
        previous_output_hash = \
            '0000000000000000000000000000000000000000000000000000000000000000'
        previous_output_vout = 4294967295
        script = '[ %s ]' % raw_input['coinbase']
        sequence = raw_input['sequence']
    else:
        previous_output_hash = raw_input['txid']
        previous_output_vout = raw_input['vout']
        script = ''
        sequence = raw_input['sequence']
        asm = []
        try:
            raw_asm = raw_input['scriptSig']['asm']
            asm = raw_asm.split(' ')            
        except Exception, e:
            info(str(e))
            error('could not split script parts')
        # pay-from-pubkey
        if len(asm) == 1:            
            script = '[ %s ]' % asm[0]
        # pay-from-pubkey-hash or multisig
        elif len(asm) == 2:
            script = '[ %s ] [ %s ]' % (asm[0], asm[1])
            pubkey = asm[1]
            if pubkey.startswith('02') or pubkey.startswith('03') or pubkey.startswith('04'):
                try:
                    address = get_address_of_pubkey(pubkey)
                except:
                    debug(raw_input)
                    info('could not transform asm to address '+raw_asm)
                    pass
    previous_output = '%s:%i' % (previous_output_hash, previous_output_vout)
    parsed_json_input = \
    {
        'previous_output': previous_output,
        'script': script,
        'sequence': sequence,
        'address': address
    }
    return parsed_json_input

def parse_vout(raw_output):
    try:
        raw_value = raw_output['value']
        raw_script_pk = raw_output['scriptPubKey']
        raw_type = raw_script_pk['type']        
        raw_asm = raw_script_pk['asm']
        asm = raw_asm.split(' ')
        amount = to_satoshi(raw_value)
    except Exception, e:
        info(str(e))
        error('could not get script infos')
    script = ''
    address = None
    # pay-to-pubkey-hash
    if raw_type == 'pubkeyhash':
        if len(asm) == 5:
            script = 'dup hash160 [ %s ] equalverify checksig' % asm[2]
            try:
                address = raw_script_pk['addresses'][0]
            except:
                info(raw_output)
                error('could not get address for output')
        else:
            info(raw_output)
            error('number of asm splits does not match')
    # pay-to-multisig
    elif raw_type == 'multisig':
        # m-of-2 multisig
        if len(asm) == 5:
            script = '%s [ %s ] [ %s ] %s checkmultisig' % (asm[0], asm[1], asm[2], asm[3])
        # m-of-3 multisig
        elif len(asm) == 6:
            script = '%s [ %s ] [ %s ] [ %s ] %s checkmultisig' % (asm[0], asm[1], asm[2], asm[3], asm[4])
        else:
            debug(raw_output)
            debug('transaction with unusual number of multisig parts found')
    # pay-to-pubkey
    elif raw_type == 'pubkey':
        if len(asm) == 2:
            script = '[ %s ] checksig' % asm[0]        
            try:
                address = raw_script_pk['addresses'][0]
            except:
                info(raw_output)
                error('could not get address for output')        
        else:
            info(raw_output)
            error('number of asm splits does not match')
    # pay-to-script-hash
    elif raw_type == 'scripthash':
        if len(asm) == 3:
            script = 'hash160 [ %s ] equal' % asm[1]
            try:
                address = raw_script_pk['addresses'][0]
            except:
                info(raw_output)
                error('could not get address for output')
    # pay-to-script-hash
    elif raw_type == 'nulldata':
        if len(asm) == 2:
            script = 'return [ %s ]' % asm[1]
    # otherwise: type is nonstandard
    parsed_json_output = \
    {
        'value': amount,
        'script': script,
        'address': address
    }
    return parsed_json_output

def parse_transaction(decoded_tx):
    try:
        parsed_json_tx = \
        {
            'hash': decoded_tx['txid'],
            'version': decoded_tx['version'],
            'locktime': decoded_tx['locktime'],
            'inputs': [],
            'outputs': []
        }
    except Exception as e:
        info(decoded_tx)
        info(str(e))
        error('could not extract basic properties of the transaction')
    # blocktime is only available for confirmed transactions
    if 'blocktime' in decoded_tx:
        parsed_json_tx['blocktime'] = decoded_tx['blocktime']
    # parse all inputs
    parsed_json_tx['inputs'] = map(parse_vin, decoded_tx['vin'])
    # parse all outputs
    parsed_json_tx['outputs'] = map(parse_vout, decoded_tx['vout'])
    # store temporary for later usage and fast lookup
    if cache_parsed_txs:
        parsed_tx_storage[parsed_json_tx['hash']] = parsed_json_tx
    return parsed_json_tx

def parse_as_output_to(to_address, tx):
    output_infos = []
    if tx != None:
        if 'blockhash' in tx and 'blockheight' not in tx:
            # listalltransactions does not include mempool txs
            # but orphaned transactions - this is one
            debug('orphaned transaction found: %s, block: %s' % (tx['txid'], tx['blockhash']))
            return []
        # temporary store transaction for later use and fast lookup
        if cache_transactions:
            transactions_storage[tx['txid']] = tx
        for vout, output in enumerate(tx['vout']):
            try:                
                # sx lists only pay-to-pubkey-hash outputs
                output_type = output['scriptPubKey']['type']
                if output_type != 'pubkeyhash':
                    continue                    
                # only outputs to to_address are of interest
                output_addrs = output['scriptPubKey']['addresses']
                if to_address not in output_addrs:
                    continue
                output_infos.append({
                    'address': to_address,
                    'output': '%s:%i' % (tx['txid'], vout),
                    'output_height': str(tx['blockheight']),
                    'value': to_satoshi(output['value'])
                })
            except Exception, e:
                info(str(e))
                error('could not parse output sent to '+to_address)
                continue
    else:
        error('unable to convert None')
        return []
    return output_infos

# used as a key function for sorting history
def output_height(item):
    try:
        return item['output_height']
    except (KeyError, TypeError):
        info(item)
        error('could not extract output_height')
        return -1


# unimplemented methods
def get_pubkey(addr):
    error('this method is not implemented')

def pubkey(key):
    error('this method is not implemented')

def get_utxo(addr, value):
    # easy to do with rpc.getallbalance(addr)
    error('this method is not implemented')

def rawscript(script):
    error('this method is not implemented')

def mktx(inputs_outputs):
    error('this method is not implemented')

def get_addr_from_key(key):
    # get_address_of_pubkey(pubkey)
    error('this method is not implemented')

def sign(tx, priv_key, inputs):
    error('this method is not implemented')

def validate_sig(filename, index, script_code, signature):
    error('this method is not implemented')

def validate_tx(filename):
    # open file, rpc.decoderawtransaction?
    error('this method is not implemented')

def send_tx(filename, host='localhost', port=8333):
    # open file, rpc.sendrawtransaction
    error('this method is not implemented')

def broadcast_tx(filename):
    # open file, rpc.sendrawtransaction
    error('this method is not implemented')


# show some stats
def print_db_usage():
    info('Storage usage:')
    info('blocktimes_storage: %i' % len(blocktimes_storage))
    info('transactions_storage: %i' % len(transactions_storage))
    info('parsed_tx_storage: %i' % len(parsed_tx_storage))

# rpc connection and bitcoind tests
def test_rpc_connection():
    try:
        rpc.getinfo()
        info('rpc connection established')
    except JSONRPCException as e:
        info(e.error['message'])
        error('rpc connection failed')
    except Exception as e:
        info(str(e))
        error('rpc disabled or credentials missing?')
    return True

def test_tx_blockhash():
    exodus_tx_hash = '546a406a131089e7c2f27d34a93a4d27441d98d096404d6737c5ad5b5e61a09b'
    exodus_tx_blockhash = '0000000000000023d3f7e09f130dd117d80d112da4db519111bc61b860dd3bcb'
    try:
        tx = rpc.getrawtransaction(exodus_tx_hash, 1)
        info('block hash of first exodus tx: '+tx['blockhash'])
        if exodus_tx_blockhash == tx['blockhash']:
            info('block hash does match')
        else:
            error('block hash of first exodus transaction does not match')
    except JSONRPCException as e:
        info(e.error['message'])
        error('test of block hash of first exodus transaction failed')
    except Exception as e:
        info(str(e))
        error('test of block hash of first exodus transaction failed')
    return True

def test_tx_blockheight():
    exodus_tx_hash = '546a406a131089e7c2f27d34a93a4d27441d98d096404d6737c5ad5b5e61a09b'
    exodus_tx_blockheight = 249498
    try:
        tx = rpc.getrawtransaction(exodus_tx_hash, 1)
        info('block height of first exodus tx: '+str(tx['blockheight']))
        if exodus_tx_blockheight == tx['blockheight']:
            info('block height is correct')
        else:
            error('height of block of first exodus transaction does not match')
    except JSONRPCException as e:
        info(e.error['message'])
        info('could not fetch block height')
        error(address_index_not_available)
    except Exception as e:
        info(str(e))
        info('could not fetch block height')
        error(address_index_not_available)
    return True

def test_tx_position():
    exodus_tx_hash = '546a406a131089e7c2f27d34a93a4d27441d98d096404d6737c5ad5b5e61a09b'
    exodus_tx_position = 23
    try:
        tx = rpc.getrawtransaction(exodus_tx_hash, 1)
        info('index of %s in block: %i' % (exodus_tx_hash, tx['position']))
        if exodus_tx_position == tx['position']:
            info('transaction of first exodus transaction position is correct')
        else:
            error('transaction position of first exodus transaction does not match')
    except JSONRPCException as e:
        info(e.error['message'])
        info('could not fetch transaction position within block')
        error(address_index_not_available)
    except Exception as e:
        info(str(e))
        info('could not fetch transaction position within block')
        error(address_index_not_available)
    return True

def test_list_all_txs():
    exodus_addr = '1EXoDusjGwvnjZUyKkxZ4UHEf77z6A5S4P'
    exodus_tx_hash = '546a406a131089e7c2f27d34a93a4d27441d98d096404d6737c5ad5b5e61a09b'
    try:
        all_txs = rpc.listalltransactions(exodus_addr, 1, 0, 1)
        tx_hash = all_txs[0]['txid']
        info('hash of first exodus tx: '+tx_hash)
        if exodus_tx_hash == tx_hash:
            info('test of rpc call listalltransactions passed')
        else:
            error('transaction hash of first exodus transaction does not match')
    except JSONRPCException as e:
        info(e.error['message'])
        info('could not fetch all transactions')
        error(address_index_not_available)
    except Exception as e:
        info(str(e))
        info('could not fetch all transactions')
        error(address_index_not_available)
    return True

def test_get_balance():
    satoshis_addr = '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa'
    try:
        balance = rpc.getallbalance(satoshis_addr)
        info('balance of %s: %f' % (satoshis_addr, balance))
        if balance > 0:
            info('test of rpc call getallbalance passed')    
        else:
            error('satoshi moved genesis coins or test of getallbalance failed')
    except JSONRPCException as e:
        info(e.error['message'])
        info('could not get balance of '+satoshis_addr)
        error(address_index_not_available)
    except Exception as e:
        info(str(e))
        info('could not get balance of '+satoshis_addr)
        error(address_index_not_available)
    return True

def test_bitcoind_addr_index():
    test_rpc_connection()
    test_tx_blockhash()
    test_tx_blockheight()
    test_tx_position()
    test_list_all_txs()
    test_get_balance()
    info('rpc and bitcoind tests passed')


# run tests on standalone startup
if __name__ == '__main__':    
    msc_globals.init()
    msc_globals.d = True
    test_bitcoind_addr_index()
