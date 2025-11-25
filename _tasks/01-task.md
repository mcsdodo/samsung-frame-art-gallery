# Trying if we can communicate with Samsung TV in art mode
Here is a library to communitate with samsung TVs ``https://github.com/NickWaterton/samsung-tv-ws-api``

Alternatively try this one ``https://github.com/xchwarze/samsung-tv-ws-api``

Verify it works with TV on our local network with IP ``192.168.0.105`` We are interested in "art mode" functionality. Logging the "supported()" function output would be a good start.

# Application requirements
1. we are going to implement a web-application that will run in a docker container on our local network. 
2. The web application will have mounted a folder with images to be displayed in art mode on the TV.
3. the web application will allow the user to select images from the mounted folder and send them to the TV to be displayed in art mode.
4. The web application should have a simple user interface to browse the images and select one to display on the TV.


DO NOT start implementing the application yet. First verify that you can communicate with the TV in art mode using the libraries mentioned above.