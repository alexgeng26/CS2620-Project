# run.sh
echo "Generating gRPC code..."
python utils/generate_proto.py protos/two_phase.proto mcp2pc

echo "Starting shards..."
python shard/shard_node.py --id shard1 --port 50061 &
python shard/shard_node.py --id shard2 --port 50062 &
python shard/shard_node.py --id shard3 --port 50063 &

sleep 1
echo "Starting coordinator..."
python coordinator/coordinator.py &

sleep 1
echo "Running client demo..."
python client/client.py