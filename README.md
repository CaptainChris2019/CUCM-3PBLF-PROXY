# CUCM 3rd Party SIP Device BLF Proxy
Normally, CUCM refuses to allow 3rd party SIP devices to subscribe to BLFs. This proxy fixes that issue by connecting to CUCM as a SIP trunk and relaying it to the phones using the RFC 3261 standard. Every standard SIP phone should work as long as you can set the BLF to use a separate IP address than the speed-dial. However for now, I have only tested it on a Cisco 7861-3PCC, and only this one phone.

This proxy server is written in Python, and was designed to work on a deadicated Debian virtual machine with at least 512MB of RAM that can sit on your ESXi host happily right next to your CUCM. It should also work in Docker or on another OS such as macOS or Windows. Because BLFs are very simple, it does not rely on any external SIP library, everything it needs is in to every Python install. This allows it use very minimal resources. However, I have not yet tested it at an extreme scale.

All you need to do is change the IP addresses in the file. UPSTREAM_HOST is the IP of the CUCM node, and PROXY_IP is the IP of the machine your running it on. You will need to create a trunk in CUCM with the proxies IP. Make sure its SIP Security and Device profiles allow for presence, and that the SUBSCRIBE Calling Search Space contains every Directory Number you are monitoring with the proxy.

This is still a very much WIP. This is not yet production-ready.

### Setup BLFs
## Polycom
On a Polycom phone, you will need to register a second line to register to the proxy server and set BLFs to use the second line.

### Planned Future Expansion
- Fixing everything including the grammar on this README (hey, dont blame me, im tired)
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
- Sending 301 to CUCM to endpoints who sent INVITES to the proxy to CUCM (for if your phone needs the speedial dst IP to be the same as the BLF IP.
- A way to make subscriptions persist after a reboot of the script (such as using SQLite)
- And more
