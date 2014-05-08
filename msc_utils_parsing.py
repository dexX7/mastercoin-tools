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

import traceback,glob,json
from msc_utils_obelisk import *

currency_type_dict={'00000001':'Mastercoin','00000002':'Test Mastercoin'}
reverse_currency_type_dict={'Mastercoin':'00000001','Test Mastercoin':'00000002'}
transaction_type_dict={'0000':'Simple send', '0014':'Sell offer', '0016':'Sell accept', '0032':'Fixed property creation', '0033': 'Fundraiser property creation', '0035': 'Fundraiser cancellation'}
sell_offer_action_dict={'00':'Undefined', '01':'New', '02':'Update', '03':'Cancel'}
exodus_address='1EXoDusjGwvnjZUyKkxZ4UHEf77z6A5S4P'
first_exodus_bootstrap_block=249498
last_exodus_bootstrap_block=255365
exodus_bootstrap_orig_deadline=1377993600
exodus_bootstrap_deadline=1377993874
seconds_in_one_year=31556926
multisig_disabled=False
dust_limit=5555
MAX_PUBKEY_IN_BIP11=3
MAX_COMMAND_TRIES=3
features_enable_dict={'distributed exchange':290630}
LAST_VALIDATED_BLOCK_NUMBER_FILE='last_validated_block.txt'
max_payment_timeframe=255

#remove unicode
def dehexify(hex_str):
    temp_str=[]
    for let in hex_str:
        if ord(let) < 128:
            temp_str.append(let)
        else:
            temp_str.append('?')
    return ''.join(temp_str)

# used as a key function for sorting outputs of msc tx
def get_dataSequenceNum(item):
    try:
        data_script=item['script'].split()[3].zfill(42)
        dataSequenceNum=data_script[2:4]
        return dataSequenceNum
    except KeyError, IndexError:
        return None

def refreshCurrencyIDs():
    try:
        property_files = glob.glob('properties/*.json')
        for property_file in property_files:
            currency_type_dict[ hex(int(str(property_file.split('.')[0].split('-')[1])))[2:].rjust(8,"0") ] = 'Smart Property'
            #reverse_currency_type_dict['Smart Property'] = str(property_file.split('.')[0].split('-')[1])
    except Exception,e:
        error('error getting glob of properties',e)

def get_currency_type_from_dict(currencyId):
    refreshCurrencyIDs()
    if currency_type_dict.has_key(currencyId):
        return currency_type_dict[currencyId]
    else:
        return 'Unknown currency id '+str(currencyId)

def get_transaction_type_from_dict(transactionType):
    if transaction_type_dict.has_key(transactionType):
        return transaction_type_dict[transactionType]
    else:
        return 'Unknown transaction type '+str(transactionType)

def bootstrap_dict_per_tx(block, tx_hash, address, value, dacoins):
    tx_dict={"block": str(block), "tx_hash": tx_hash, "currency_str": "Mastercoin and Test Mastercoin", "to_address": address, "from_address": "exodus", "exodus": True, "tx_method_str": "exodus", "orig_value":value ,"formatted_amount": from_satoshi(dacoins), "tx_type_str": "exodus"}
    return tx_dict

def parse_data_script(data_script):
    parse_dict={}
    if len(data_script)<42:
        info('invalid data script '+data_script.encode('hex_codec'))
        return parse_dict
    parse_dict['baseCoin']=data_script[0:2] # 00 for normal bitcoin (different for multisig?)
    parse_dict['dataSequenceNum']=data_script[2:4]
    parse_dict['transactionVersion']=data_script[4:8]
    parse_dict['transactionType']=data_script[8:12]
    parse_dict['currencyId']=data_script[12:20]
    parse_dict['amount']=data_script[20:36]
    parse_dict['bitcoin_amount_desired']=data_script[36:52]
    parse_dict['block_time_limit']=data_script[52:54]
    return parse_dict

