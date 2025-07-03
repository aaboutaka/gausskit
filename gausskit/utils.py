def parse_swap_pairs(swap_string):
    if not swap_string:
        return []
    pairs = [pair.strip() for pair in swap_string.split(',') if pair.strip()]
    return [pair.split() for pair in pairs]


