import {Injectable} from '@angular/core';
import {HttpClient} from '@angular/common/http';
import {environment} from '../../environments/environment';
import {MatTableDataSource} from '@angular/material/table';
import {PaginationService} from './pagination.service';

@Injectable({
  providedIn: 'root'
})
export class EvmService {
  loaded = true;

  jsonRpcApi = environment.eosioNodeUrl + '/evm';
  streamClientStatus = false;
  libNum = 0;
  streamClientLoaded = true;
  transactions = [];
  addressTransactions: MatTableDataSource<any[]>;
  blockTransactions: MatTableDataSource<any[]>;
  private server: string;

  constructor(private http: HttpClient, private pagService: PaginationService) {
    this.getServerUrl();
    this.addressTransactions = new MatTableDataSource([]);
    this.blockTransactions = new MatTableDataSource([]);
  }

  async callRpcMethod(method: string, params: any[]): Promise<any> {
    try {
      const response = await this.http.post(this.jsonRpcApi, {
        jsonrpc: '2.0',
        id: Date.now(),
        method,
        params
      }).toPromise() as any;
      return response.result;
    } catch (e) {
      console.log(e);
      return null;
    }
  }

  async getBalance(address: string): Promise<number> {
    const getBalResult = await this.callRpcMethod('eth_getBalanceHuman', [address]);
    if (getBalResult) {
      return Number(getBalResult);
    } else {
      return 0;
    }
  }

  async getTransactionReceipt(hash: string): Promise<any> {
    return await this.callRpcMethod('eth_getTransactionReceipt', [hash.toLowerCase()]);
  }

  async getTransactionByHash(hash: string): Promise<any> {
    return await this.callRpcMethod('eth_getTransactionByHash', [hash.toLowerCase()]);
  }

  async getBlockByNumber(blockNumber: string): Promise<any> {
    return await this.callRpcMethod('eth_getBlockByNumber', [blockNumber.toLowerCase()]);
  }

  async getBlockByHash(hash: string): Promise<any> {
    return await this.callRpcMethod('eth_getBlockByHash', [hash.toLowerCase()]);
  }

  getServerUrl(): void {
    let server;
    if (environment.production) {
      server = window.location.origin;
    } else {
      server = environment.hyperionApiUrl;
    }
    this.server = server;
  }

  toggleStreaming(): void {
    this.streamClientStatus = !this.streamClientStatus;
  }

  async loadTransactions(address: string): Promise<void> {
    const resp = await this.http.get(this.server + '/evm_explorer/get_transactions?address=' + address).toPromise() as any;
    this.processTransactions(resp.transactions);
    if (resp.total) {
      this.pagService.totalItems = resp.total;
    }
  }

  async loadBlock(blockNumber: any): Promise<any> {
    const blockData = await this.getBlockByNumber('0x' + Number(blockNumber).toString(16));
    this.blockTransactions.data = await this.getTransactions(blockData.transactions);
  }

  async loadMoreTransactions(address: string): Promise<void> {
    console.log(address);
  }

  private processTransactions(transactions: any[]): void {
    this.transactions = [];
    this.transactions = transactions;
    for (const trx of this.transactions) {
      if (trx.receipt) {
        trx.evm_block = trx.receipt.block;
        trx.evm_hash = trx.receipt.hash;
      }
    }
    this.addressTransactions.data = this.transactions;
  }

  async getTransactions(hashes: string[]): Promise<any> {
    try {
      return await this.http.post(this.server + '/evm_explorer/get_transactions', {
        tx_hashes: hashes
      }).toPromise() as any;
    } catch (e) {
      console.log(e);
      return [];
    }
  }
}