def parse_2nd_data_script(data_script):
    parse_dict={}
    if len(data_script)<42:
        info('invalid data script '+data_script.encode('hex_codec'))
        return parse_dict
    parse_dict['fee_required']=data_script[4:10]
    parse_dict['action']=data_script[10:12]
    parse_dict['should_be_zeros']=data_script[12:54]
    try:
        parse_dict['action_str']=sell_offer_action_dict[parse_dict['action']]
    except KeyError:
        parse_dict['action_str']='unknown '+str(parse_dict['action'])
    return parse_dict

def parse_bitcoin_payment(tx, tx_hash='unknown'):
    json_tx=get_json_tx(tx)
    outputs_list=json_tx['outputs']
    
    from_address=''
    to_address=''
    total_inputs=0
    total_outputs=0
    try:
        inputs=json_tx['inputs']
        for i in inputs:
            if i['address'] != None:
                if from_address != '':
                    from_address+=';'
                from_address+=i['address']
            else:
                from_address='not signed'
            input_value=get_value_from_output(i['previous_output'])
            if input_value==None:
                error('failed get_value_from_output')
            total_inputs+=input_value
    except KeyError, IndexError:
        error('inputs error')
    try:
        for o in outputs_list:
            if o['address'] != None:
                if to_address != '':
                    to_address+=';'
                to_address+=o['address']+':'+from_satoshi((o['value']))
            total_outputs+=(o['value'])
    except KeyError, IndexError:
        error('outputs error')

    parse_dict={}
    parse_dict['from_address']=from_address
    parse_dict['to_address']=to_address
    parse_dict['fee']=from_satoshi(total_inputs-total_outputs)
    parse_dict['tx_hash']=tx_hash
    parse_dict['invalid']=(True,'bitcoin payment')
    parse_dict['icon']='bitcoin'
    parse_dict['icon_text']='Bitcoin payment'
    parse_dict['color']='bgc-done'
    return parse_dict

def peek_and_decode(outputs_list):
    # locate data output by checking:
    # Bytes two to eight must equal 00
    # Byte nine must equal 01 or 02
    data_output=None
    data_seq=None
    for o in outputs_list:
        data_script=o['script'].split()[3].zfill(42)
        data_dict=parse_data_script(data_script)
        if (data_dict['transactionType'] == '0000' and \
            ((data_dict['currencyId'] == '00000001' or \
              data_dict['currencyId'] == '00000002'))):
            # invalidate if data was already found before among those outputs
            if data_output != None:
                info('invalid mastercoin tx (multiple valid looking data addresses)')
                return ((True,'multiple valid looking data addresses'), None, None)
            data_output=o
            data_seq=get_dataSequenceNum(o)
    return ((False, ''), data_output, data_seq)

def class_A_Level_1(outputs_list):
    (validity_tuple, data_output, data_seq)=peek_and_decode(outputs_list)
    if (validity_tuple[0]==True):
        return (validity_tuple, None, None)

    if data_output == None:
        info('no data output found')
        return ((True,'no data output found'), None, None)

    recipient=None
    # get the sequence number of this address and add one to it to get the recipient
    recipient_seq=(int(data_seq,16)+1)%256
    for o in outputs_list:
        seq=get_dataSequenceNum(o)
        if int(seq,16)==int(recipient_seq):
            # taking the first one (there may be more)
            recipient=o['address']
    # on failure with 3 outputs case, take non data/exodus to be the recipient
    if len(outputs_list) == 3:
        for o in outputs_list:
            if o['address'] != exodus_address and o != data_output:
                recipient = o['address']
    return ((False,''), data_output, recipient)

