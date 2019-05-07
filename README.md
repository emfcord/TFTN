Easy and clean launch TFTN coin using ForkNote, the most advanced CryptoNote software supporting numerous networks.

### Overview

Forknote uses configuration files to describe the properties of a Cryptonote blockchain. To get started you must download the latest version of Forknote.

Connecting the daemon to a blockchain

To connect to the daemon to existing blockchain, just start forknoted with the corresponding configuration file.

$ ./forknoted --config-file configs/imaginary_blockchain.conf New blockchains are created by creating new configuration files. Configuration files are created with our blockchain creation form. You can find more about the available configuration options in our documentation.

### Examples

To connect the daemon to the TFTN coin, start TFTNd with its corresponding configuration file:

$ ./TFTNd --config-file configs/TFTN.conf To connect to the TFTN blockchain 

Starting simplewallet

Simplewallet uses the same configuration file as the daemon.

To start simplewallet:

$ ./TFTN_simplewallet --config-file configs/TFTN.conf Starting simplewallet for the TFTN blockchain


