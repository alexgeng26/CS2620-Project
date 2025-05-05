# scripts/compile_abi.py

import solcx, json, os

# ensure Solc 0.8.0 is installed
try:
    solcx.set_solc_version("0.8.0")
except solcx.exceptions.SolcNotInstalled:
    solcx.install_solc("0.8.0")
    solcx.set_solc_version("0.8.0")

# read Solidity source file as UTF-8
with open("TwoPhaseAdapter.sol", encoding="utf-8") as f:
    src = f.read()

# compile just to get the ABI
compiled = solcx.compile_standard({
    "language": "Solidity",
    "sources": { "TwoPhaseAdapter.sol": { "content": src } },
    "settings": {
        "outputSelection": { "*": { "*": ["abi"] } }
    }
})

abi = compiled["contracts"]["TwoPhaseAdapter.sol"]["TwoPhaseAdapter"]["abi"]

# write it out
os.makedirs("abi", exist_ok=True)
with open("abi/TwoPhaseAdapter.json", "w", encoding="utf-8") as f:
    json.dump(abi, f, indent=2)

print("ABI written to abi/TwoPhaseAdapter.json")