# "Class A" transaction
def parse_simple_basic(tx, tx_hash='unknown', after_bootstrap=True):
    json_tx=get_json_tx(tx)
    outputs_list=json_tx['outputs']
    (outputs_list_no_exodus, outputs_to_exodus, different_outputs_values, invalid)=examine_outputs(outputs_list, tx_hash, tx)
    if invalid != None:
        info(str(invalid[1])+' on '+tx_hash)
        return {'invalid':invalid, 'tx_hash':tx_hash}

    num_of_outputs=len(outputs_list)

    # collect all "from addresses" (normally only a single one)
    from_address=''
    try:
        # the from address is the one with the highest value
        from_address=select_input_reference(json_tx['inputs'])

        if from_address == None:
            info('invalid from address (address with largest value is None) at tx '+tx_hash)
            return {'invalid':(True,'address with largest value is None'), 'tx_hash':tx_hash}

        #######################################################################
        # follow Class A P&D https://github.com/mastercoin-MSC/spec/issues/29 #
        #######################################################################
        # Level 1
        # Take all the outputs that have the same value as the value to the Exodus address
        # (the first exodus output is checked here)
        exodus_value=outputs_to_exodus[0]['value']
        outputs_with_exodus_value=different_outputs_values[exodus_value]
        # locate data address by checking:
        # Bytes two to eight must equal 00
        # Byte nine must equal 01 or 02
        (invalidity_tuple, data_output, recipient)=class_A_Level_1(outputs_with_exodus_value)
        # check for invalids
        if invalidity_tuple[0] == True:
            info(invalidity_tuple[1]+' '+tx_hash)
        if data_output == None or recipient == None:
            # Level 2
            # If the sequence number can't be found you can expand the searching range to
            # include all outputs
            (invalidity_tuple, level2_data_output, level2_recipient)=class_A_Level_1(outputs_list)
            # check for invalids
            if invalidity_tuple[0] == True:
                info(invalidity_tuple[1]+' '+tx_hash)
            if level2_data_output != None and level2_recipient != None:
                debug('Level 2 peek and decode for '+tx_hash)
                data_output=level2_data_output
                recipient=level2_recipient
            else:
                # Level 3
                # all output values are equal in size and if there are three outputs
                # of these type of outputs total
                if (len(different_outputs_values)==1 and len(different_outputs_values[0])==3 and data_output != None):
                    debug('Level 3 peek and decode for '+tx_hash)
                    # Collect all outputs and remove the data address and the Exodus output.
                    # The remaining output is the recipient address.
                    all_addresses=[d['address'] for d in different_outputs_values[0]]
                    all_addresses.remove(exodus_address)
                    all_addresses.remove(data_output['address'])
                    recipient=all_addresses[0]
                else:
                    info('invalid mastercoin tx (failed all peek and decode levels) '+tx_hash)
                    return parse_bitcoin_payment(tx, tx_hash)
        else:
            debug('Level 1 peek and decode for '+tx_hash)         

        to_address=recipient
        data_script=data_output['script'].split()[3].zfill(42)
        data_dict=parse_data_script(data_script)
        if len(data_dict) >= 6: # at least the basic 6 fields were parsed
            parse_dict=data_dict
            parse_dict['tx_hash']=tx_hash
            parse_dict['from_address']=from_address
            parse_dict['to_address']=to_address
            parse_dict['formatted_amount']=from_hex_satoshi(data_dict['amount'])
            parse_dict['currency_str']=get_currency_type_from_dict(data_dict['currencyId'])
            parse_dict['tx_type_str']=get_transaction_type_from_dict(data_dict['transactionType'])
            parse_dict['tx_method_str']='basic'
            return parse_dict
        else:
            info('invalid mastercoin tx with less than 6 fields '+tx_hash)
            return {'invalid':(True,'invalid mastercoin tx with less than 6 fields'), 'tx_hash':tx_hash}
    except (KeyError, IndexError, TypeError) as e:
        info('invalid mastercoin tx ('+str(e)+') at tx '+tx_hash)
        return {'invalid':(True,'bad parsing'), 'tx_hash':tx_hash}

