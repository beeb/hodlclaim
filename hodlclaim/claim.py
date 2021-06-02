"""
Claim bot for HODL token.

web3.eth.accounts.privateKeyToAccount(privateKey)
"""
import logging
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from eth_account.signers.local import LocalAccount
from loguru import logger
from web3 import Web3
from web3.types import TxParams, Wei


class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


logger.remove()
logger.add(
    sys.stderr,
    format="<d>{time:YYYY-MM-DD HH:mm:ss}</> <lvl>{level: ^8}</>|<lvl><n>{message}</n></lvl>",
    level='INFO',
    backtrace=False,
    diagnose=False,
    colorize=True,
)
logging.getLogger("apscheduler.executors.default").setLevel("WARNING")
logging.basicConfig(handlers=[InterceptHandler()], level=0)

w3_provider = Web3.HTTPProvider(endpoint_uri='https://bsc-dataseed.binance.org:443')
w3 = Web3(provider=w3_provider)

account: LocalAccount

hodl_address = Web3.toChecksumAddress('0x0E3EAF83Ea93Abe756690C62c72284943b96a6Bc')
hodl_abi = Path('hodlclaim/hodl.abi').open('r').read()
hodl_contract = w3.eth.contract(address=hodl_address, abi=hodl_abi)

scheduler = BlockingScheduler()


def make_transaction() -> None:
    logger.info('Now trying to claim the reward.')
    func = hodl_contract.functions.claimBNBReward()
    try:
        gas_estimate = Web3.toWei(func.estimateGas({'from': account.address, 'value': Wei(0)}) * 1.2, unit='wei')
    except Exception:
        logger.error('Failed to estimate gas')
        return
    nonce = w3.eth.get_transaction_count(account.address)
    params: TxParams = {
        'from': account.address,
        'value': Wei(0),
        'gas': gas_estimate,
        'nonce': nonce,
        'gasPrice': Web3.toWei(w3.eth.gas_price + 1, unit='wei'),
    }
    transaction = func.buildTransaction(params)
    signed_tx = account.sign_transaction(transaction)
    tx = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx)
    txhash = Web3.toHex(primitive=receipt["transactionHash"])
    if receipt['status'] == 0:  # fail
        logger.error(f'Claim transaction failed at tx {txhash}')
        return
    amount_out = Decimal(0)
    logs = hodl_contract.events.ClaimBNBSuccessfully().processReceipt(receipt)
    for log in logs:
        amount_out = Web3.fromWei(log['args']['ethReceived'], unit='ether')
    logger.info(f'Claim transaction succeeded at tx {txhash}')
    logger.success(f'Claimed {amount_out:.3g} BNB')


def claim() -> None:
    reward = Web3.fromWei(hodl_contract.functions.calculateBNBReward(account.address).call(), unit='ether')
    logger.info(f'Next claim is for {reward:.3g} BNB')
    next_claim = datetime.fromtimestamp(hodl_contract.functions.nextAvailableClaimDate(account.address).call())
    timediff = next_claim - datetime.now()
    if timediff.total_seconds() < 0:
        logger.info('Claim will be performed now')
        run_date = datetime.now()
    else:
        logger.info(f'Next claim available at {next_claim} so in {timediff.total_seconds() / 3600:.1f} hours')
        logger.info('Now waiting for that time to come...')
        run_date = next_claim + timedelta(seconds=1)
    scheduler.add_job(make_transaction, trigger='date', run_date=run_date)
    scheduler.start()


def main() -> None:
    global account
    pk = os.environ.get('WALLET_PK')
    if pk is None:
        logger.error('No WALLET_PK environment variable.')
        return
    account = w3.eth.account.from_key(pk)
    logger.info(f'Using wallet address {account.address}')
    try:
        while True:
            claim()
    except KeyboardInterrupt:
        logger.warning('User cancelled')


if __name__ == '__main__':
    main()
