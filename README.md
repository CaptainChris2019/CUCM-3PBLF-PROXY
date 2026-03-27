# CUCM 3rd Party SIP Device BLF Proxy
Normally, CUCM refuses to allow 3rd party SIP devices to subscribe to BLFs. This proxy fixes that issue by connecting to CUCM as a SIP trunk and relaying CUCM's presence messages to the phones using the RFC 3261 dialog standard. Every standard SIP phone should work as long as you can set the BLF to use a separate server from what the speed-dial calls.

This proxy server is written in Python, and was designed to work on a dedicated Linux virtual machine with at least 512MB of RAM that can sit on your ESXi host happily right next to your CUCM. It should also work in Docker or on another OS such as macOS or Windows. Because BLFs are very simple, the codebase does not rely on any external SIP library; everything it needs is done with Python's built-in libraries. Though many optional features require external libraries. This allows it to use very minimal resources. However, I have not yet tested it at an extreme scale.

All you need to do is change the IP addresses in the file. UPSTREAM_HOST is the IP of the CUCM node, and PROXY_IP is the IP of the machine your running it on. You will need to create a trunk in CUCM with the proxies IP. Make sure its SIP Security and Device profiles allow for presence, and that the SUBSCRIBE Calling Search Space contains every Directory Number you are monitoring with the proxy.

This is still a very much WIP. This is not yet production-ready.

## Setup BLFs
The process of setting up BLFs on most phones so they use a separate server for BLFs is very different from just adding a BLF and pointing it to the server.
### Polycom
On a Polycom phone, you will need to register a second line to register to the proxy server and set BLFs to use the second line.
### Cisco SPA/3PCC
These phones will happily monitor a BLF of any server. 
### MicroSIP
I have not yet found a way to do this on MicroSIP.

## Limitations
- CUCM does not seem to send ringing status to trunks


## Planned Future Expansion
- Support for Ringing Status
- TCP & TLS support
- Automatic detection of host IP address (if using DHCP/DNS, for some reason)
- Automatic installation for GNU/Linux users, including systemd service creation, and storing the script and debug tools in /usr/local/bin
- Possibly a version written in C ???
- Support for multiple CUCM nodes
- Testing on more phones, and testing at a larger scale
- A debug tool, to view in real time, while the script is running in the background, all the SIP headers
- A better way of storing settings
- Multiplexing (so say more than one phone is monitoring the same directory number, the proxy sends only one SUBSCRIBE request to CUCM and distrubites status updates to each phone) 
- Maybe making this more than just a proxy, including adding a REST API.
- And more
