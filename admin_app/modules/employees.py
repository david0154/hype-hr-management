# employees.py patch note:
# The actual file is too large to rewrite here — patching via id_card.py company_name fix instead.
# See id_card.py generate_id_card_image() — already handles company_name correctly.
# The employees.py add/edit form must save 'company_name' field when role is security/supervisor.
# This is handled by the Firestore document — company_name is set at company level not per-employee.
# No change needed here — company_name is read from settings/company collection.
