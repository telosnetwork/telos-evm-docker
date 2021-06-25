import {Component, OnDestroy, OnInit} from '@angular/core';
import {EvmService} from '../../services/evm.service';
import {faExchangeAlt} from '@fortawesome/free-solid-svg-icons/faExchangeAlt';
import {faSadTear} from '@fortawesome/free-solid-svg-icons/faSadTear';
import {faCircle} from '@fortawesome/free-solid-svg-icons/faCircle';
import {faHourglassStart} from '@fortawesome/free-solid-svg-icons/faHourglassStart';
import {faLock} from '@fortawesome/free-solid-svg-icons/faLock';
import {Subscription} from 'rxjs';
import {ActivatedRoute} from '@angular/router';
import {BigInteger} from '@angular/compiler/src/i18n/big_integer';
import {AccountService} from '../../services/account.service';

@Component({
  selector: 'app-evm-transaction',
  templateUrl: './evm-transaction.component.html',
  styleUrls: ['./evm-transaction.component.css']
})
export class EvmTransactionComponent implements OnInit, OnDestroy {
  faSadTear = faSadTear;
  faExchange = faExchangeAlt;
  faCircle = faCircle;
  faLock = faLock;
  faHourglass = faHourglassStart;

  txHash = '';

  txData: any = {
    hash: '0xaef244314c42bdc2d62bfaa82880049dafa958ae4e4ce8a0ae8b94598ff1549a',
    block_num: 0,
    block: 0,
    timestamp: '',
    from: '',
    to: '',
    value: 0,
    gas_price: '',
    gas_used: '',
    nonce: 0,
    input_data: '',
    logs: '',
    errors: '',
    status: ''
  };

  subs: Subscription[];

  constructor(
    private activatedRoute: ActivatedRoute,
    public accountService: AccountService,
    public evm: EvmService
  ) {
    this.subs = [];
  }

  ngOnInit(): void {
    this.subs.push(this.activatedRoute.params.subscribe(async (routeParams) => {
      this.txHash = routeParams.hash;
      const txData = await this.evm.getTransactionByHash(this.txHash);
      this.txData.block = parseInt(txData.blockNumber, 16);
      this.txData.from = txData.from;
      this.txData.timestamp = txData.timestamp || Date.now();
      this.txData.to = txData.to;
      this.txData.value = parseInt(txData.value, 16);
      this.txData.nonce = parseInt(txData.nonce, 16);
      this.txData.gas_price = parseInt(txData.gasPrice, 16);
      this.txData.gas_used = parseInt(txData.gas, 16);
      this.txData.input_data = txData.input;
      this.txData.logs = txData.logs;
      this.txData.errors = txData.errors;
      this.txData.status = txData.status;
      await this.accountService.checkIrreversibility();
    }));
  }

  ngOnDestroy(): void {
    this.subs.forEach(s => s.unsubscribe());
  }

  formatDate(date: string): string {
    return new Date(date).toLocaleString();
  }

}
