def getEstimatedAfterFees(amount):
    #Allow up to 0.07% entry fee
    return amount - (amount * 0.007)

def get_change(current, previous):
    if current == previous:
        return 100.0
    try:
        return (abs(current - previous) / previous) * 100.0
    except ZeroDivisionError:
        return 0