# Bannerpunk

A lightning node that is forwarding a payment obtains two things
a) a fee
b) a preimage

Here, the node, with the help of some software, if a sufficient forwarding fee is paid the node will interpet the preimage as pixel data and publish it via websocket.

# To draw pixels

Run a circular payment script with the correct preimage and fee for the target node.

Here is [a WIP example](circular.py)

This borrows logic/inspiration from the [sendinvoiceless.py](https://github.com/lightningd/plugins/blob/master/sendinvoiceless/sendinvoiceless.py) plugin.

* TODO - package as c-lightning plugin
* TODO - do the LND equavalent script
* TODO - script to unpack .png image into draw instructions (document package dependencies for image processing libs!)

# The Frontend

The example frontend which connects to the websocket app server and draws the pixels - as well as real-time updates (like satoshis.place) - is provided in the [htdocs](htdocs/) directory.

# Dependencies for running the server

depends on txzmq, Twisted, autobahn

`sudo pip3 install txzmq twisted autobahn`

# To Run Server With Node

1. The current lates c-lightning release (v0.7.3) will need to be patched with [this horrible hack](c-lightning-hack.diff) in order to expose the preimage involved in a forwarded payment to the plugin. (Before judging the quality of this code, recall half the theme of the competition is `Hack`).

2. The c-lightning node will also need to run with [this plugin](https://github.com/lightningd/plugins/pull/70) for publishing plugin notiviations via ZeroMQ. (this plugin was wlso written by us, eyeballs/test/review appreciated).

3. C-Lightning will need to be booted with a launch arg to configure the ZeroMQ publishing to an endpoint. Eg `--zmq-pub-forward-event=tcp//0.0.0.0:5556`

4. The [app server program](bat.py) will need to be run and configured to listen at the ZeroMQ for forward events. This will also accept websocket connections from browser clients running.

# Test the websocket and frontend without a lightning node

Since setting up nodes and payments is cumbersome for development a [mock publisher](mock-random.py) app is provided which publishes preimage-like values to the ZMQ endpoint for the websocket app server to catch and process.


reqires `pillow` and dependancies for interpeting .png images
`sudo apt-get install libopenjp2-7 libtiff5`
`sudo pip3 install pillow`