# only pay-to-pubkey-hash inputs are allowed
# the sender is largest contributor of the transaction
def select_input_reference(inputs):
    inputs_values_dict={}
    for i in inputs:
        prev_output=get_vout_from_output(i['previous_output'])
        # skip, if input is not usable
        if prev_output==None:
            continue
        # skip, if input is not pay-to-pubkey-hash
        if not is_script_paytopubkeyhash(prev_output['script']):
            return None
        input_value=prev_output['value']
        input_address=i['address']
        if inputs_values_dict.has_key(input_address):
            inputs_values_dict[input_address]+=int(input_value)
        else:
            inputs_values_dict[input_address]=int(input_value)
    # no valid input found
    if len(inputs_values_dict)==0:
        return None
    # the input reference is the one with the highest value
    from_address=max(inputs_values_dict, key=inputs_values_dict.get)
    return from_address

# only non-exodus, pay-to-pubkey-hash outputs are considered
# other output types are ignores, sender may not be the receiver
# the receiver is derived from the last remaining output
def select_receiver_reference(input_addr, outputs):
    to_address='unknown'
    sender_references=0    
    # filter outputs to consider only pay-to-pubkey-hash outputs
    potential_recipients=[]
    for o in outputs:
        if is_script_paytopubkeyhash(o['script']):
            address=o['address']
            # count outputs to sender
            if address==input_addr:
                sender_references+=1
            potential_recipients.append(address)
    # recipient is last output, but first reference to sender may be skipped
    remaining=len(potential_recipients)  
    if remaining==1 or sender_references>1 or remaining>0 and potential_recipients[-1]!=input_addr:
        to_address=potential_recipients[-1]
    # strip change output
    elif remaining>1 and potential_recipients[-1]==input_addr:
        to_address=potential_recipients[-2]
    return to_address

def get_obfus_str_list(address, length):
    obfus_str_list=[]
    obfus_str_list.append(get_sha256(address)) # 1st obfus is simple sha256
    for i in range(length):
        if i<length-1: # one less obfus str is needed (the first was not counted)
            obfus_str_list.append(get_sha256(obfus_str_list[i].upper())) # i'th obfus is sha256 of upper prev
    return obfus_str_list

