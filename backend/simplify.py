from circuit_safety import build_circuit
from qiskit import QuantumCircuit
from equivalence import circuits_equivalent

SELF_INVERSE_GATES = {"h", "x", "y", "z", "cx"}
GATE_ORDER = {"h": 2, "x": 2, "y": 2, "z": 2, "s": 4}
GATE_POWER_REPLACEMENTS = {
    ("s", 2): "z",
    ("t", 2): "s",
}
ROTATION_GATES = {"rx", "ry", "rz"}
PAULI_PRODUCTS = {
    frozenset({"x", "y"}): "z",
    frozenset({"y", "z"}): "x",
    frozenset({"z", "x"}): "y",
}


def circuit_to_gate_list(qc):
    gate_list = []
    for instruction in qc.data:
        name = instruction.operation.name
        qubit_indices = tuple(qc.find_bit(q).index for q in instruction.qubits)
        params = tuple(float(p) for p in instruction.operation.params)
        gate_list.append((name, qubit_indices, params))
    return gate_list


def gate_list_to_circuit(gate_list, num_qubits):
    # Validated: gate lists can originate from requests or LLM output.
    return build_circuit(gate_list, num_qubits)


def find_adjacent_cancellation(gate_list):
    for i in range(len(gate_list) - 1):
        name_a, qubits_a, params_a = gate_list[i]
        name_b, qubits_b, params_b = gate_list[i + 1]

        if (
            name_a == name_b
            and qubits_a == qubits_b
            and params_a == params_b
            and name_a in SELF_INVERSE_GATES
        ):
            return i

    return None


def gates_commute(gate_a, gate_b):
    _, qubits_a, _ = gate_a
    _, qubits_b, _ = gate_b
    return set(qubits_a).isdisjoint(set(qubits_b))


def find_commuting_cancellation(gate_list):
    for i in range(len(gate_list)):
        name_i, qubits_i, params_i = gate_list[i]

        if name_i not in SELF_INVERSE_GATES:
            continue

        for j in range(i + 1, len(gate_list)):
            name_j, qubits_j, params_j = gate_list[j]

            if name_i == name_j and qubits_i == qubits_j and params_i == params_j:
                return (i, j)

            if not gates_commute(gate_list[i], gate_list[j]):
                break

    return None


def find_power_replacement(gate_list):
    for i in range(len(gate_list) - 1):
        name_a, qubits_a, params_a = gate_list[i]
        name_b, qubits_b, params_b = gate_list[i + 1]

        if name_a == name_b and qubits_a == qubits_b and params_a == params_b:
            key = (name_a, 2)
            if key in GATE_POWER_REPLACEMENTS:
                return (i, GATE_POWER_REPLACEMENTS[key])

    return None


def find_pauli_product(gate_list):
    for i in range(len(gate_list) - 1):
        name_a, qubits_a, params_a = gate_list[i]
        name_b, qubits_b, params_b = gate_list[i + 1]

        if qubits_a != qubits_b or name_a == name_b:
            continue

        key = frozenset({name_a, name_b})
        if key in PAULI_PRODUCTS:
            return (i, PAULI_PRODUCTS[key])

    return None


def find_full_order_cancellation(gate_list):
    for i in range(len(gate_list)):
        name, qubits, params = gate_list[i]

        if name not in GATE_ORDER:
            continue

        order = GATE_ORDER[name]
        run_length = 1

        for j in range(i + 1, len(gate_list)):
            next_name, next_qubits, next_params = gate_list[j]
            if next_name == name and next_qubits == qubits and next_params == params:
                run_length += 1
                if run_length == order:
                    return (i, j + 1)
            else:
                break

    return None


def find_rotation_composition(gate_list):
    for i in range(len(gate_list) - 1):
        name_a, qubits_a, params_a = gate_list[i]
        name_b, qubits_b, params_b = gate_list[i + 1]

        if (
            name_a == name_b
            and qubits_a == qubits_b
            and name_a in ROTATION_GATES
        ):
            return i

    return None


