#include "testcontract.hpp"

void testcontract::print(std::string msg, bool cancel) {
    eosio::print(PRINT_HEADER, ": ", msg);
    check(!cancel, "action cancelled");
}
