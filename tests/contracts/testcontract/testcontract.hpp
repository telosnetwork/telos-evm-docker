#include <eosio/eosio.hpp>

#define PRINT_HEADER "VAR3"

using namespace eosio;

class [[eosio::contract]] testcontract : public contract {
    public:
        using contract::contract;

        [[eosio::action]]
        void print(std::string msg, bool cancel);
}
