**Spartan Messenger**

A chat messenger using gRPC in python3
A response-streaming RPC where the client sends a request to the server and gets a stream to read a sequence of messages back. The client reads from the returned stream until there are no more messages.

*Features*

- [x] Design supports group chats.
- [x] Implements a LRU Cache to store recent messages in memory.
- [x] Limit the number of messages a user can send to an API within a time window.
- [x] Provide end-to-end message encryption using AES.
- [x] LRU cache and rate limit implemented using decorator.

*configs*
Check config.yaml and client.yaml file for setting usernames, LRU/rate_limit, encryption keys, Port, etc. 

*dependencies*
Check dependencies.txt