def parse_multisig(tx, tx_hash='unknown'):
    if multisig_disabled:
        info('multisig is disabled: '+tx_hash)
        return {'invalid':(True,'multisig is disabled'), 'tx_hash':tx_hash}
    parsed_json_tx=get_json_tx(tx)
    parse_dict={}
    
    # the sender is largest contributor of the transaction
    input_addr=select_input_reference(parsed_json_tx['inputs'])
    
    if input_addr == None:
        info('invalid from address (address with largest value is None) or non-pay-to-pubkeyhash supplied at tx '+tx_hash)
        return {'invalid':(True,'address with largest value is None or non-pay-to-pubkeyhash supplied'), 'tx_hash':tx_hash}
                                      
    # the receiver is not exodus and preferably not sender, not all tx types require a receiver
    all_outputs=parsed_json_tx['outputs']
    (outputs_list_no_exodus, outputs_to_exodus, different_outputs_values, invalid)=examine_outputs(all_outputs, tx_hash, tx)
    if invalid != None:
        info(str(invalid[1])+' on '+tx_hash)
        return {'tx_hash':tx_hash, 'invalid':invalid}
        
    to_address=select_receiver_reference(input_addr, outputs_list_no_exodus)

    data_script_list = []
    for idx,o in enumerate(outputs_list_no_exodus):
        if o['address']==None: # This should be the multisig
            script=o['script']
            # verify that it is a multisig
            if not script.endswith('checkmultisig'):
                error('Bad multisig data script '+script)
            fields=script.split('[ ')

            # more sanity checks on BIP11
            max_pubkeys=int(fields[-1].split()[-2])
            if max_pubkeys < 2 or max_pubkeys > 3:
                info('error m-of-n with n out of range ('+str(max_pubkeys)+'). skipping tx '+tx_hash)
                return {'tx_hash':tx_hash, 'invalid':(True, 'error m-of-n with n out of range')}

            # parse the BIP11 pubkey list
            for i in range(MAX_PUBKEY_IN_BIP11-1):
                index=i+2 # the index of the i'th pubkey
                try:
                    data_script = fields[index].split(' ]')[0]
                    if data_script not in data_script_list: 
                        data_script_list.append(data_script)
                except IndexError:
                    break

            # prepare place holder lists for obfus,deobfus,data_dict
            dataHex_deobfuscated_list=[]
            data_dict_list=[]

            list_length=len(data_script_list)
            obfus_str_list=get_obfus_str_list(input_addr, list_length)

            for i in range(list_length):
                dataHex_deobfuscated_list.append(get_string_xor(data_script_list[i][2:-2],obfus_str_list[i][:62]).zfill(64)+'00')

            try:
                data_dict=parse_data_script(dataHex_deobfuscated_list[0])
            except IndexError:
                error('cannot parse dataHex_deobfuscated_list')

            # no recipient? allow for sell offer
            if to_address=='unknown' and (data_dict['transactionType'] == '0000' or data_dict['transactionType'] == '0016'):
                info('no recipient tx '+tx_hash)
                return {'tx_hash':tx_hash, 'invalid':(True, 'no recipient')}

            if len(data_dict) >= 6: # at least 6 basic fields got parse on the first dataHex
                amount=int(data_dict['amount'],16)/100000000.0
                parse_dict=data_dict
                parse_dict['tx_hash']=tx_hash
                parse_dict['formatted_amount'] = formatted_decimal(amount)
                parse_dict['currency_str'] = get_currency_type_from_dict(data_dict['currencyId'])
                parse_dict['tx_type_str'] = get_transaction_type_from_dict(data_dict['transactionType'])
                parse_dict['tx_method_str'] = 'multisig'

                if data_dict['transactionType'] == '0000': # Simple send
                    # remove irrelevant keys
                    parse_dict.pop('bitcoin_amount_desired', None)
                    parse_dict.pop('block_time_limit', None)
                else:
                    if data_dict['transactionType'] == '0014': # Sell offer
                        # check feature is enabled
                        if currency_type_dict[data_dict['currencyId']]=='Mastercoin':
                            (height,index)=get_tx_index(tx_hash)
                            if height == -1:
                                error('failed getting height of '+tx_hash)
                            if int(features_enable_dict['distributed exchange']) > int(height):
                                info('distributed exchange of msc is not yet enabled '+tx_hash)
                                parse_dict['invalid']=(True, 'distributed exchange of msc is not yet enabled')
                                parse_dict['color']='bgc-invalid'
                                parse_dict['icon_text']='Invalid sell offer'
                                parse_dict['from_address']=input_addr
                                parse_dict['to_address']=to_address
                                return parse_dict

                        bitcoin_amount_desired=int(data_dict['bitcoin_amount_desired'],16)/100000000.0
                        if amount > 0:
                            price_per_coin=bitcoin_amount_desired/amount
                        else:
                            price_per_coin=0

                        # duplicate with another name
                        parse_dict['formatted_amount_available'] = parse_dict['formatted_amount']
                        # format fields
                        parse_dict['formatted_bitcoin_amount_desired']= formatted_decimal(bitcoin_amount_desired)
                        parse_dict['formatted_price_per_coin']= formatted_decimal(price_per_coin)
                        parse_dict['formatted_block_time_limit']= str(int(data_dict['block_time_limit'],16))

                        if len(dataHex_deobfuscated_list)>1: # currently true only for Sell offer (?)
                            data_dict2=parse_2nd_data_script(dataHex_deobfuscated_list[1])

                            # verify positive sell offer amount
                            if amount == 0: # this is allowed only on Cancel action
                                if data_dict['transactionVersion']=='0000' or data_dict2['action_str']=='Cancel':
                                    debug('cancel sell offer with zero amount on '+tx_hash)
                                else:
                                    parse_dict['invalid']=(True,'zero sell offer amount')
                            else:
                                if amount < 0:
                                    info('BUG: negative sell offer amount on '+tx_hash)
                                    parse_dict['invalid']=(True,'negative sell offer amount')


                            if data_dict2['should_be_zeros'] == '0000000000000000000000000000000000000000000' or \
                               data_dict2['should_be_zeros'] == '000000000000000000000000000000000000000000':
                                data_dict2.pop('should_be_zeros')
                                for key in data_dict2:
                                    parse_dict[key]=data_dict2[key]
                                parse_dict['formatted_fee_required'] = from_hex_satoshi(data_dict2['fee_required'])
                            else:
                                parse_dict['invalid']=(True,'invalid last data script in BIP11')
                                return parse_dict
                    else:
                        if data_dict['transactionType'] == '0016': # Sell accept
                            # check feature is enabled
                            if currency_type_dict[data_dict['currencyId']]=='Mastercoin' and tx_hash != 'unknown':
                                (height,index)=get_tx_index(tx_hash)
                                if height == -1 or height == 'failed:':
                                    error('failed getting height of '+tx_hash)
                                if int(features_enable_dict['distributed exchange']) > int(height):
                                    info('distributed exchange of msc is not yet enabled '+tx_hash)
                                    parse_dict['invalid']=(True, 'distributed exchange of msc is not yet enabled')
                                    parse_dict['color']='bgc-invalid'
                                    parse_dict['icon_text']='Invalid sell accept'
                                    parse_dict['from_address']=input_addr
                                    parse_dict['to_address']=to_address
                                    return parse_dict

                            # remove irrelevant keys
                            parse_dict.pop('bitcoin_amount_desired', None)
                            parse_dict.pop('block_time_limit', None)
                            # duplicate with another name
                            parse_dict['formatted_amount_requested'] = parse_dict['formatted_amount']
                            # add place holders
                            parse_dict['bitcoin_required'] = 'Not available'
                            parse_dict['sell_offer_txid'] = 'Not available'
                            parse_dict['payment_txid'] = 'Not available'
                            parse_dict['status'] = 'Awaiting payment'
                            # parse as bitcoin payment to get the tx fee
                            bitcoin_dict=parse_bitcoin_payment(tx, tx_hash)
                            parse_dict['formatted_fee']=bitcoin_dict['fee']
                        else:
                            if data_dict['transactionType'] == '0032' or data_dict['transactionType'] == '0033': # Smart Property
                                if idx == len(outputs_list_no_exodus)-1: # we are on last output
                                    long_packet = ''
                                    for datahex in dataHex_deobfuscated_list:
                                        if len(datahex)<42:
                                            info('invalid data script '+data_script.encode('hex_codec'))
                                            parse_dict['invalid']=(True, 'datahex is not right length')
                                        parse_dict['baseCoin']=datahex[0:2] # 00 for BTC
                                        long_packet += datahex[4:-2].upper()

                                    #set these fields for validation
                                    parse_dict['formatted_amount'] = 0
                                    parse_dict['currency_str'] = 'Smart Property'
                                    parse_dict['currencyId'] = 0

                                    #unneeded fields
                                    parse_dict.pop('amount', None)
                                    parse_dict.pop('bitcoin_amount_desired', None)
                                    parse_dict.pop('block_time_limit', None)

                                    parse_dict['tx_hash'] = tx_hash

                                    #fixed fields
                                    parse_dict['transactionVersion']=long_packet[0:4]
                                    parse_dict['transactionType']=long_packet[4:8]
                                    parse_dict['ecosystem']=long_packet[8:10]
                                    parse_dict['property_type']=long_packet[10:14]
                                    parse_dict['previous_property_id']=long_packet[14:22]

                                    #non-hex version for UI
                                    parse_dict['formatted_transactionVersion']=int(long_packet[0:4],16)
                                    parse_dict['formatted_transactionType']=int(long_packet[4:8],16)
                                    parse_dict['formatted_ecosystem']=int(long_packet[8:10],16)
                                    parse_dict['formatted_property_type']=int(long_packet[10:14],16)
                                    parse_dict['formatted_previous_property_id']=int(long_packet[14:22],16)
                                    #prepare var-fields for processing
                            
                                    #var fields
                                    try:
                                        spare_bytes = []
                                        for i in range(0,len(long_packet[22:]),2):
                                            spare_bytes.append(long_packet[22:][i] + long_packet[22:][i+1])
                                        
                                        prop_cat = ''.join(spare_bytes[0:spare_bytes.index('00')]).decode('hex')
                                        prop_cat=dehexify(prop_cat)

                                        spare_bytes = spare_bytes[spare_bytes.index('00')+1:]
                                        prop_subcat = ''.join(spare_bytes[0:spare_bytes.index('00')]).decode('hex') 
                                        prop_subcat=dehexify(prop_subcat)

                                        spare_bytes = spare_bytes[spare_bytes.index('00')+1:]
                                        prop_name = ''.join(spare_bytes[0:spare_bytes.index('00')]).decode('hex') 
                                        prop_name=dehexify(prop_name)

                                        spare_bytes = spare_bytes[spare_bytes.index('00')+1:]
                                        prop_url = ''.join(spare_bytes[0:spare_bytes.index('00')]).decode('hex')
                                        prop_name=dehexify(prop_name)

                                        spare_bytes = spare_bytes[spare_bytes.index('00')+1:]
                                        prop_data = ''.join(spare_bytes[0:spare_bytes.index('00')]).decode('hex') 
                                        prop_data=dehexify(prop_data)

                                        parse_dict['propertyCategory']=prop_cat
                                        parse_dict['propertySubcategory']=prop_subcat
                                        parse_dict['propertyName']=prop_name
                                        parse_dict['propertyUrl']=prop_url
                                        parse_dict['propertyData']=prop_data
                                    except Exception,e:
                                        debug(['cannot parse smart property fields',e, traceback.format_exc(), tx_hash])
                                        return {'tx_hash':tx_hash, 'invalid':(True, 'malformed smart property fields')}

                                    #fixed fields after var fields
                                    try:
                                        if data_dict['transactionType'] == '0032':
                                            spare_bytes = ''.join(spare_bytes[spare_bytes.index('00')+1:])
                                            parse_dict['numberOfProperties']=str(int(spare_bytes[:16],16))
                                        else:
                                            spare_bytes = ''.join(spare_bytes[spare_bytes.index('00')+1:])
                                            parse_dict['currencyIdentifierDesired']=str(int(spare_bytes[:8],16))

                                            spare_bytes = ''.join(spare_bytes[8:])
                                            parse_dict['numberOfProperties']=str(int(spare_bytes[:16],16))

                                            spare_bytes = ''.join(spare_bytes[16:])
                                            parse_dict['deadline']=str(int(spare_bytes[:16],16))

                                            spare_bytes = ''.join(spare_bytes[16:])
                                            parse_dict['earlybirdBonus']=str(int(spare_bytes[:2],16))

                                            spare_bytes = ''.join(spare_bytes[2:4])
                                            parse_dict['percentageForIssuer']=str(int(spare_bytes[:2],16))
                                    except Exception,e:
                                        debug(['cannot parse smart property fields',e, traceback.format_exc(), tx_hash])
                                        return {'tx_hash':tx_hash, 'invalid':(True, 'malformed smart property fields')}

                            else: # non valid tx type
                                if data_dict['transactionType'] == '0035': # Smart Property Cancellation
                                    #should only be one packet for this tx type
                                    dataHex = dataHex_deobfuscated_list[0][4:]
                                    parse_dict['transactionVersion']=dataHex[0:4]
                                    parse_dict['transactionType']=dataHex[4:8]
                                    parse_dict['property_type']=dataHex[8:16]

                                    #set these fields for validation
                                    parse_dict['formatted_amount'] = 0
                                    parse_dict['currency_str'] = 'Smart Property'
                                    parse_dict['currencyId'] = 0

                                    #unneeded fields
                                    parse_dict.pop('amount', None)
                                    parse_dict.pop('bitcoin_amount_desired', None)
                                    parse_dict.pop('block_time_limit', None)
                                else:
                                    return {'tx_hash':tx_hash, 'invalid':(True, 'non supported tx type '+data_dict['transactionType'])}

        else: # not the multisig output
            # the output with dust
            parse_dict['to_address']=o['address']

    if parse_dict == {}:
        error('Bad parsing of multisig: '+tx_hash)

    parse_dict['from_address']=input_addr
    parse_dict['to_address']=to_address
                
    return parse_dict

