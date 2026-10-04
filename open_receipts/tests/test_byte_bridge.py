"""R9: byte preservation, bounded replay, missing evidence and trust boundary."""
import base64
import contextlib
import copy
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from open_receipts.byte_bridge import (
    MAX_BYTES, SCHEMA, capture, load_record, main, read_bounded, restore_original, transform, verify,
)
from open_receipts.verifier import finalize_receipt, verify_receipts


class ByteBridgeTests(unittest.TestCase):
    def pair(self, embedded=False):
        source = 'Júnior\r\nfonte\r'.encode('utf-8')
        output = 'Júnior\nfonte\n'.encode('utf-8')
        return source, output, capture(source, output, 'utf8-lf-v1', include_original=embedded)

    def test_powerbi_fields_are_separate_commitments(self):
        source, output, record = self.pair()
        self.assertEqual(record['SHA256Fonte'], hashlib.sha256(source).hexdigest())
        self.assertEqual(record['SHA256Saida'], hashlib.sha256(output).hexdigest())
        self.assertNotEqual(record['SHA256Fonte'], record['SHA256Saida'])
        self.assertEqual(record['TamanhoFonteBytes'], len(source))
        self.assertEqual(record['TamanhoSaidaBytes'], len(output))

    def test_no_source_embedding_by_default(self):
        source, output, record = self.pair()
        self.assertFalse(record['OriginalReversivelIncluido'])
        self.assertNotIn('OriginalBase64', record)
        self.assertNotIn('Júnior', json.dumps(record, ensure_ascii=False))

    def test_exact_restoration_all_byte_values(self):
        raw = bytes(range(256)) + b'\x00\xff\r\n'
        record = capture(raw, raw, 'identity-v1', include_original=True)
        self.assertEqual(restore_original(record), raw)
        self.assertEqual(verify(record, output=raw)['status'], 'VERIFIED_BYTES_AND_REPLAY')

    def test_lossy_normalization_does_not_replace_original(self):
        source, output, record = self.pair(True)
        self.assertNotEqual(source, output)
        self.assertEqual(restore_original(record), source)
        self.assertEqual(verify(record, output=output)['status'], 'VERIFIED_BYTES_AND_REPLAY')

    def test_json_normalization_keeps_sha256_key(self):
        source = b'{ "z": 2, "sha256":"payload", "a":1 }\r\n'
        output = transform(source, 'json-object-sorted-v1')
        self.assertEqual(output, b'{"a":1,"sha256":"payload","z":2}')
        record = capture(source, output, 'json-object-sorted-v1')
        self.assertEqual(verify(record, source=source, output=output)['status'], 'VERIFIED_BYTES_AND_REPLAY')

    def test_semantically_equal_json_has_distinct_raw_hashes(self):
        a, b = b'{"a":1,"b":2}', b'{ "b": 2, "a": 1 }\n'
        output = transform(a, 'json-object-sorted-v1')
        self.assertEqual(output, transform(b, 'json-object-sorted-v1'))
        rec_a, rec_b = (capture(x, output, 'json-object-sorted-v1') for x in (a,b))
        self.assertEqual(rec_a['SHA256Saida'], rec_b['SHA256Saida'])
        self.assertNotEqual(rec_a['SHA256Fonte'], rec_b['SHA256Fonte'])
        self.assertEqual(verify(rec_a, source=b, output=output)['status'], 'INVALID')

    def test_missing_evidence_is_not_decidable(self):
        _, output, record = self.pair()
        self.assertEqual(verify(record)['status'], 'NOT_DECIDABLE')
        self.assertEqual(verify(record, output=output)['status'], 'NOT_DECIDABLE')
        self.assertEqual(verify(self.pair(True)[2])['status'], 'NOT_DECIDABLE')

    def test_empty_file_is_not_empty_chain(self):
        record = capture(b'', b'', 'identity-v1', include_original=True)
        self.assertEqual(restore_original(record), b'')
        self.assertEqual(verify(record, output=b'')['status'], 'VERIFIED_BYTES_AND_REPLAY')
        self.assertTrue(verify_receipts([]))

    def test_source_tamper_and_truncation(self):
        source, output, record = self.pair()
        for bad in (source[:-1], b'X' + source[1:]):
            with self.subTest(bad=bad):
                self.assertEqual(verify(record, source=bad, output=output)['status'], 'INVALID')

    def test_output_tamper(self):
        source, output, record = self.pair()
        self.assertEqual(verify(record, source=source, output=output+b'X')['status'], 'INVALID')

    def test_embedded_original_tamper(self):
        source, output, record = self.pair(True)
        record['OriginalBase64'] = base64.b64encode(b'X'+source[1:]).decode()
        self.assertEqual(verify(record, output=output)['restoration'], 'MISMATCH')
        with self.assertRaises(ValueError):
            restore_original(record)

    def test_supplied_source_cannot_be_silently_replaced(self):
        source, output, record = self.pair(True)
        result = verify(record, source=b'X'+source[1:], output=output)
        self.assertEqual(result['restoration'], 'MISMATCH')
        self.assertEqual(result['status'], 'INVALID')

    def test_base64_whitespace_invalid_alphabet_and_padbits(self):
        record = capture(b'a', b'a', 'identity-v1', include_original=True)
        for text in ('YQ=\n', 'Y?==', 'YR=='):
            with self.subTest(text=text):
                changed = {**record, 'OriginalBase64': text}
                with self.assertRaises(ValueError):
                    restore_original(changed)

    def test_metadata_schema_types_and_sizes(self):
        _, _, record = self.pair(True)
        cases = [('schema','other'), ('OriginalReversivelIncluido',1),
                 ('SHA256Fonte','A'*64), ('TamanhoFonteBytes',False),
                 ('TamanhoFonteBytes',-1), ('TamanhoSaidaBytes',1.0),
                 ('TamanhoSaidaBytes',MAX_BYTES+1), ('ModoSaida','run_shell')]
        for key,value in cases:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                verify({**record,key:value})

    def test_missing_and_extra_fields(self):
        _,_, record = self.pair()
        for field in record:
            changed = dict(record); del changed[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify(changed)
        with self.assertRaises(ValueError):
            verify({**record,'path':'/do/not/open'})

    def test_duplicate_keys_and_nonfinite_json_rejected(self):
        for raw in (b'{"schema":"a","schema":"b"}', b'{"x":NaN}', b'{"x":1e999}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                load_record(raw)
        for raw in (b'{"x":{"a":1,"a":2}}', b'{"x":Infinity}', b'{"x":1e999}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                transform(raw,'json-object-sorted-v1')

    def test_invalid_utf8_preserved_but_not_normalized(self):
        raw = b'\xff\x00'
        self.assertEqual(restore_original(capture(raw,raw,'identity-v1',include_original=True)),raw)
        for mode in ('utf8-lf-v1','json-object-sorted-v1'):
            with self.subTest(mode=mode), self.assertRaises(UnicodeError):
                transform(raw,mode)

    def test_json_object_requirement_and_surrogate(self):
        for raw in (b'[]',b'null',b'1',b'{"s":"\\ud800"}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                transform(raw,'json-object-sorted-v1')

    def test_declared_transform_not_claimed_verified(self):
        record = capture(b'a', b'b', 'declared-only-v1')
        result = verify(record, source=b'a',output=b'b')
        self.assertEqual(result['source_bytes'],'MATCH')
        self.assertEqual(result['output_bytes'],'MATCH')
        self.assertEqual(result['replay'],'NOT_CHECKED')
        self.assertEqual(result['status'],'NOT_DECIDABLE')

    def test_capture_rejects_false_replay_claim(self):
        with self.assertRaisesRegex(ValueError,'replay'):
            capture(b'a',b'b','identity-v1')
        with self.assertRaises(ValueError):
            capture(b'a',b'a','identity-v1',include_original=1)

    def test_forged_hash_pair_does_not_establish_replay(self):
        record = capture(b'a',b'a','identity-v1')
        record['SHA256Saida'] = hashlib.sha256(b'b').hexdigest()
        result = verify(record, source=b'a',output=b'b')
        self.assertEqual(result['output_bytes'],'MATCH')
        self.assertEqual(result['replay'],'MISMATCH')
        self.assertEqual(result['status'],'INVALID')

    def test_record_roundtrip_and_no_digest_reconstruction(self):
        _, _, record = self.pair()
        self.assertEqual(load_record(json.dumps(record).encode()), record)
        with self.assertRaises(ValueError):
            restore_original(record)

    def test_size_limits_and_bounded_read(self):
        for n in (False,0,-1,2.5):
            with self.subTest(n=n), self.assertRaises(ValueError):
                capture(b'a',b'a','identity-v1',max_bytes=n)
        with self.assertRaises(ValueError):
            capture(b'12345',b'12345','identity-v1',max_bytes=4)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'large'; path.write_bytes(b'12345')
            with self.assertRaises(ValueError):
                read_bounded(path,4)

    def test_payload_chains_with_r7_without_changing_r7(self):
        source, output, record = self.pair(True)
        receipt = finalize_receipt({'seq':0,'prev_sha256':None,'byte_bridge':record})
        self.assertEqual(verify_receipts([receipt],expected_head=receipt['sha256']),[])
        self.assertEqual(verify(receipt['byte_bridge'],output=output)['status'],'VERIFIED_BYTES_AND_REPLAY')
        receipt['byte_bridge']['SHA256Fonte']='0'*64
        self.assertTrue(verify_receipts([receipt]))

    def test_full_rewrite_still_requires_independent_checkpoint(self):
        a = finalize_receipt({'seq':0,'prev_sha256':None,'byte_bridge':capture(b'a',b'a','identity-v1')})
        b = finalize_receipt({'seq':0,'prev_sha256':None,'byte_bridge':capture(b'b',b'b','identity-v1')})
        self.assertEqual(verify_receipts([b]),[])
        self.assertEqual(verify(b['byte_bridge'],source=b'b',output=b'b')['status'],'VERIFIED_BYTES_AND_REPLAY')
        self.assertTrue(verify_receipts([b],expected_head=a['sha256']))

    def test_cli_return_codes_and_no_raw_payload(self):
        source,output,record=self.pair(True)
        with tempfile.TemporaryDirectory() as td:
            r,s,o=(Path(td)/n for n in ('record.json','source.bin','output.bin'))
            r.write_text(json.dumps(record)); s.write_bytes(source); o.write_bytes(output)
            for argv,code in (([str(r),'--source',str(s),'--output',str(o)],0),([str(r)],2)):
                out=io.StringIO()
                with contextlib.redirect_stdout(out):
                    self.assertEqual(main(argv),code)
                self.assertNotIn('Júnior',out.getvalue())
            o.write_bytes(b'bad')
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(r),'--output',str(o)]),1)
            r.write_bytes(b'\xff')
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main([str(r)]),2)


if __name__ == '__main__':
    unittest.main()
