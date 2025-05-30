# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: two_phase.proto
# Protobuf Python Version: 5.29.0
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    5,
    29,
    0,
    '',
    'two_phase.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0ftwo_phase.proto\x12\x06mcp2pc\"\x07\n\x05\x45mpty\"\x87\x01\n\x0ePrepareRequest\x12\x16\n\x0etransaction_id\x18\x01 \x01(\t\x12\x12\n\noperations\x18\x02 \x03(\t\x12\x16\n\x0etimeout_blocks\x18\x03 \x01(\x05\x12\x19\n\x11onchain_recipient\x18\x04 \x01(\t\x12\x16\n\x0eonchain_amount\x18\x05 \x01(\x04\"s\n\x0fPrepareResponse\x12.\n\x06status\x18\x01 \x01(\x0e\x32\x1e.mcp2pc.PrepareResponse.Status\x12\x10\n\x08shard_id\x18\x02 \x01(\t\"\x1e\n\x06Status\x12\t\n\x05READY\x10\x00\x12\t\n\x05\x41\x42ORT\x10\x01\"\'\n\rCommitRequest\x12\x16\n\x0etransaction_id\x18\x01 \x01(\t\"&\n\x0c\x41\x62ortRequest\x12\x16\n\x0etransaction_id\x18\x01 \x01(\t\")\n\x0fRollbackRequest\x12\x16\n\x0etransaction_id\x18\x01 \x01(\t\"Z\n\x0bLockRequest\x12\x16\n\x0etransaction_id\x18\x01 \x01(\t\x12\x11\n\trecipient\x18\x02 \x01(\t\x12\x0e\n\x06\x61mount\x18\x03 \x01(\x04\x12\x10\n\x08\x64\x65\x61\x64line\x18\x04 \x01(\x04\"\x16\n\x06TxHash\x12\x0c\n\x04hash\x18\x01 \x01(\t\"(\n\x0eOnChainRequest\x12\x16\n\x0etransaction_id\x18\x01 \x01(\t2\xa9\x01\n\x0b\x43oordinator\x12<\n\x07Prepare\x12\x16.mcp2pc.PrepareRequest\x1a\x17.mcp2pc.PrepareResponse0\x01\x12.\n\x06\x43ommit\x12\x15.mcp2pc.CommitRequest\x1a\r.mcp2pc.Empty\x12,\n\x05\x41\x62ort\x12\x14.mcp2pc.AbortRequest\x1a\r.mcp2pc.Empty2\xfc\x02\n\x05Shard\x12:\n\x07Prepare\x12\x16.mcp2pc.PrepareRequest\x1a\x17.mcp2pc.PrepareResponse\x12.\n\x06\x43ommit\x12\x15.mcp2pc.CommitRequest\x1a\r.mcp2pc.Empty\x12,\n\x05\x41\x62ort\x12\x14.mcp2pc.AbortRequest\x1a\r.mcp2pc.Empty\x12\x32\n\x08Rollback\x12\x17.mcp2pc.RollbackRequest\x1a\r.mcp2pc.Empty\x12\x32\n\x0bLockOnChain\x12\x13.mcp2pc.LockRequest\x1a\x0e.mcp2pc.TxHash\x12\x37\n\rCommitOnChain\x12\x16.mcp2pc.OnChainRequest\x1a\x0e.mcp2pc.TxHash\x12\x38\n\x0eReclaimOnChain\x12\x16.mcp2pc.OnChainRequest\x1a\x0e.mcp2pc.TxHashb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'two_phase_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_EMPTY']._serialized_start=27
  _globals['_EMPTY']._serialized_end=34
  _globals['_PREPAREREQUEST']._serialized_start=37
  _globals['_PREPAREREQUEST']._serialized_end=172
  _globals['_PREPARERESPONSE']._serialized_start=174
  _globals['_PREPARERESPONSE']._serialized_end=289
  _globals['_PREPARERESPONSE_STATUS']._serialized_start=259
  _globals['_PREPARERESPONSE_STATUS']._serialized_end=289
  _globals['_COMMITREQUEST']._serialized_start=291
  _globals['_COMMITREQUEST']._serialized_end=330
  _globals['_ABORTREQUEST']._serialized_start=332
  _globals['_ABORTREQUEST']._serialized_end=370
  _globals['_ROLLBACKREQUEST']._serialized_start=372
  _globals['_ROLLBACKREQUEST']._serialized_end=413
  _globals['_LOCKREQUEST']._serialized_start=415
  _globals['_LOCKREQUEST']._serialized_end=505
  _globals['_TXHASH']._serialized_start=507
  _globals['_TXHASH']._serialized_end=529
  _globals['_ONCHAINREQUEST']._serialized_start=531
  _globals['_ONCHAINREQUEST']._serialized_end=571
  _globals['_COORDINATOR']._serialized_start=574
  _globals['_COORDINATOR']._serialized_end=743
  _globals['_SHARD']._serialized_start=746
  _globals['_SHARD']._serialized_end=1126
# @@protoc_insertion_point(module_scope)
