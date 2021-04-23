import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';
import {HomeComponent} from './home/home.component';
import {SearchResultsComponent} from './search-results/search-results.component';
import {AccountComponent} from './search-results/account/account.component';
import {TransactionComponent} from './search-results/transaction/transaction.component';
import {BlockComponent} from './search-results/block/block.component';
import {KeyComponent} from './search-results/key/key.component';
import {EvmAddressComponent} from './search-results/evm-address/evm-address.component';
import {EvmBlockComponent} from './search-results/evm-block/evm-block.component';
import {EvmTransactionComponent} from './search-results/evm-transaction/evm-transaction.component';

const routes: Routes = [
  {
    path: '', component: HomeComponent
  },
  {
    path: '',
    component: SearchResultsComponent,
    children: [
      {path: 'account/:account_name', component: AccountComponent},
      {path: 'transaction/:transaction_id', component: TransactionComponent},
      {path: 'block/:block_num', component: BlockComponent},
      {path: 'key/:key', component: KeyComponent},
      {path: 'evm/address/:address', component: EvmAddressComponent},
      {path: 'evm/transaction/:hash', component: EvmTransactionComponent},
      {path: 'evm/block/:block_num', component: EvmBlockComponent}
    ],
  },
  {
    path: '**', component: HomeComponent
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes, {
    scrollPositionRestoration: 'enabled'
  })],
  exports: [RouterModule]
})
export class AppRoutingModule {
}
