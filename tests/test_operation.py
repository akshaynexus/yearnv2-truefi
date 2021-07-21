import pytest
from brownie import Wei, accounts, chain
from common_utils import getEstimatedAfterFees, get_change

# reference code taken from yHegic repo and stecrv strat
# https://github.com/Macarse/yhegic
# https://github.com/Grandthrax/yearnv2_steth_crv_strat


@pytest.mark.require_network("mainnet-fork")
def test_operation(
    currency,
    strategy,
    chain,
    vault,
    whale,
    gov,
    bob,
    alice,
    strategist,
    guardian,
):
    # Amount configs
    test_budget = 888000 * 1e6
    approve_amount = 1000000 * 1e6
    deposit_limit = 889000 * 1e6
    bob_deposit = 100000 * 1e6
    alice_deposit = 788000 * 1e6

    total_deposit = bob_deposit + alice_deposit
    #Get atleast enough to cover exit costs
    targetAssets = total_deposit + (total_deposit * (0.16 / 100))
    currency.approve(whale, approve_amount, {"from": whale})
    currency.transferFrom(whale, gov, test_budget, {"from": whale})

    vault.setDepositLimit(deposit_limit)

    # 100% of the vault's depositLimit
    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 0, {"from": gov})

    currency.approve(gov, approve_amount, {"from": gov})
    currency.transferFrom(gov, bob, bob_deposit, {"from": gov})
    currency.transferFrom(gov, alice, alice_deposit, {"from": gov})
    currency.approve(vault, approve_amount, {"from": bob})
    currency.approve(vault, approve_amount, {"from": alice})

    vault.deposit(bob_deposit, {"from": bob})
    vault.deposit(alice_deposit, {"from": alice})
    blockedMined = 0
    while strategy.estimatedTotalAssets() < targetAssets:
        chain.sleep(50000)
        strategy.harvest({"from": gov})
        blockedMined = blockedMined + 1
        print(f"Mined blocks :{blockedMined}")
        print(f"Loss Remaing to cover {get_change(strategy.estimatedTotalAssets(), targetAssets)}")
    #sleep for 6 hours
    chain.sleep(6*60*60)
    # # Sleep and harvest 5 times,approx for 24 hours
    # sleepAndHarvest(5, strategy, gov)
    # We should have made profit or stayed stagnant (This happens when there is no rewards in 1INCH rewards)
    assert vault.pricePerShare() / 1e6 >= 1
    # Log estimated APR
    growthInShares = vault.pricePerShare() - 1e6
    growthInPercent = (growthInShares / 1e6) * 100
    growthYearly = growthInPercent * 365
    print(f"Yearly APR :{growthYearly}%")
    # Withdraws should not fail
    vault.withdraw(alice_deposit, {"from": alice})
    vault.withdraw(bob_deposit, {"from": bob})

    # Depositors after withdraw should have a profit or gotten the original amount
    assert currency.balanceOf(alice) >= alice_deposit
    assert currency.balanceOf(bob) >= bob_deposit

    # Make sure it isnt less than 1 after depositors withdrew
    assert vault.pricePerShare() / 1e6 >= 1


def sleepAndHarvest(times, strat, gov):
    for i in range(times):
        debugStratData(strat, "Before harvest" + str(i))
        # for j in range(139):
        #     chain.sleep(13)
        #     chain.mine(1)
        strat.harvest({"from": gov})
        debugStratData(strat, "After harvest" + str(i))


# Used to debug strategy balance data
def debugStratData(strategy, msg):
    print(msg)
    print("Total assets " + str(strategy.estimatedTotalAssets()))
    print("USDC Balance " + str(strategy.balanceOfWant()))
    print("Stake balance " + str(strategy.balanceOfStake()))
    print("Pending reward " + str(strategy.pendingReward()))
