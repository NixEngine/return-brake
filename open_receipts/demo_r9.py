"""Synthetic R9 demo; no network, source-file reads or filesystem writes."""
import json
from .byte_bridge import capture, restore_original, transform, verify
from .verifier import finalize_receipt, verify_receipts


def main() -> None:
    source = '{ "z":2, "nome":"Júnior", "sha256":"dado" }\r\n'.encode('utf-8')
    output = transform(source, 'json-object-sorted-v1')
    record = capture(source, output, 'json-object-sorted-v1', include_original=True)
    receipt = finalize_receipt({'seq': 0, 'prev_sha256': None, 'byte_bridge': record})
    result = {
        'synthetic_only': True,
        'original': verify(record, output=output),
        'same_json_different_bytes': verify(record, source=source+b'\n', output=output),
        'no_output_supplied': verify(record),
        'restoration_exact': restore_original(record) == source,
        'r7_chain_errors': verify_receipts([receipt]),
        'receipt_sha256': receipt['sha256'],
        'external_authentication_performed': False,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