def examine_outputs(outputs_list, tx_hash, raw_tx):
        # if we're here, then 1EXoDus is within the outputs. Remove it, but ...
        outputs_list_no_exodus=[]
        outputs_to_exodus=[]
        different_outputs_values={}
        for o in outputs_list:
            # ignore outputs which are not pay-to-pubkey-hash or multisig
            if not (is_script_paytopubkeyhash(o['script']) or is_script_multisig(o['script'])):
                continue
            if o['address']!=exodus_address:
                outputs_list_no_exodus.append(o)
            else:
                outputs_to_exodus.append(o)
            output_value=o['value']
            if different_outputs_values.has_key(output_value):
                different_outputs_values[output_value].append(o)
            else:
                different_outputs_values[output_value]=[o]
        # take care if multiple 1EXoDus exist (for the case that someone sends msc
        # to 1EXoDus, or have 1EXoDus as change address, or sends from 1EXoDus)
        if len(outputs_to_exodus) != 1:
            # support the special case of sending from 1EXoDus
            json_tx=get_json_tx(raw_tx)
            inputs_list=json_tx['inputs']
            from_exodus=False
            for i in inputs_list:
                if i['address']==exodus_address:
                    from_exodus=True
                    break
            if from_exodus: # 1EXoDus has sent this tx
                # Maximal 2 values are valid (dust and change)
                if len(different_outputs_values.keys()) > 2:
                    error("tx sent by exodus with more than 2 different values: "+tx_hash)
                # move the dust exodus from outputs_to_exodus list to the outputs_list_no_exodus one
                if len(different_outputs_values.keys()) == 1: # change is identical to marker
                    debug("tx sent by exodus with single value")
                    # move one item from exodus to no exodus list
                    o=outputs_to_exodus.pop()
                    outputs_list_no_exodus.append(o)
                else:
                    debug("tx sent by exodus with 2 values to exodus")
                    # as there is a signle change, dust_value belongs to list with non single item
                    output_values=different_outputs_values.keys()
                    if len(different_outputs_values[output_values[0]])==1:
                        dust_value=output_values[1]
                    else:
                        dust_value=output_values[0]
                    # move the dust item from exodus to no exodus list
                    dust_outputs_to_exodus=[]
                    non_dust_outputs_to_exodus=[]
                    for o in outputs_to_exodus:
                        if o['value']==dust_value:
                            dust_outputs_to_exodus.append(o)
                        else:
                            non_dust_outputs_to_exodus.append(o)
                    # move the item
                    outputs_list_no_exodus+=[dust_outputs_to_exodus[0]]
                    outputs_to_exodus=non_dust_outputs_to_exodus+dust_outputs_to_exodus[1:]
        return (outputs_list_no_exodus, outputs_to_exodus, different_outputs_values, None)
