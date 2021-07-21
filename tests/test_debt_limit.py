import pytest
import brownie
from brownie import Wei
from common_utils import getEstimatedAfterFees, get_change

deposit_amount = 40000 * 1e6
second_deposit_amount = 160000 * 1e6
final_amount = 80000 * 1e6


def test_increasing_debt_limit(gov, whale, currency, vault, strategy):
    currency.approve(vault, 2 ** 256 - 1, {"from": gov})
    # Fund gov with enough tokens
    currency.approve(whale, deposit_amount + second_deposit_amount, {"from": whale})
    currency.transferFrom(
        whale, gov, deposit_amount + second_deposit_amount, {"from": whale}
    )

    # Start with a 40k deposit limit
    vault.setDepositLimit(deposit_amount, {"from": gov})
    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 0, {"from": gov})

    # deposit 40k in total to test
    vault.deposit(deposit_amount, {"from": gov})
    print(strategy.pricePerLendToken())
    strategy.harvest()
    assert strategy.estimatedTotalAssets() >= getEstimatedAfterFees(deposit_amount)

    # User shouldn't be able to deposit 40k more
    with brownie.reverts():
        vault.deposit(deposit_amount, {"from": gov})

    vault.setDepositLimit(second_deposit_amount, {"from": gov})
    vault.deposit(deposit_amount, {"from": gov})
    strategy.harvest()
    assert (
        strategy.estimatedTotalAssets() >= getEstimatedAfterFees(final_amount)
    )  # Check that assets is >= 80k


def test_decrease_debt_limit(gov, whale, currency, vault, strategy, chain):
    currency.approve(vault, 2 ** 256 - 1, {"from": gov})
    # Fund gov with enough tokens
    currency.approve(whale, deposit_amount + second_deposit_amount, {"from": whale})
    currency.transferFrom(
        whale, gov, deposit_amount + second_deposit_amount, {"from": whale}
    )

    vault.setDepositLimit(second_deposit_amount, {"from": gov})
    # Start with 100% of the debt
    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 0, {"from": gov})
    print(vault.availableDepositLimit())
    # Depositing 80k
    vault.deposit(second_deposit_amount, {"from": gov})
    strategy.harvest()

    print(f" Deposted : {second_deposit_amount / 1e6}")
    print(f" Assets : {strategy.estimatedTotalAssets() / 1e6}")
    print(f" Difference : {(second_deposit_amount -  strategy.estimatedTotalAssets())/ 1e6}")
    print(f" Difference in %: {get_change(strategy.estimatedTotalAssets(), second_deposit_amount)}")

    assert strategy.estimatedTotalAssets() >= getEstimatedAfterFees(second_deposit_amount)

    assetsBeforeDec = strategy.estimatedTotalAssets()
    # let's lower the debtLimit so the strategy adjust it's position
    vault.updateStrategyDebtRatio(strategy, 5_000)
    strategy.harvest()
    strategy.harvest()

    assert strategy.estimatedTotalAssets() >= getEstimatedAfterFees(assetsBeforeDec / 2)

    #Wait for 6 hours,harvest,then wait for another 6 hours so that we dont have any debt outstanding
    chain.sleep(21600)
    chain.mine(1)
    strategy.harvest()
    chain.sleep(21600)
    chain.mine(1)
    strategy.harvest()
    chain.sleep(21600)
    chain.mine(1)

    assert vault.debtOutstanding(strategy) == 0
