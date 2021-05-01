# LocalNetworkServices
LocalNetworkServices is a program which facilitates interactions between computers on a local network.

Hello ! I present to you my python LAN software !
There is what you can do with this program :
You can access some services on LAN (chat/message service, file service and settings service).
- Message service : You can send messages to all the other clients (like a group chat).
- File : You can send a file to one or more clients and the recipient(s) will accept the file.
- Settings : You can actually only modify your nickname or view the others clients (nickname + ip with port).


### How does it work ?
 Okay let's begin with the technical part ! So, there are 2 major parts to understand :
- The transmission between the server and the clients : I use the "socket" library to transfer information between all these programs. The server and the client can communicate in the 2 ways. I created a kind of "protocol of transmission" who is really simple. The idea behind this "protocol" is to use a python dictionary to contain the data. Next, I transform it into a string with a function, I transform the data in bytes and I send the request ! The receiver will do the same process but backwards (I use the same functions to decode and code string to dictionary and dictionary to string). It seems simple but it takes a while to code ! On the server side, I choose to match one thread by client (idea of the client thread by using the library threading) to avoid big crashes and a slowdown if many users interact with the server at the same time. Indeed to avoid crashes it's a good solution because if a client crashes it won't normally crash the others threads (and it seems easier to handle).
- The GUI : By GUI I use the library "eel" (which allows me to use HTML/CSS/JS to create a "fancy" GUI and to transfer data between the web page and python). Indeed, I should have used Tkinter but creating a dynamic and fancy GUI with Tkinter it's a bit complicated (moreover Tkinter is not designed to create beautiful GUIs). For the record, "eel" is a GUI based on Chrome and links python and the web page. I only do a "complete" GUI for the client (because there is nearly nothing to do with the server in terms of user interactions). Otherwise I used Tkinter (very simply) as a IP/port chooser for the server and a file chooser for the client. And also a client error pop-up but it does nothing really useful (it was just to hear the beautiful Windows error song). I also created a "protocol of transmission" but this time it's more simple (just a command and a content in a string). Yes I have 2 transmission protocols, and yes it can get tricky to handle that but that's how I made it and it works (most of the time) !
