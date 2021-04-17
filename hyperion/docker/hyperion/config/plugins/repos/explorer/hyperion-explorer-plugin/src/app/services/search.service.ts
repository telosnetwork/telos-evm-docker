import {Injectable} from '@angular/core';
import {HttpClient} from '@angular/common/http';
import {environment} from '../../environments/environment';
import {GetTableByScopeResponse, TableData} from '../interfaces';
import {Router} from '@angular/router';

@Injectable({
  providedIn: 'root'
})
export class SearchService {
  searchAccountUrl: string;

  constructor(private httpClient: HttpClient, private router: Router) {
    this.searchAccountUrl = environment.eosioNodeUrl + '/v1/chain/get_table_by_scope';
  }

  async filterAccountNames(value: string): Promise<any> {

    if ((value && value.length > 12) || !value) {
      return [];
    }

    try {
      const sValue = value.toLowerCase();

      const requestBody = {
        code: environment.systemContract,
        table: environment.userResourcesTable,
        lower_bound: sValue,
        limit: 5
      };

      const response = await this.httpClient.post(this.searchAccountUrl, requestBody).toPromise() as GetTableByScopeResponse;

      if (response.rows) {
        return response.rows.filter((tableData: TableData) => {
          return tableData.scope.startsWith(sValue);
        }).map((tableData: TableData) => {
          return tableData.scope;
        });
      }
    } catch (error) {
      console.log(error);
      return [];
    }
  }


  async submitSearch(searchText: any, filteredAccounts: string[]): Promise<boolean> {

    const sValue = searchText.toLowerCase();

    // account direct
    if (filteredAccounts.length > 0) {
      await this.router.navigate(['/account', sValue]);
      return true;
    }

    // tx id
    if (sValue.length === 64) {
      await this.router.navigate(['/transaction', sValue]);
      return true;
    }

    // account search
    if (sValue.length > 0 && sValue.length <= 12 && isNaN(sValue)) {
      await this.router.navigate(['/account', sValue]);
      return true;
    }

    // public key
    if (searchText.startsWith('PUB_K1_') || searchText.startsWith('EOS')) {
      await this.router.navigate(['/key', searchText]);
      return true;
    }

    // block number
    const blockNum = searchText.replace(/[,.]/g, '');
    if (parseInt(blockNum, 10) > 0) {
      await this.router.navigate(['/block', blockNum]);
      return true;
    }

    // match EVM 0x prefix
    if (searchText.startsWith('0x')) {
      let route;
      switch (searchText.length) {
        case 42: {
          route = '/evm/address';
          break;
        }
        case 66: {
          route = '/evm/transaction';
          break;
        }
        default: {
          if (searchText.length < 16) {
            // probably a block number in hex
            route = '/evm/block';
          } else {
            console.log('Ox prefixed string with length:', searchText.length);
          }
        }
      }
      if (route) {
        await this.router.navigate([route, searchText]);
        return true;
      }
    }

    console.log('NO PATTERN MATCHED!');
    return false;
  }
}
