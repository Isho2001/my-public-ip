# MyPublicIP
A simple automation tool that reports your public IP address to you via email, It must be executed on a Windows or a Linux box in your LAN, It reports the IP address based on a time interval that the user inserts (optional). It also connects to a local database to store the past IP addresses and avoid duplicate reports. The tool is useful for people that are with ISPs that don't provide static public IP addresses.

Command line examples:

- sudo python3 MyPublicip.py --re ExampleReceiverEmail@ExampleDomain.com --o linux --se ExampleSenderEmail2@gmail.com --pw ExampleSenderPassword --t 24
- python MyPublicip.py --re ExampleReceiverEmail@ExampleDomain.com --o windows --se ExampleSenderEmail2@gmail.com --pw ExampleSenderPassword --t 24
