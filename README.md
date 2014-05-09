Bitcoin Core and mastercoin-tools
=================================



### What is this branch? ###

This is an experimental branch for very high performance usage of mastercoin-tools in 
combination with an address-indexed Bitcoin Core client. While sx is great, setting up 
sx takes a lot of time and resources and in the case of using an external obelsik server, 
parsing the complete Mastercoin history can easily take more than half a day.

This is the first attempt to find a solution inbetween.

### What can be achived ###

* Use Bitcoin Core as backend instead of sx/obelisk
* Full functionality of mastercoin-tools and no restrictions or limitations related to the 
usage of Bitcoin Core
* Confirmed to be working on Microsoft Windows 7 x64 (this was tested only)
* Parsing and validating of all Mastercoin based transactions starting from block 249498 
up to the current height of almost 300000 takes about **8 minutes** on a cheaper VPS

### How this is done ###

About 11 months ago [a popular pull request](https://github.com/bitcoin/bitcoin/pull/2802) appeared in the wild which made it possible 
to lookup all transactions associated with any address, something that is impossible otherwise 
with Bitcoin Core, but quite essential for efficient parsing of Mastercoin transactions with 
mastercoin-tools.

This basis was taken and resulted in a Bitcoin Core client which not only allows to list all 
transactions associated with any address, but also to fetch any balance and all unspent outputs 
of any address. 

Based on that the sx wrapper of mastercoin-tools was adjusted so it is compatible with such a 
Bitcoin client.

Just to be clear: this is not mastercoind or a Bitcoin Core based Mastercoin client, but the 
combination of an address-indexed Bitcoin branch and mastercoin-tools.

### Requirements and setup ###

Depending on your preferences there are two clients available: one based on the current [master](https://github.com/dexX7/bitcoin/tree/master-addrindex-extended) 
of Bitcoin Core or one that is based on [release v0.9.1](https://github.com/dexX7/bitcoin/tree/0.9.1-addrindex-extended) which may be considered as less 
"experimental" by some:

* [/bitcoin/tree/0.9.1-addrindex-extended](https://github.com/dexX7/bitcoin/tree/0.9.1-addrindex-extended)
* [/bitcoin/tree/master-addrindex-extended](https://github.com/dexX7/bitcoin/tree/master-addrindex-extended)

Build instructions can be found in [/doc#building](https://github.com/dexX7/bitcoin/tree/0.9.1-addrindex-extended/doc#building). Once bitcoind or bitcoind and Bitcoin-Qt were 
build, the client you may use at the moment could be replaced, if this is wanted. Bitcoin Core 
needs to be started with the enabled address and transaction index as well as with an enabled RPC 
interface. The bitcoin.conf could look like this:

```
server=1
txindex=1
addrindex=1
rpcuser=your_rpc_username
rpcpassword=your_rpc_password
rpcport=8332
rpcconnect=127.0.0.1
```

On the first startup the indexing needs to be done (but only once) via `-reindex`. If used with the 
GUI the client will probably ask for this step. Please note: this can take a few hours.

Once finished, please make sure the file `msc_utils_bitcoind.py` is available. Open the file 
and enter the RPC connection data [at the very top](https://github.com/dexX7/mastercoin-tools/blob/bitcoind-dev/msc_utils_bitcoind.py#L10):

```
rpcuser='your_rpc_username'
rpcpassword='your_rpc_password'
rpcconnect='127.0.0.1'
rpcport='8332'
```

In the next step `msc_utils_obelisk` needs to be replaced with `msc_utils_bitcoind` at the top 
of `msc_utils_parying.py`. If all files are used from this branch this step is not necessary.

Information about the usage of mastercoin-tools can be found in the related documents, but the 
general usage may look like this to start from scratch:

```
~/mastercoin-tools$ python msc_bootstrap.py
~/mastercoin-tools$ python msc_parse.py -d -r ./
~/mastercoin-tools$ python msc_validate.py -d
```

### State of this version ###

This is fully working with mastercoin-tools, whereby it's not guaranteed to be working with 
[Omniwallet](https://github.com/mastercoin-MSC/omniwallet) at this point, because only the required methods for mastetrcoin-tools were adopted 
at this point.

For the purpose of finding potential bugs almost all paths that have no consequences for the 
overall parsing and validation process still do throw information about potential errors and may 
cancel the process. This did not occure to me, but if it happens: it's intended. Please forward 
anything you may see in this context, so optimization potentials can be identified.

### Binaries!! ###

There are none, but they are easily to build! :)

Please consider this at this stage as developer-preview and in the case this is not only used by 
very few and for very specific applications, this may eventually change in the future.


mastercoin-tools
================

### What is it? ###
* Package of mastercoin related tools.
* The intention is to help finalizing the mastercoin spec, and enable easy further coding.

For API documentation, please [Read The Docs](http://mastercoin-tools-installer.readthedocs.org/en/latest/).


### Aim of this package ###
* Live update - direct "realtime" interaction with the bitcoin network (using
  sx).
* Multi platform - python runs on any arch.
* No additional database is needed (obelisk has its own and can be used
  remotely, and the parser/validator use filesystem and a python dict).
* Alternative code base - use libbitcoin instead of "satoshi client".
* Simple cool and mobile friendly web UI.
* Send transaction directly using a hybrid web wallet (not "Advisor").
* Support for offline wallets.
* Generate parsed data snapshots for download.
* Low CPU requirement on server side (server serves static html files and json
  which are rendered on the client side).
* API (json).


### Let's see something ###

### Already implemented ###

* Web UI with focus on usability. Mobile phones and Tablets friendly:
  https://masterchain.info
  transaction and addresses can be explored by following links
* Built in API:
 * Transactions: https://masterchain.info/tx/$TX_ID.json
 * Addresses: https://masterchain.info/addr/$ADDR.json
 * Latest transactions: https://masterchain.info/general/$CURRENCY_$PAGE_NUMBER.json
* Mastercoin verification
 * Mastercoin addresses balances: https://masterchain.info/mastercoin_verify/addresses/0
 * TMSC addresses balances: https://masterchain.info/mastercoin_verify/addresses/1
 * Transactions per address: https://masterchain.info/mastercoin_verify/transactions/
* Consensus checker:
 * https://masterchain.info/general/MSC-difference.txt
 * https://masterchain.info/general/MSC-difference.json
* Distibuted exchange (currently only TMSC is supported, but soon MSC is enabled)
* Basic hybrid web wallet
 * Wallet: https://masterchain.info/wallet.html
 * Send/Sell/Accept forms for BTC or T/MSC:
   https://masterchain.info/sendform.html?addr=182osbPxCo88oaSX4ReJwUr9uAcchmJVaL&currency=MSC
 * Orderbook: https://masterchain.info/index.html?currency=TMSC&filter=sell
 * Last deals: https://masterchain.info/index.html?currency=TMSC&filter=accept
 * Offline transaction: https://masterchain.info/offlinesign.html


### Example UI pages ###

TMSC on example address showing distributed exchange activity:
https://masterchain.info/Address.html?addr=1BKpa19m5Xy9SvSzC5djPWtCfbuynSDwmb&currency=TMSC

MSC on mastercoin-tools tips jar address:
https://masterchain.info/Address.html?addr=182osbPxCo88oaSX4ReJwUr9uAcchmJVaL&currency=MSC


### Known forks ###

https://github.com/mastercoin-MSC/omniwallet
There you could also find better detailed documentation for API (including
wallet), json format, etc.


### Parsing usage examples ###
```
$ python msc_parse.py -h
Usage: msc_parse.py [options]

Options:
  -h, --help            show this help message and exit
  -d, --debug           turn debug mode on
  -t SINGLE_TX, --transaction=SINGLE_TX
                        hash of a specific tx to parse
  -s STARTING_BLOCK_HEIGHT, --start-block=STARTING_BLOCK_HEIGHT
                        start the parsing at a specific block height (default
                        is last)
  -a, --archive-parsed-data
                        archive the parsed data of tx addr and general for
                        others to download
```

```
$ python msc_parse.py -t aa64fd6088532156a37670e6cbd175c74bb101f1406517613a1a0ae6bc02fb02
[I] main: {'currency_type_str': 'Mastercoin', 'transaction_type_str': 'Simple send', 'currencyId': '00000001', 'transaction_method_str': 'multisig_simple', 'recipientAddress': '17RVTF3vJzsuaGh7a94DFkg4msJ7FcBYgX', 'padding': '000000', 'amount': '0000000002faf080', 'changeAddress': '182osbPxCo88oaSX4ReJwUr9uAcchmJVaL', 'formatted_amount': '0.50000000', 'baseCoin': '00', 'dataSequenceNum': '45', 'transactionType': '00000000'}
$
$ python msc_parse.py -t 298a6af50089184f7b434c700f83f390d5dfdd5dac10b39b95f99036a5c66df7
[I] main: {'currency_type_str': 'Test Mastercoin', 'transaction_type_str': 'Simple send', 'currencyId': '00000002', 'transaction_method_str': 'multisig_simple', 'recipientAddress': '17RVTF3vJzsuaGh7a94DFkg4msJ7FcBYgX', 'padding': '000000', 'amount': '0000000000000003', 'changeAddress': '182osbPxCo88oaSX4ReJwUr9uAcchmJVaL', 'formatted_amount': '0.00000003', 'baseCoin': '00', 'dataSequenceNum': '45', 'transactionType': '00000000'}
$
```

```
$ python msc_validate.py -h
Usage: msc_validate.py [options]

Options:
  -h, --help   show this help message and exit
  -d, --debug  turn debug mode on
```

enjoy!

BTC/Mastercoins Tips Jar:
* https://masterchain.info/Address.html?addr=182osbPxCo88oaSX4ReJwUr9uAcchmJVaL&currency=MSC



