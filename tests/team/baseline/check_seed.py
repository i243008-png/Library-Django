# Baseline state check. Run inside the web container's Django shell:
#   docker compose -f docker-compose-dev.yml exec -T web python manage.py shell < tests/team/baseline/check_seed.py
# Prints one line per check and exits non-zero if the database is not in the
# documented baseline state (see BASELINE.md, "Expected baseline state").
import sys

from authentication.models import CustomUser
from author.models import Author
from book.models import Book
from order.models import Order, Reservation

failures = []


def check(label, actual, expected):
    ok = actual == expected
    print(
        ("PASS  " if ok else "FAIL  ") + f"{label}: expected {expected}, got {actual}"
    )
    if not ok:
        failures.append(label)


check("users", CustomUser.objects.count(), 4)
check("authors", Author.objects.count(), 8)
check("books", Book.objects.count(), 9)
check("loans (orders)", Order.objects.count(), 3)
check("open loans", Order.objects.filter(end_at__isnull=True).count(), 2)
check("reservations", Reservation.objects.count(), 0)

# Shared record: available copies = count - open loans - active reservations.
expected_available = {
    "Kobzar": 4,  # 5 copies, 1 open loan (reader@library.com)
    "1984": 7,  # 8 copies, 1 open loan (alice@library.com)
    "Clean Code: A Handbook of Agile Software Craftsmanship": 3,  # loan already returned
    "Animal Farm": 7,
}
available = {b.name: b.available_count for b in Book.objects.with_availability()}
for name, value in expected_available.items():
    check(f"available copies of {name!r}", available.get(name), value)

if failures:
    print(f"\nBASELINE NOT CLEAN: {len(failures)} check(s) failed")
    sys.exit(1)
print("\nBASELINE CLEAN")
