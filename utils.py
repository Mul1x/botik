def format_amount(amount: float) -> str:
    return f"{amount:,.2f}".replace(",", " ")

def get_rating_stars(rating: float) -> str:
    return "★" * int(rating) + "☆" * (5 - int(rating))
