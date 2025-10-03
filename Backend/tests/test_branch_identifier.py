from src.domain.utils.branch_identifier import BranchIdentifier, validate_table


def test_branch_identifier_from_payload_number():
    identifier = BranchIdentifier.from_payload({"number": 42, "raw_text": "Sucursal 42"})
    assert identifier is not None
    assert identifier.number == 42
    condition, params = identifier.build_condition()
    assert condition == "sucursal_numero = $1"
    assert params == [42]


def test_branch_identifier_from_payload_name():
    identifier = BranchIdentifier.from_payload({"name": "Villa Crespo"})
    assert identifier is not None
    assert identifier.name == "Villa Crespo"
    condition, params = identifier.build_condition()
    assert condition == "sucursal_nombre ILIKE $1"
    assert params == ["%Villa Crespo%"]


def test_validate_table_normalizes_name():
    assert validate_table("PUBLIC.SALDOS_SUCURSAL") == "public.saldos_sucursal"
    assert validate_table("desconocida") == "public.saldos_sucursal"

