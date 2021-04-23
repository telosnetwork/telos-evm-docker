import {Component, OnInit} from '@angular/core';
import {ActivatedRoute} from '@angular/router';
import {AccountService} from '../../services/account.service';
import {ChainService} from '../../services/chain.service';
import {Title} from '@angular/platform-browser';
import {faSpinner} from '@fortawesome/free-solid-svg-icons/faSpinner';
import {faSadTear} from '@fortawesome/free-solid-svg-icons/faSadTear';
import {faKey} from '@fortawesome/free-solid-svg-icons/faKey';
import {faCircle} from '@fortawesome/free-solid-svg-icons/faCircle';

interface KeyResponse {
  account_names: string[];
  permissions: any[];
}

@Component({
  selector: 'app-key',
  templateUrl: './key.component.html',
  styleUrls: ['./key.component.css']
})
export class KeyComponent implements OnInit {
  key: KeyResponse = {
    account_names: null,
    permissions: null
  };
  pubKey: string;
  faCircle = faCircle;
  faKey = faKey;
  faSadTear = faSadTear;
  faSpinner = faSpinner;

  constructor(private activatedRoute: ActivatedRoute,
              public accountService: AccountService,
              public chainData: ChainService,
              private title: Title) {
  }

  ngOnInit(): void {
    this.activatedRoute.params.subscribe(async (routeParams) => {
      this.pubKey = routeParams.key;
      this.key = await this.accountService.loadPubKey(routeParams.key) as KeyResponse;

      if (!this.chainData.chainInfoData.chain_name) {
        this.title.setTitle(`🔑 ${routeParams.key.slice(0, 12)} • Hyperion Explorer`);
      } else {
        this.title.setTitle(`🔑 ${routeParams.key.slice(0, 12)} • ${this.chainData.chainInfoData.chain_name} Hyperion Explorer`);
      }

    });
  }

}
