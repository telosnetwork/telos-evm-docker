import {Injectable} from '@angular/core';
import {HttpClient} from '@angular/common/http';
import {environment} from '../../environments/environment';
import {MatTableDataSource} from '@angular/material/table';
import {PaginationService} from './pagination.service';

const REVERT_FUNCTION_SELECTOR = '0x08c379a0';
const REVERT_PANIC_SELECTOR = '0x4e487b71';
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

  async getBlockByNumber(blockNumber: string, full: boolean): Promise<any> {
    return await this.callRpcMethod('eth_getBlockByNumber', [blockNumber.toLowerCase(), full]);
  }

  async getBlockByHash(hash: string, full: boolean): Promise<any> {
    return await this.callRpcMethod('eth_getBlockByHash', [hash.toLowerCase(), full]);
  }

  async traceTransaction(hash: string): Promise<any> {
    return await this.callRpcMethod('trace_transaction', [hash.toLowerCase()]);
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
    const blockData = await this.getBlockByNumber('0x' + Number(blockNumber).toString(16), true);
    blockData.transactions.forEach((trx) => {
      trx.val_formatted = `${(parseInt(trx.value, 16) / 1000000000000000000 ).toFixed(4)} TLOS`
    })
    this.blockTransactions.data = blockData.transactions;
  }

  async loadMoreTransactions(address: string): Promise<void> {
    console.log(address);
  }

  private processTransactions(transactions: any[]): void {
    this.transactions = [];
    this.transactions = transactions;
    for (const trx of this.transactions) {
      trx.evm_block = trx.block;
      trx.evm_hash = trx.hash;
      trx.val_formatted = `${parseInt(trx.value_d).toFixed(4)} TLOS`
    }
    this.addressTransactions.data = this.transactions;
  }

  getErrorFromOutput(output: string): string {
    if (!output) return '';
    if (output.startsWith(REVERT_FUNCTION_SELECTOR)) {
      return this.parseRevertReason(output);
    }

    if (output.startsWith(REVERT_PANIC_SELECTOR)) {
      return this.parsePanicReason(output);
    }

    return '';
  }

  parseRevertReason(revertOutput: string): string {
    if (!revertOutput || revertOutput.length < 138) {
      return '';
    }
  
    let reason = '';
    let trimmedOutput = revertOutput.substr(138);
    for (let i = 0; i < trimmedOutput.length; i += 2) {
      reason += String.fromCharCode(parseInt(trimmedOutput.substr(i, 2), 16));
    }
    return reason;
  }
  
  parsePanicReason(revertOutput: string): string {
    let trimmedOutput = revertOutput.slice(-2)
    let reason;
  
    switch(trimmedOutput) {
      case "01":
        reason = "If you call assert with an argument that evaluates to false.";
        break;
      case "11":
        reason = "If an arithmetic operation results in underflow or overflow outside of an unchecked { ... } block.";
        break;
      case "12":
        reason = "If you divide or modulo by zero (e.g. 5 / 0 or 23 % 0).";
        break;
      case "21":
        reason = "If you convert a value that is too big or negative into an enum type.";
        break;
      case "31":
        reason = "If you call .pop() on an empty array.";
        break;
      case "32":
        reason = "If you access an array, bytesN or an array slice at an out-of-bounds or negative index (i.e. x[i] where i >= x.length or i < 0).";
        break;
      case "41":
        reason = "If you allocate too much memory or create an array that is too large.";
        break;	
      case "51":
        reason = "If you call a zero-initialized variable of internal function type.";
        break;		
      default:
        reason = "Default panic message";
    }	
    return reason;
  }
}
