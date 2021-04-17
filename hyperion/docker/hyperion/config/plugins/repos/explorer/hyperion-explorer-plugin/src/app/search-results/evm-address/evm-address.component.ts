import {Component, OnDestroy, OnInit} from '@angular/core';
import {ActivatedRoute} from '@angular/router';
import {faCircle} from '@fortawesome/free-solid-svg-icons/faCircle';
import {faHistory} from '@fortawesome/free-solid-svg-icons/faHistory';
import {faUserCircle} from '@fortawesome/free-solid-svg-icons/faUserCircle';
import {Subscription} from 'rxjs';
import {EvmService} from '../../services/evm.service';
import {PageEvent} from '@angular/material/paginator';
import {faClock} from '@fortawesome/free-solid-svg-icons/faClock';
import {AccountService} from '../../services/account.service';

@Component({
  selector: 'app-evm-address',
  templateUrl: './evm-address.component.html',
  styleUrls: ['./evm-address.component.css']
})
export class EvmAddressComponent implements OnInit, OnDestroy {

  address = '';
  subs: Subscription[];
  faUserCircle = faUserCircle;
  nativeBalance = 0;
  faCircle = faCircle;
  faHistory = faHistory;
  faClock = faClock;

  columnsToDisplay: string[] = [
    'hash',
    'block',
    'fromAddr',
    'toAddr',
    'nativeValue'
  ];

  constructor(
    private activatedRoute: ActivatedRoute,
    public accountService: AccountService,
    public evm: EvmService
  ) {
    this.subs = [];
  }

  ngOnInit(): void {
    this.subs.push(this.activatedRoute.params.subscribe(async (routeParams) => {
      this.address = routeParams.address;
      this.nativeBalance = await this.evm.getBalance(this.address);
      await this.evm.loadTransactions(this.address);
      await this.accountService.checkIrreversibility();
    }));
  }

  ngOnDestroy(): void {
    this.subs.forEach(s => s.unsubscribe());
  }

  formatDate(date: string): string {
    return new Date(date).toLocaleString();
  }

  changePage(event: PageEvent): void {

    // disable streaming if enabled
    if (this.evm.streamClientStatus) {
      this.evm.toggleStreaming();
    }

    const maxPages = Math.floor(event.length / event.pageSize);
    console.log(event);
    console.log(`${event.pageIndex} / ${maxPages}`);
    try {
      if (event.pageIndex === maxPages - 1) {
        this.evm.loadMoreTransactions(this.address).catch(console.log);
      }
    } catch (e) {
      console.log(e);
    }
  }

}