def simplify_once(qc):
    """
    Try to find and verify ONE simplification. Returns a 4-tuple:
    (new_circuit, rule_name, consumed_indices, replacement_count)
    if found, else (None, None, None, None).

    consumed_indices: positions in THIS circuit's gate list that this rule
    consumed -- used by simplify_fully to track which ORIGINAL gates each
    step traces back to, for click-to-trace provenance.

    replacement_count: 0 if the consumed gates are fully removed
    (cancellation), 1 if they're merged into a single new gate (power
    replacement, Pauli product, rotation composition).
    """
    gate_list = circuit_to_gate_list(qc)
    num_qubits = qc.num_qubits

    cancel_index = find_adjacent_cancellation(gate_list)
    if cancel_index is not None:
        candidate_gate_list = gate_list[:cancel_index] + gate_list[cancel_index + 2:]
        rule_name = f"adjacent self-inverse cancellation ({gate_list[cancel_index][0].upper()}^2 = I)"
        consumed_indices = [cancel_index, cancel_index + 1]
        replacement_count = 0
    else:
        full_order_range = find_full_order_cancellation(gate_list)
        if full_order_range is not None:
            start, end = full_order_range
            gate_name = gate_list[start][0]
            order = GATE_ORDER[gate_name]
            candidate_gate_list = gate_list[:start] + gate_list[end:]
            rule_name = f"full-order cancellation ({gate_name.upper()}^{order} = I)"
            consumed_indices = list(range(start, end))
            replacement_count = 0
        else:
            power_replacement = find_power_replacement(gate_list)
            if power_replacement is not None:
                start, replacement_name = power_replacement
                original_name, qubits, params = gate_list[start]
                candidate_gate_list = (
                    gate_list[:start] + [(replacement_name, qubits, ())] + gate_list[start + 2:]
                )
                rule_name = f"power replacement ({original_name.upper()}^2 = {replacement_name.upper()})"
                consumed_indices = [start, start + 1]
                replacement_count = 1
            else:
                pauli_product = find_pauli_product(gate_list)
                if pauli_product is not None:
                    start, replacement_name = pauli_product
                    name_a, qubits, params = gate_list[start]
                    name_b, _, _ = gate_list[start + 1]
                    candidate_gate_list = (
                        gate_list[:start] + [(replacement_name, qubits, ())] + gate_list[start + 2:]
                    )
                    rule_name = (
                        f"Pauli product ({name_a.upper()}\u00b7{name_b.upper()} = "
                        f"{replacement_name.upper()}, up to global phase)"
                    )
                    consumed_indices = [start, start + 1]
                    replacement_count = 1
                else:
                    rotation_index = find_rotation_composition(gate_list)
                    if rotation_index is not None:
                        name, qubits, params_a = gate_list[rotation_index]
                        _, _, params_b = gate_list[rotation_index + 1]
                        combined_angle = params_a[0] + params_b[0]

                        removed_gate_list = gate_list[:rotation_index] + gate_list[rotation_index + 2:]
                        removed_circuit = gate_list_to_circuit(removed_gate_list, num_qubits)

                        if circuits_equivalent(qc, removed_circuit):
                            return (
                                removed_circuit,
                                (
                                    f"rotation composition to identity "
                                    f"({name.upper()}(\u03b81)\u00b7{name.upper()}(\u03b82) = I, since \u03b81+\u03b82 "
                                    f"is a multiple of the rotation period)"
                                ),
                                [rotation_index, rotation_index + 1],
                                0,
                            )

                        candidate_gate_list = (
                            gate_list[:rotation_index]
                            + [(name, qubits, (combined_angle,))]
                            + gate_list[rotation_index + 2:]
                        )
                        rule_name = (
                            f"rotation composition "
                            f"({name.upper()}(\u03b81)\u00b7{name.upper()}(\u03b82) = {name.upper()}(\u03b81+\u03b82))"
                        )
                        consumed_indices = [rotation_index, rotation_index + 1]
                        replacement_count = 1
                    else:
                        commuting_pair = find_commuting_cancellation(gate_list)
                        if commuting_pair is None:
                            return None, None, None, None
                        i, j = commuting_pair
                        candidate_gate_list = gate_list[:i] + gate_list[i + 1:j] + gate_list[j + 1:]
                        rule_name = (
                            f"commutation-based non-adjacent cancellation "
                            f"({gate_list[i][0].upper()} gates commute past disjoint-qubit operations)"
                        )
                        consumed_indices = [i, j]
                        replacement_count = 0

    candidate_circuit = gate_list_to_circuit(candidate_gate_list, num_qubits)

    if circuits_equivalent(qc, candidate_circuit):
        return candidate_circuit, rule_name, consumed_indices, replacement_count
    else:
        return None, None, None, None


def simplify_fully(qc, max_iterations=50):
    """
    Repeatedly apply simplify_once until no more simplifications are found.
    Tracks a `provenance` list, parallel to the current circuit's gate list,
    where each entry is a tuple of ORIGINAL gate indices that position
    traces back to. Each step's `affected_gate_indices` records which
    original gates that step consumed -- this powers click-to-trace
    highlighting in the frontend.
    """
    current = qc
    steps_taken = []

    provenance = [(i,) for i in range(len(circuit_to_gate_list(qc)))]

    for _ in range(max_iterations):
        result = simplify_once(current)
        new_circuit, rule_name, consumed_indices, replacement_count = result

        if new_circuit is None:
            break

        affected_original_indices = sorted(set(
            original_index
            for position in consumed_indices
            for original_index in provenance[position]
        ))

        steps_taken.append({
            "rule": rule_name,
            "before_gate_count": len(current.data),
            "after_gate_count": len(new_circuit.data),
            "before_depth": current.depth(),
            "after_depth": new_circuit.depth(),
            "affected_gate_indices": affected_original_indices,
        })

        consumed_set = set(consumed_indices)
        new_provenance = []
        merged_entry_inserted = False

        for position in range(len(provenance)):
            if position in consumed_set:
                if replacement_count == 1 and not merged_entry_inserted:
                    new_provenance.append(tuple(affected_original_indices))
                    merged_entry_inserted = True
                continue
            new_provenance.append(provenance[position])

        provenance = new_provenance
        current = new_circuit

    return current, steps_taken


if __name__ == "__main__":
    qc = QuantumCircuit(3)
    qc.x(0)
    qc.x(0)
    qc.h(1)
    qc.z(2)
    qc.h(1)

    print("Original circuit:")
    print(qc.draw())
    print(f"Original gate count: {len(qc.data)}")

    final_circuit, steps = simplify_fully(qc)

    print(f"\nSimplification steps taken: {len(steps)}")
    for i, step in enumerate(steps, 1):
        print(f"  Step {i}: {step['rule']}")
        print(f"    affected original gate indices: {step['affected_gate_indices']}")

    print("\nFinal simplified circuit:")
    print(final_circuit.draw())
    print(f"Final gate count: {len(final_circuit.data)}")

    print("\nVerified equivalent to original:", circuits_equivalent(qc, final_circuit))